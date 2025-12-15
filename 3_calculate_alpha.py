#!/usr/bin/env python3
"""
Phase 3: Calculate Alpha and Generate Profile

Input:
    - node_*.yaml (모든 노드)
    - tool_oi_measurements.json

Output:
    - profile.yaml (49개 tool의 alpha, P_comp)
    - roofline_all_nodes.png (전체 Roofline 그래프)

Alpha 계산 방법:
    - Roofline 기반: α = sigmoid(log(OI) - log(ridge_point))
    - OI > ridge_point → CPU-bound (α ≈ 1.0)
    - OI < ridge_point → Memory/IO-bound (α ≈ 0.0)

Usage:
    python3 3_calculate_alpha.py
"""

import json
import yaml
import math
import glob
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from utils.tool_definitions import get_all_tools


def calculate_alpha_sigmoid(oi, ridge_point, k=2.0):
    """
    Calculate alpha using sigmoid function

    Args:
        oi: Operational Intensity (FLOPS/Byte)
        ridge_point: Ridge point of the node (FLOPS/Byte)
        k: Sigmoid steepness parameter

    Returns:
        alpha value (0.0 ~ 1.0)
    """
    if oi is None or ridge_point is None or ridge_point == 0:
        return 0.5  # Default to mixed

    # Avoid log(0)
    oi = max(oi, 1e-6)
    ridge_point = max(ridge_point, 1e-6)

    log_oi = math.log(oi)
    log_ridge = math.log(ridge_point)

    x = k * (log_oi - log_ridge)
    alpha = 1.0 / (1.0 + math.exp(-x))

    return alpha


def determine_data_locality(server_name):
    """
    Determine data locality based on server type

    Returns:
        data_locality string
    """
    locality_map = {
        'filesystem': 'local_data',
        'image_resize': 'local_data',
        'log_parser': 'local_data',
        'data_aggregate': 'local_compute',
        'sequentialthinking': 'local_compute',
        'git': 'version_control',
        'fetch': 'network',
        'summarize': 'network',
        'time': 'local_utility',
    }
    return locality_map.get(server_name, 'unknown')


def estimate_p_comp_from_oi(oi, node_specs):
    """
    Estimate P_comp (execution cost) based on OI and node specs

    Higher OI → CPU-bound → faster on high-FLOPS nodes
    Lower OI → Memory-bound → faster on high-BW nodes

    Args:
        oi: Operational Intensity
        node_specs: dict of {node_type: {'peak_flops', 'memory_bw', 'ridge_point'}}

    Returns:
        P_comp dict: {'DEVICE': X, 'EDGE': Y, 'CLOUD': Z}
    """
    # Estimate relative execution time on each node type
    exec_times = {}

    for node_type, specs in node_specs.items():
        ridge = specs['ridge_point']
        if ridge == 0:
            continue

        alpha = calculate_alpha_sigmoid(oi, ridge)

        # Inverse performance (higher = slower)
        # T ∝ 1/FLOPS (CPU) + 1/BW (Memory)
        cpu_contrib = alpha / specs['peak_flops']
        mem_contrib = (1 - alpha) / specs['memory_bw']

        # Relative execution time (inverse performance)
        exec_times[node_type] = cpu_contrib + mem_contrib

    if not exec_times:
        return {'DEVICE': 1.0, 'EDGE': 0.5, 'CLOUD': 0.0}

    # Min-Max normalization
    min_time = min(exec_times.values())
    max_time = max(exec_times.values())

    if max_time == min_time:
        return {nt: 0.5 for nt in exec_times.keys()}

    p_comp = {}
    for node_type, exec_time in exec_times.items():
        p_comp[node_type] = (exec_time - min_time) / (max_time - min_time)

    return p_comp


