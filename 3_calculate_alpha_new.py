#!/usr/bin/env python3
"""
Phase 3: Calculate Alpha from Execution Time

Alpha 계산 공식:
    alpha = T_exec / (T_exec + T_comm_ref)

where:
    T_exec = 실제 tool 실행시간 (측정값)
    T_comm_ref = (Input_size + Output_size) / Bandwidth_node

Input:
    - node_*.yaml (노드 성능, network_bandwidth_mbps 포함)
    - native_tool_exec_time_*.json (Native 실행시간)
    - wasm_tool_exec_time_*.json (WASM 실행시간)

Output:
    - profile_native.yaml
    - profile_wasm.yaml

Usage:
    python3 3_calculate_alpha_new.py
"""

import json
import yaml
import glob
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from utils.tool_definitions import get_all_tools, determine_data_locality


def load_node_specs():
    """Load all node_*.yaml files"""
    node_files = glob.glob('node_*.yaml')

    if not node_files:
        print("❌ No node_*.yaml files found!")
        print("\nRun Phase 1 first:")
        print("  python3 1_benchmark_node.py")
        return None

    nodes = {}
    for node_file in node_files:
        with open(node_file, 'r') as f:
            data = yaml.safe_load(f)
        hostname = data['hostname']
        nodes[hostname] = data

    print(f"Loaded {len(nodes)} nodes:")
    for hostname, specs in nodes.items():
        bw = specs.get('network_bandwidth_mbps', 100)
        print(f"  {hostname:20s} → Network BW: {bw:.2f} Mbps")

    return nodes


def load_exec_times(pattern):
    """Load tool execution time measurements"""
    files = glob.glob(pattern)

    if not files:
        print(f"⚠️  No files matching: {pattern}")
        return {}

    all_data = {}
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)

        # Group by hostname (extract from filename)
        # e.g., native_tool_exec_time_device-rpi.json → device-rpi
        hostname = file.split('_')[-1].replace('.json', '')

        all_data[hostname] = {item['tool_name']: item for item in data}

    print(f"Loaded execution times from {len(files)} files")
    for hostname, tools in all_data.items():
        print(f"  {hostname}: {len(tools)} tools")

    return all_data


def calculate_alpha(t_exec, input_size, output_size, bandwidth_mbps):
    """
    Calculate alpha using execution time and communication reference time

    Args:
        t_exec: Execution time (seconds)
        input_size: Input payload size (bytes)
        output_size: Output payload size (bytes)
        bandwidth_mbps: Network bandwidth (Mbps)

    Returns:
        alpha: Computation importance (0.0 ~ 1.0)
    """
    # Convert bandwidth to bytes/second
    bandwidth_bytes_per_sec = (bandwidth_mbps * 1_000_000) / 8

    # Total data transfer (input + output)
    total_bytes = input_size + output_size

    # Communication reference time
    t_comm_ref = total_bytes / bandwidth_bytes_per_sec if bandwidth_bytes_per_sec > 0 else 0

    # Alpha = T_exec / (T_exec + T_comm_ref)
    if t_exec + t_comm_ref == 0:
        return 0.5  # Default

    alpha = t_exec / (t_exec + t_comm_ref)

    # Clamp to [0, 1]
    return min(1.0, max(0.0, alpha))


def generate_profile(exec_times_by_node, nodes, output_file):
    """Generate profile.yaml"""

    all_tools = get_all_tools()
    tool_profiles = {}

    print("\nCalculating Alpha for each tool...")
    print("="*80)

    for tool in all_tools:
        tool_name = tool['name']
        server_name = tool['server']

        # Collect alpha values from different nodes
        alphas = {}
        t_execs = {}
        input_sizes = []
        output_sizes = []

        for hostname, exec_data in exec_times_by_node.items():
            if tool_name not in exec_data:
                continue

            tool_data = exec_data[tool_name]
            node_specs = nodes.get(hostname, {})
            bandwidth = node_specs.get('network_bandwidth_mbps', 100)

            t_exec = tool_data['t_exec']
            input_size = tool_data['input_size']
            output_size = tool_data['output_size']

            alpha = calculate_alpha(t_exec, input_size, output_size, bandwidth)

            alphas[hostname] = round(alpha, 3)
            t_execs[hostname] = round(t_exec, 4)
            input_sizes.append(input_size)
            output_sizes.append(output_size)

        if not alphas:
            print(f"{tool_name:30s} ⚠️  No measurements")
            continue

        # Average alpha
        avg_alpha = sum(alphas.values()) / len(alphas)

        # Average sizes
        avg_input = sum(input_sizes) / len(input_sizes) if input_sizes else 0
        avg_output = sum(output_sizes) / len(output_sizes) if output_sizes else 0

        # Determine data locality
        data_locality = determine_data_locality(server_name)

        # Tool profile
        tool_profile = {
            'description': tool['description'],
            'data_locality': data_locality,
            'alpha': round(avg_alpha, 3),
            'alpha_by_node': alphas,
            't_exec_by_node': t_execs,
            'avg_input_size_bytes': int(avg_input),
            'avg_output_size_bytes': int(avg_output),
        }

        tool_profiles[tool_name] = tool_profile

        # Print
        alpha_str = f"α={avg_alpha:.3f}"
        nodes_str = ", ".join([f"{h}:{alphas[h]:.3f}" for h in sorted(alphas.keys())])
        print(f"{tool_name:30s} {alpha_str:10s} [{nodes_str}]")

    # Save
    output_data = {
        'tools': tool_profiles,
        'metadata': {
            'measured_nodes': list(exec_times_by_node.keys()),
            'total_tools': len(tool_profiles),
        }
    }

    with open(output_file, 'w') as f:
        yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

    print()
    print("="*80)
    print(f"✓ Profile saved: {output_file}")
    print(f"  Tools: {len(tool_profiles)}")
    print("="*80)

    # Statistics
    alphas = [p['alpha'] for p in tool_profiles.values()]
    high_alpha = sum(1 for a in alphas if a >= 0.7)
    low_alpha = sum(1 for a in alphas if a <= 0.3)
    mid_alpha = len(alphas) - high_alpha - low_alpha

    print("\nAlpha Distribution:")
    print(f"  High (α ≥ 0.7):  {high_alpha:3d} tools (Computation-intensive)")
    print(f"  Mid  (0.3 < α < 0.7): {mid_alpha:3d} tools (Mixed)")
    print(f"  Low  (α ≤ 0.3):  {low_alpha:3d} tools (Communication-intensive)")


def main():
    print("="*80)
    print("Phase 3: Calculate Alpha from Execution Time")
    print("="*80)
    print()

    # Load node specs
    nodes = load_node_specs()
    if not nodes:
        return

    print()

    # Load Native execution times
    print("Loading Native execution times...")
    native_exec = load_exec_times('native_tool_exec_time_*.json')

    print()

    # Load WASM execution times
    print("Loading WASM execution times...")
    wasm_exec = load_exec_times('wasm_tool_exec_time_*.json')

    print()

    # Generate profiles
    if native_exec:
        print("="*80)
        print("Generating Native Profile")
        print("="*80)
        generate_profile(native_exec, nodes, 'profile_native.yaml')

    print()

    if wasm_exec:
        print("="*80)
        print("Generating WASM Profile")
        print("="*80)
        generate_profile(wasm_exec, nodes, 'profile_wasm.yaml')

    print()
    print("="*80)
    print("✓ All done!")
    print("="*80)


if __name__ == "__main__":
    main()
