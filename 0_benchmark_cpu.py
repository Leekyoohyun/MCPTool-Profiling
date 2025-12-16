#!/usr/bin/env python3
"""
Phase 0: CPU & Memory Benchmark

각 노드의 CPU 성능과 메모리 대역폭 측정

측정 항목:
- GFLOPS (부동소수점 연산 성능)
- Memory Bandwidth (메모리 읽기/쓰기 속도)
- CPU Info (코어 수, 주파수)

Usage:
    python3 0_benchmark_cpu.py

Output:
    - node_<hostname>.yaml (기존 파일에 추가)

Dependencies:
    pip install numpy pyyaml
    sudo apt-get install sysbench
"""

import subprocess
import yaml
import socket
import platform
import time
import multiprocessing
import re
import sys
from pathlib import Path

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("⚠️  numpy not installed. FLOPS measurement will be skipped.")
    print("   Install: pip install numpy")


def get_cpu_info():
    """Get CPU information"""
    print("\n" + "="*60)
    print("CPU Information")
    print("="*60)

    cpu_count = multiprocessing.cpu_count()
    machine = platform.machine()

    # Try to get CPU model from /proc/cpuinfo
    cpu_model = "Unknown"
    cpu_freq_mhz = 0

    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'model name' in line:
                    cpu_model = line.split(':')[1].strip()
                    break
                elif 'Model' in line and machine == 'aarch64':
                    cpu_model = line.split(':')[1].strip()
                    break

        # Get CPU frequency
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'cpu MHz' in line:
                    cpu_freq_mhz = float(line.split(':')[1].strip())
                    break
    except:
        pass

    print(f"CPU Model:  {cpu_model}")
    print(f"CPU Cores:  {cpu_count}")
    if cpu_freq_mhz > 0:
        print(f"CPU Freq:   {cpu_freq_mhz:.0f} MHz")

    return {
        'cpu_model': cpu_model,
        'cpu_cores': cpu_count,
        'cpu_freq_mhz': cpu_freq_mhz if cpu_freq_mhz > 0 else None,
    }


def measure_gflops(size=2000, iterations=50, runs=3):
    """
    Measure GFLOPS using numpy matrix multiplication (multiple runs, take max)

    Args:
        size: Matrix size (NxN)
        iterations: Number of iterations per run
        runs: Number of measurements (default: 3)

    Returns:
        gflops: Peak GFLOPS
    """
    if not HAS_NUMPY:
        print("\n⚠️  Skipping FLOPS measurement (numpy required)")
        return None

    print("\n" + "="*60)
    print("FLOPS Benchmark")
    print("="*60)
    print(f"Matrix size: {size}x{size}")
    print(f"Iterations:  {iterations} per run")
    print(f"Runs:        {runs}")
    print()

    # Create random matrices
    a = np.random.rand(size, size).astype(np.float64)
    b = np.random.rand(size, size).astype(np.float64)

    # Warmup
    print("Warming up...")
    for _ in range(5):
        c = np.dot(a, b)

    # Benchmark multiple times
    print("Running benchmark...")
    gflops_list = []

    for i in range(runs):
        start = time.time()
        for _ in range(iterations):
            c = np.dot(a, b)
        elapsed = time.time() - start

        # Matrix multiply: 2*N^3 FLOPs per iteration
        total_flops = 2 * (size ** 3) * iterations
        gflops = total_flops / elapsed / 1e9
        gflops_list.append(gflops)

        print(f"  Run {i+1}/{runs}: {gflops:.2f} GFLOPS ({elapsed:.2f}s)")

    peak_gflops = max(gflops_list)
    avg_gflops = sum(gflops_list) / len(gflops_list)

    print()
    print(f"✓ Peak GFLOPS: {peak_gflops:.2f}")
    print(f"  Average: {avg_gflops:.2f}")
    print(f"  Min: {min(gflops_list):.2f}, Max: {max(gflops_list):.2f}")

    return peak_gflops