def load_node_specs():
    """Load all node_*.yaml files"""
    node_files = glob.glob('node_*.yaml')

    if not node_files:
        print("❌ No node_*.yaml files found!")
        print("\nRun Phase 1 first:")
        print("  python3 1_benchmark_node.py")
        return None

    nodes = {}
    node_types = {}  # Map hostname to node type (DEVICE/EDGE/CLOUD)

    for node_file in node_files:
        with open(node_file, 'r') as f:
            data = yaml.safe_load(f)

        hostname = data['hostname']

        # Determine node type based on hostname or specs
        # Simple heuristic: lowest FLOPS = DEVICE, highest = CLOUD
        nodes[hostname] = data

    # Classify nodes as DEVICE, EDGE, CLOUD based on peak_flops
    sorted_nodes = sorted(nodes.items(), key=lambda x: x[1].get('peak_flops', 0))

    if len(sorted_nodes) >= 3:
        node_types[sorted_nodes[0][0]] = 'DEVICE'   # Slowest
        for i in range(1, len(sorted_nodes) - 1):
            node_types[sorted_nodes[i][0]] = 'EDGE'
        node_types[sorted_nodes[-1][0]] = 'CLOUD'   # Fastest
    elif len(sorted_nodes) == 2:
        node_types[sorted_nodes[0][0]] = 'DEVICE'
        node_types[sorted_nodes[1][0]] = 'EDGE'
    elif len(sorted_nodes) == 1:
        node_types[sorted_nodes[0][0]] = 'DEVICE'

    print(f"Loaded {len(nodes)} nodes:")
    for hostname, node_type in node_types.items():
        specs = nodes[hostname]
        print(f"  {hostname:20s} → {node_type:6s} "
              f"(FLOPS={specs.get('peak_flops', 0):.1f}, "
              f"BW={specs.get('memory_bw', 0):.1f}, "
              f"Ridge={specs.get('ridge_point', 0):.2f})")

    # Create node_specs by type
    node_specs = {}
    for hostname, node_type in node_types.items():
        if node_type not in node_specs:
            node_specs[node_type] = []
        node_specs[node_type].append(nodes[hostname])

    # Average specs for each type
    averaged_specs = {}
    for node_type, specs_list in node_specs.items():
        averaged_specs[node_type] = {
            'peak_flops': sum(s.get('peak_flops', 0) for s in specs_list) / len(specs_list),
            'memory_bw': sum(s.get('memory_bw', 0) for s in specs_list) / len(specs_list),
            'ridge_point': sum(s.get('ridge_point', 0) for s in specs_list) / len(specs_list),
        }

    return averaged_specs, nodes, node_types


def load_tool_oi():
    """Load tool_oi_measurements.json"""
    oi_file = 'tool_oi_measurements.json'

    if not Path(oi_file).exists():
        print(f"❌ {oi_file} not found!")
        print("\nRun Phase 2 first:")
        print("  python3 2_measure_tool_oi.py")
        return None

    with open(oi_file, 'r') as f:
        data = json.load(f)

    # Convert to dict
    tool_oi = {}
    for item in data:
        tool_oi[item['tool_name']] = item

    print(f"\nLoaded OI for {len(tool_oi)} tools")
    return tool_oi


def plot_roofline_all(node_specs, tool_profiles):
    """Generate comprehensive Roofline plot"""
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(14, 8))

        colors = {
            'DEVICE': '#e74c3c',  # Red
            'EDGE': '#3498db',    # Blue
            'CLOUD': '#2ecc71',   # Green
        }

        # OI range
        oi = np.logspace(-2, 2, 1000)

        # Plot Roofline for each node type
        for node_type, specs in node_specs.items():
            peak_flops = specs['peak_flops']
            memory_bw = specs['memory_bw']

            memory_bound = memory_bw * oi
            cpu_bound = np.ones_like(oi) * peak_flops
            roofline = np.minimum(memory_bound, cpu_bound)

            ax.loglog(oi, roofline, color=colors[node_type], linewidth=2.5,
                     label=f'{node_type} Roofline', alpha=0.7)

        # Plot tools (color by alpha value)
        for tool_name, profile in tool_profiles.items():
            oi_val = profile.get('operational_intensity')
            alpha_val = profile.get('alpha', 0.5)

            if oi_val and oi_val > 0:
                # Estimate performance for plotting (use average node)
                avg_flops = sum(s['peak_flops'] for s in node_specs.values()) / len(node_specs)
                avg_bw = sum(s['memory_bw'] for s in node_specs.values()) / len(node_specs)

                perf = min(avg_bw * oi_val, avg_flops)

                # Color by alpha: red (CPU-bound) to blue (Memory-bound)
                if alpha_val >= 0.7:
                    color = 'red'
                elif alpha_val <= 0.3:
                    color = 'blue'
                else:
                    color = 'orange'

                ax.scatter(oi_val, perf, c=color,
                          s=50, alpha=0.6, edgecolors='black', linewidth=0.5)

        # Ridge points
        for node_type, specs in node_specs.items():
            ridge = specs['ridge_point']
            ax.axvline(ridge, color=colors[node_type], linestyle='--',
                      linewidth=1.5, alpha=0.5)

        ax.set_xlabel('Operational Intensity (FLOPS/Byte)', fontsize=13)
        ax.set_ylabel('Performance (GFLOPS)', fontsize=13)
        ax.set_title('Roofline Model - All Nodes and Tools', fontsize=15, fontweight='bold')
        ax.grid(True, which='both', linestyle=':', alpha=0.4)

        # Custom legend
        from matplotlib.patches import Patch
        legend_elements = []

        # Node types
        for node_type, color in colors.items():
            if node_type in node_specs:
                legend_elements.append(Patch(facecolor=color, label=f'{node_type} Node'))

        # Tool alpha categories
        legend_elements.append(Patch(facecolor='red', alpha=0.6, label='CPU-bound (α ≥ 0.7)'))
        legend_elements.append(Patch(facecolor='orange', alpha=0.6, label='Mixed (0.3 < α < 0.7)'))
        legend_elements.append(Patch(facecolor='blue', alpha=0.6, label='Memory/IO-bound (α ≤ 0.3)'))

        ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

        plt.tight_layout()
        output_file = 'roofline_all_nodes.png'
        plt.savefig(output_file, dpi=200)
        print(f"\n✓ Roofline plot saved: {output_file}")

    except ImportError:
        print("\n⚠️  matplotlib not installed, skipping plot")


