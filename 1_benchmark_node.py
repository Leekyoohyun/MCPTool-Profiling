#!/usr/bin/env python3
"""
Phase 1: Node Performance Benchmark

각 노드에서 하드웨어 성능 측정:
- Peak FLOPS (GFLOPS)
- Memory Bandwidth (GB/s)
- Ridge Point = FLOPS / Memory_BW
- Network Bandwidth (Mbps)

Usage:
    python3 1_benchmark_node.py

Output:
    - node_<hostname>.yaml
"""

import subprocess
import re
import yaml
import socket
import platform
import os
import json
from pathlib import Path


def run_command(cmd, description):
    """Run command and return output"""
    print(f"  Running: {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            print(f"  ⚠️  Warning: {description} failed")
            print(f"     {result.stderr}")
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Timeout: {description}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def benchmark_cpu():
    """Measure Peak FLOPS"""
    print("\n" + "="*60)
    print("CPU Benchmark (Peak FLOPS)")
    print("="*60)

    output = run_command("./peak_flops 2048", "Peak FLOPS")
    if output:
        match = re.search(r'Peak GFLOPS:\s+([\d.]+)', output)
        if match:
            return float(match.group(1))
    return None


def benchmark_memory():
    """Measure Memory Bandwidth"""
    print("\n" + "="*60)
    print("Memory Benchmark (STREAM Triad)")
    print("="*60)

    output = run_command("./memory_bandwidth", "Memory Bandwidth")
    if output:
        match = re.search(r'Triad \(Best\):\s+([\d.]+)', output)
        if match:
            return float(match.group(1))
    return None


def benchmark_network():
    """
    Benchmark network bandwidth using iperf3

    Returns:
        bandwidth_mbps: Network bandwidth in Mbps
    """
    print("\n" + "="*60)
    print("Network Bandwidth Benchmark")
    print("="*60)
    print("Using iperf3 to measure network throughput")
    print()

    # Check if iperf3 is available
    try:
        result = subprocess.run(['which', 'iperf3'], capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️  iperf3 not found")
            print("   Install: sudo apt-get install iperf3")
            print("   Using default: 100 Mbps")
            return 100.0
    except Exception:
        print("⚠️  iperf3 not available, using default 100 Mbps")
        return 100.0

    # Get server host from environment or use default
    server_host = os.getenv('IPERF_SERVER', '10.2.0.1')

    print(f"Testing to server: {server_host}")
    print("Make sure iperf3 server is running:")
    print(f"  ssh {server_host} 'iperf3 -s -D'")
    print()

    try:
        # Run iperf3 client
        cmd = ['iperf3', '-c', server_host, '-t', '5', '-J']
        print("Running test (5 seconds)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Parse JSON output
            import json
            data = json.loads(result.stdout)
            bandwidth_bps = data['end']['sum_sent']['bits_per_second']
            bandwidth_mbps = bandwidth_bps / 1e6

            print(f"✓ Bandwidth: {bandwidth_mbps:.2f} Mbps")
            return bandwidth_mbps
        else:
            print(f"⚠️  iperf3 failed: {result.stderr}")
            print("   Using default: 100 Mbps")
            return 100.0

    except subprocess.TimeoutExpired:
        print("⚠️  Network test timed out")
        print("   Using default: 100 Mbps")
        return 100.0
    except Exception as e:
        print(f"⚠️  Network test error: {e}")
        print("   Using default: 100 Mbps")
        return 100.0


def main():
    hostname = socket.gethostname()

    print("="*60)
    print(f"Node Performance Benchmark - {hostname}")
    print("="*60)
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print()

    # Compile benchmarks
    print("Compiling benchmarks...")
    result = subprocess.run(['make'], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Make failed:")
        print(result.stderr)
        return

    # Run benchmarks
    peak_flops = benchmark_cpu()
    memory_bw = benchmark_memory()
    network_bw = benchmark_network()

    # Calculate ridge point
    ridge_point = None
    if peak_flops and memory_bw:
        ridge_point = peak_flops / memory_bw

    # Print results
    print("\n" + "="*60)
    print("Benchmark Results")
    print("="*60)
    if peak_flops:
        print(f"Peak FLOPS:        {peak_flops:.1f} GFLOPS")
    if memory_bw:
        print(f"Memory Bandwidth:  {memory_bw:.1f} GB/s")
    if ridge_point:
        print(f"Ridge Point:       {ridge_point:.2f} FLOPS/Byte")
    if network_bw:
        print(f"\nNetwork:")
        print(f"  Bandwidth:       {network_bw:.2f} Mbps")

    # Save to YAML
    node_data = {
        'hostname': hostname,
        'os': platform.system(),
        'machine': platform.machine(),
        'peak_flops': peak_flops,
        'memory_bw': memory_bw,
        'ridge_point': ridge_point,
        'network_bandwidth_mbps': network_bw,
    }

    output_file = f'node_{hostname}.yaml'
    with open(output_file, 'w') as f:
        yaml.dump(node_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Results saved: {output_file}")

    print("\n" + "="*60)
    print("✓ Benchmark complete!")
    print("="*60)


if __name__ == "__main__":
    main()
