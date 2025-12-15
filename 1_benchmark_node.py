#!/usr/bin/env python3
"""
Phase 1: Network Bandwidth Measurement

각 노드에서 네트워크 대역폭 측정 (Alpha 계산용)

Usage:
    export IPERF_SERVER=<server-ip>
    python3 1_benchmark_node.py

Output:
    - node_<hostname>.yaml
"""

import subprocess
import yaml
import socket
import platform
import os
import json
import time
from pathlib import Path


def measure_latency(target_host, port=80, runs=10):
    """
    Measure network latency using TCP connection time

    Args:
        target_host: Target IP or hostname
        port: TCP port to connect to (default: 80 for HTTP)
        runs: Number of measurements to average

    Returns:
        latency_ms: Average latency in milliseconds
    """
    print("\n" + "="*60)
    print("Network Latency Measurement")
    print("="*60)
    print(f"Measuring TCP connection time to {target_host}:{port}")
    print()

    latencies = []

    for i in range(runs):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((target_host, port))
            end = time.time()
            sock.close()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        except (socket.timeout, socket.error) as e:
            print(f"⚠️  Connection failed: {e}")
            continue

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        print(f"Measurements: {len(latencies)}/{runs}")
        print(f"✓ Average latency: {avg_latency:.3f} ms")
        print(f"  Min: {min_latency:.3f} ms, Max: {max_latency:.3f} ms")
        return avg_latency
    else:
        print(f"⚠️  All measurements failed")
        print(f"   Using default: 50.0 ms")
        return 50.0


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

    # Get server host and port from environment or use default
    server_host = os.getenv('IPERF_SERVER', '10.2.0.1')
    server_port = os.getenv('IPERF_PORT', '5201')

    print(f"Testing to server: {server_host}:{server_port}")
    print("Make sure iperf3 server is running:")
    print(f"  ssh {server_host} 'iperf3 -s -p {server_port} -D'")
    print()

    try:
        # Run iperf3 client
        cmd = ['iperf3', '-c', server_host, '-p', server_port, '-t', '5', '-J']
        print("Running test (5 seconds)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

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
    print(f"Network Benchmark - {hostname}")
    print("="*60)
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print()

    # Get target server from environment
    target_server = os.getenv('IPERF_SERVER', '10.2.0.1')
    latency_port = int(os.getenv('LATENCY_PORT', '80'))

    # Measure network bandwidth
    network_bw = benchmark_network()

    # Measure network latency
    network_latency = measure_latency(target_server, port=latency_port)

    # Print results
    print("\n" + "="*60)
    print("Results")
    print("="*60)
    print(f"Network Bandwidth:  {network_bw:.2f} Mbps")
    print(f"Network Latency:    {network_latency:.3f} ms")

    # Save to YAML
    node_data = {
        'hostname': hostname,
        'os': platform.system(),
        'machine': platform.machine(),
        'network_bandwidth_mbps': network_bw,
        'network_latency_ms': network_latency,
        'target_server': target_server,
    }

    output_file = f'node_{hostname}.yaml'
    with open(output_file, 'w') as f:
        yaml.dump(node_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Results saved: {output_file}")

    print("\n" + "="*60)
    print("✓ Measurement complete!")
    print("="*60)


if __name__ == "__main__":
    main()