def main():
    print("="*60)
    print("Phase 3: Calculate Alpha and Generate Profile")
    print("="*60)
    print()

    # Load node specs
    result = load_node_specs()
    if not result:
        return
    node_specs, all_nodes, node_types = result

    # Load tool OI
    tool_oi = load_tool_oi()
    if not tool_oi:
        return

    print()
    print("="*60)
    print("Calculating Alpha for each tool...")
    print("="*60)
    print()

    tool_profiles = {}

    for tool in get_all_tools():
        tool_name = tool['name']
        oi_data = tool_oi.get(tool_name, {})
        oi = oi_data.get('operational_intensity', 0.5)

        # Calculate alpha for each node type
        alphas = {}
        for node_type, specs in node_specs.items():
            alpha = calculate_alpha_sigmoid(oi, specs['ridge_point'])
            alphas[node_type] = round(alpha, 3)

        # Average alpha (for tools that can run on multiple node types)
        avg_alpha = sum(alphas.values()) / len(alphas)

        # Estimate P_comp
        p_comp = estimate_p_comp_from_oi(oi, node_specs)

        tool_profile = {
            'description': tool['description'],
            'data_locality': determine_data_locality(tool['server']),
            'operational_intensity': round(oi, 4),
            'alpha': round(avg_alpha, 3),
            'P_comp': [
                round(p_comp.get('DEVICE', 1.0), 3),
                round(p_comp.get('EDGE', 0.5), 3),
                round(p_comp.get('CLOUD', 0.0), 3),
            ],
        }

        tool_profiles[tool_name] = tool_profile

        print(f"{tool_name:30s} OI={oi:6.4f}  α={avg_alpha:.3f}  "
              f"P_comp=[{tool_profile['P_comp'][0]:.2f}, {tool_profile['P_comp'][1]:.2f}, {tool_profile['P_comp'][2]:.2f}]  "
              f"[{tool_profile['data_locality']}]")

    # Save profile.yaml
    output_data = {
        'tools': tool_profiles,
        'node_specs': node_specs,
    }

    output_file = 'profile.yaml'
    with open(output_file, 'w') as f:
        yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

    # Fix P_comp formatting to be inline [x, y, z] instead of multi-line
    import re
    with open(output_file, 'r') as f:
        content = f.read()

    # Replace P_comp multi-line lists with inline format
    # Pattern: P_comp:\n    - X\n    - Y\n    - Z
    def replace_pcomp(match):
        lines = match.group(0).split('\n')
        values = [line.strip().replace('- ', '') for line in lines[1:] if line.strip().startswith('-')]
        return f"P_comp: [{', '.join(values)}]\n"

    content = re.sub(r'P_comp:\n(?:    - [0-9.]+\n)+', replace_pcomp, content)

    with open(output_file, 'w') as f:
        f.write(content)

    print()
    print("="*60)
    print(f"✓ Profile saved: {output_file}")
    print("="*60)

    # Statistics
    print("\nAlpha distribution:")
    cpu_bound = sum(1 for p in tool_profiles.values() if p['alpha'] >= 0.7)
    memory_bound = sum(1 for p in tool_profiles.values() if p['alpha'] <= 0.3)
    mixed = len(tool_profiles) - cpu_bound - memory_bound

    print(f"  CPU-bound (α ≥ 0.7):         {cpu_bound:2d} tools")
    print(f"  Memory/IO-bound (α ≤ 0.3):   {memory_bound:2d} tools")
    print(f"  Mixed (0.3 < α < 0.7):       {mixed:2d} tools")

    # Generate Roofline plot
    plot_roofline_all(node_specs, tool_profiles)

    print()
    print("✓ All done!")


if __name__ == "__main__":
    main()
