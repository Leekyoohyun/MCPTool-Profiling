#!/usr/bin/env python3
"""
Phase 2: Tool Operational Intensity (OI) Measurement

Linux perf를 사용하여 각 Tool의 OI 측정:
- OI = Instructions / (Cache Misses × 64)
- 64 = Typical cache line size

Requirements:
    - Linux OS (perf 필요)
    - sudo 권한 (perf 실행용)
    - MCP 서버 실행 가능

Usage:
    python3 2_measure_tool_oi.py

Output:
    - tool_oi_measurements.json
"""

import asyncio
import subprocess
import json
import signal
import time
import psutil
from pathlib import Path
import sys

# Tool definitions 임포트
sys.path.insert(0, str(Path(__file__).parent))
from utils.tool_definitions import TOOLS, get_all_tools


CACHE_LINE_SIZE = 64  # bytes
RUNS_PER_TOOL = 3


def check_perf_available():
    """Check if perf is available"""
    try:
        result = subprocess.run(['perf', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ perf available: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("❌ perf not found!")
    print("\nInstall perf:")
    print("  Ubuntu/Debian: sudo apt-get install linux-tools-generic")
    print("  Fedora/RHEL:   sudo dnf install perf")
    return False


def setup_perf_permissions():
    """Setup perf permissions"""
    try:
        # Check current paranoid level
        with open('/proc/sys/kernel/perf_event_paranoid', 'r') as f:
            level = int(f.read().strip())

        if level > -1:
            print(f"\n⚠️  perf_event_paranoid = {level} (needs -1)")
            print("Run: sudo sysctl -w kernel.perf_event_paranoid=-1")
            return False

        print("✓ perf permissions OK")
        return True

    except Exception as e:
        print(f"⚠️  Could not check perf permissions: {e}")
        return True  # Continue anyway


def measure_tool_with_perf(server_process, tool_name, tool_args):
    """
    Measure a single tool execution with perf

    Returns:
        dict with instructions, cache_misses, oi
    """
    pid = server_process.pid

    # perf stat command
    perf_cmd = [
        'perf', 'stat',
        '-e', 'instructions,cache-misses',
        '-p', str(pid),
        '--',
        'sleep', '0.1'  # Short duration to capture events
    ]

    try:
        # Start perf monitoring
        perf_proc = subprocess.Popen(
            perf_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait briefly for perf to attach
        time.sleep(0.05)

        # Execute the tool (this would be actual MCP tool call)
        # For now, we'll simulate with sleep
        # TODO: Replace with actual MCP client call
        time.sleep(0.2)

        # Wait for perf to finish
        perf_proc.wait(timeout=5)

        # Parse perf output
        output = perf_proc.stderr.read()

        instructions = None
        cache_misses = None

        for line in output.split('\n'):
            if 'instructions' in line:
                parts = line.split()
                if parts:
                    instructions = int(parts[0].replace(',', ''))
            elif 'cache-misses' in line:
                parts = line.split()
                if parts:
                    cache_misses = int(parts[0].replace(',', ''))

        if instructions and cache_misses:
            # OI = Instructions / (Cache Misses × Cache Line Size)
            memory_bytes = cache_misses * CACHE_LINE_SIZE
            oi = instructions / memory_bytes if memory_bytes > 0 else 0

            return {
                'instructions': instructions,
                'cache_misses': cache_misses,
                'memory_bytes': memory_bytes,
                'oi': oi
            }

    except Exception as e:
        print(f"    ⚠️  perf measurement failed: {e}")

    return None


async def measure_tool_real(tool_name, tool_info):
    """
    Real tool measurement using perf

    TODO: Implement actual MCP server execution with perf monitoring
    For now, returns None to indicate measurement needed
    """
    # This would require:
    # 1. Start MCP server
    # 2. Attach perf to server process
    # 3. Execute tool via MCP client
    # 4. Collect perf stats
    # 5. Calculate OI from instructions and cache misses

    return None  # Indicate measurement not yet implemented


async def main():
    print("="*60)
    print("Tool Operational Intensity (OI) Measurement")
    print("="*60)
    print()

    # Check perf availability
    if not check_perf_available():
        print("\n❌ ERROR: perf not available")
        print("\nThis script MUST run on Linux with perf installed.")
        print("\nInstall perf:")
        print("  Ubuntu/Debian: sudo apt-get install linux-tools-generic")
        print("  Fedora/RHEL:   sudo dnf install perf")
        print("\nThen run:")
        print("  sudo sysctl -w kernel.perf_event_paranoid=-1")
        print("  python3 2_measure_tool_oi.py")
        return

    setup_perf_permissions()

    print("\n" + "="*60)
    print("⚠️  IMPLEMENTATION REQUIRED")
    print("="*60)
    print("""
This script requires implementation of:
1. MCP server startup for each tool
2. perf monitoring integration
3. Actual tool execution via MCP client
4. OI calculation from perf counters

Current status: Framework only (실측 구현 필요)

For now, you must:
1. Manually measure OI for each tool using perf
2. Create tool_oi_measurements.json with format:
   [
     {
       "tool_name": "resize_image",
       "server": "image_resize",
       "description": "...",
       "operational_intensity": 8.5,
       "runs": 3
     },
     ...
   ]
3. Then run: python3 3_calculate_alpha.py
""")



if __name__ == "__main__":
    asyncio.run(main())