def measure_memory_bandwidth(runs=3):
    """
    Measure memory bandwidth using sysbench (multiple runs, take max)

    Args:
        runs: Number of measurements (default: 3)

    Returns:
        bandwidth_mbps: Peak memory bandwidth in MiB/sec
    """
    print("\n" + "="*60)
    print("Memory Bandwidth Benchmark")
    print("="*60)

    # Check if sysbench is available
    try:
        result = subprocess.run(['which', 'sysbench'], capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️  sysbench not found")
            print("   Install: sudo apt-get install sysbench")
            return None
    except Exception:
        print("⚠️  sysbench not available")
        return None

    print(f"Running {runs} measurements (taking peak)...")
    print()

    bandwidths = []

    for i in range(runs):
        try:
            # Run sysbench memory test
            cmd = [
                'sysbench', 'memory',
                '--memory-block-size=1M',
                '--memory-total-size=10G',
                'run'
            ]

            print(f"  Run {i+1}/{runs}...", end=' ', flush=True)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # Parse output for bandwidth
                # Look for: "10240.00 MiB transferred (37472.03 MiB/sec)"
                match = re.search(r'\((\d+\.?\d*)\s+MiB/sec\)', result.stdout)
                if match:
                    bandwidth_mibps = float(match.group(1))
                    bandwidths.append(bandwidth_mibps)
                    print(f"{bandwidth_mibps:.2f} MiB/sec")
                else:
                    print("⚠️  Could not parse output")
            else:
                print(f"⚠️  Failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("⚠️  Timed out")
        except Exception as e:
            print(f"⚠️  Error: {e}")

    if bandwidths:
        peak_bw = max(bandwidths)
        avg_bw = sum(bandwidths) / len(bandwidths)
        print()
        print(f"✓ Peak Memory Bandwidth: {peak_bw:.2f} MiB/sec ({peak_bw/1024:.2f} GiB/sec)")
        print(f"  Average: {avg_bw:.2f} MiB/sec ({avg_bw/1024:.2f} GiB/sec)")
        print(f"  Min: {min(bandwidths):.2f}, Max: {max(bandwidths):.2f}")
        return peak_bw
    else:
        print("⚠️  All measurements failed")
        return None


def main():
    hostname = socket.gethostname()

    print("="*60)
    print(f"CPU & Memory Benchmark - {hostname}")
    print("="*60)
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")

    # Get CPU info
    cpu_info = get_cpu_info()

    # Measure GFLOPS
    gflops = measure_gflops(size=2000, iterations=50)

    # Measure memory bandwidth
    memory_bw = measure_memory_bandwidth()

    # Print summary
    print("\n" + "="*60)
    print("Benchmark Results")
    print("="*60)
    print(f"CPU Model:          {cpu_info['cpu_model']}")
    print(f"CPU Cores:          {cpu_info['cpu_cores']}")
    if cpu_info['cpu_freq_mhz']:
        print(f"CPU Frequency:      {cpu_info['cpu_freq_mhz']:.0f} MHz")
    if gflops:
        print(f"Peak GFLOPS:        {gflops:.2f}")
    if memory_bw:
        print(f"Memory Bandwidth:   {memory_bw:.2f} MiB/sec ({memory_bw/1024:.2f} GiB/sec)")

    # Load existing node_*.yaml if exists, otherwise create new
    output_file = f'node_{hostname}.yaml'

    if Path(output_file).exists():
        with open(output_file, 'r') as f:
            node_data = yaml.safe_load(f) or {}
        print(f"\n✓ Updating existing file: {output_file}")
    else:
        node_data = {
            'hostname': hostname,
            'os': platform.system(),
            'machine': platform.machine(),
        }
        print(f"\n✓ Creating new file: {output_file}")

    # Add CPU & memory benchmark data
    node_data.update(cpu_info)

    if gflops:
        node_data['peak_gflops'] = round(gflops, 2)

    if memory_bw:
        node_data['memory_bandwidth_mibps'] = round(memory_bw, 2)
        node_data['memory_bandwidth_gibps'] = round(memory_bw / 1024, 2)

    # Save to YAML
    with open(output_file, 'w') as f:
        yaml.dump(node_data, f, default_flow_style=False, sort_keys=False)

    print(f"✓ Results saved: {output_file}")

    print("\n" + "="*60)
    print("✓ Benchmark complete!")
    print("="*60)


if __name__ == "__main__":
    main()
