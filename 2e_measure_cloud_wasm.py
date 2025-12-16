#!/usr/bin/env python3
"""
Phase 2E: Measure Cloud WASM Tool Execution Time

클라우드에서 WASM 서버로 tool 실행 시간 측정
- Edge와 동일한 WASM 사용 (MCP 클라이언트 라이브러리 사용)
- 동일한 50MB 표준 payload 사용
- 공정한 비교 가능

Usage:
    python3 2e_measure_cloud_wasm.py

Output:
    - cloud_wasm_tool_exec_time_<hostname>.json

Requirements:
    - wasmtime 설치: curl https://wasmtime.dev/install.sh -sSf | bash
    - WASM 빌드: cd wasm_mcp && cargo build --target wasm32-wasip2 --release
    - pip install langchain-mcp-adapters
"""

import asyncio
import json
import time
import sys
import socket
import os
from pathlib import Path

# Import standard payloads
sys.path.insert(0, str(Path(__file__).parent))
from standard_payloads import get_standard_payloads

# WASM MCP test utilities path (for MCPServerConfig)
WASM_MCP_TEST_PATH_CANDIDATES = [
    Path.home() / "CCGrid-2026/EdgeAgent/EdgeAgent/wasm_mcp/tests",  # AWS EC2
    Path.home() / "EdgeAgent/wasm_mcp/tests",  # Nodes
    Path.home() / "DDPS/undergraduated/CCGrid-2026/EdgeAgent/EdgeAgent/wasm_mcp/tests",  # MacBook
]

# Add wasm_mcp/tests to path for MCPServerConfig
for test_path in WASM_MCP_TEST_PATH_CANDIDATES:
    if test_path.exists():
        sys.path.insert(0, str(test_path))
        break

# Import MCP client libraries (same as 2b_measure_simple_tools.py)
try:
    from mcp_comparator import MCPServerConfig, TransportType
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
except ImportError as e:
    print(f"❌ Missing required library: {e}")
    print("\nInstall required packages:")
    print("  pip install langchain-mcp-adapters")
    print("\nEnsure wasm_mcp/tests is in path for MCPServerConfig")
    sys.exit(1)

# WASM server path
WASM_PATH_CANDIDATES = [
    Path.home() / "CCGrid-2026/EdgeAgent/EdgeAgent/wasm_mcp/target/wasm32-wasip2/release",  # AWS EC2
    Path.home() / "EdgeAgent/wasm_mcp/target/wasm32-wasip2/release",  # Nodes
    Path.home() / "DDPS/undergraduated/CCGrid-2026/EdgeAgent/EdgeAgent/wasm_mcp/target/wasm32-wasip2/release",  # MacBook
]

# Check environment variable first
env_wasm_path = os.environ.get('WASM_PATH', '')
if env_wasm_path:
    WASM_PATH_CANDIDATES.insert(0, Path(env_wasm_path))

WASM_PATH = None
for path in WASM_PATH_CANDIDATES:
    if path.exists() and list(path.glob('*.wasm')):
        WASM_PATH = path
        break

if WASM_PATH is None:
    print("❌ WASM files not found!")
    print("   Set WASM_PATH environment variable:")
    print("   export WASM_PATH=/path/to/wasm_mcp/target/wasm32-wasip2/release")
    print()
    print("   Or build WASM:")
    print("   cd EdgeAgent/wasm_mcp && cargo build --target wasm32-wasip2 --release")
    WASM_PATH = WASM_PATH_CANDIDATES[1]  # Default fallback

# Server WASM file mapping
SERVER_WASM_MAP = {
    'filesystem': 'mcp_server_filesystem.wasm',
    'git': 'mcp_server_git.wasm',
    'fetch': 'mcp_server_fetch.wasm',
    'time': 'mcp_server_time.wasm',
    'data_aggregate': 'mcp_server_data_aggregate.wasm',
    'image_resize': 'mcp_server_image_resize.wasm',
    'log_parser': 'mcp_server_log_parser.wasm',
    'summarize': 'mcp_server_summarize.wasm',
    'sequentialthinking': 'mcp_server_sequential_thinking.wasm',
}

# Tools by server - ALL servers (same as Edge measurement)
TOOLS_BY_SERVER = {
    'time': ['get_current_time', 'convert_time'],
    'sequentialthinking': ['sequentialthinking'],
    'fetch': ['fetch'],
    'filesystem': ['read_file', 'read_text_file', 'read_media_file', 'read_multiple_files', 'write_file',
                   'edit_file', 'create_directory', 'list_directory', 'list_directory_with_sizes',
                   'move_file', 'list_allowed_directories'],
    'git': ['git_status', 'git_diff_unstaged', 'git_diff_staged', 'git_diff', 'git_commit',
            'git_add', 'git_reset', 'git_log', 'git_show', 'git_branch'],
    'log_parser': ['parse_logs', 'filter_entries', 'compute_log_statistics', 'search_entries', 'extract_time_range'],
    'data_aggregate': ['aggregate_list', 'merge_summaries', 'combine_research_results', 'deduplicate', 'compute_trends'],
    'image_resize': ['get_image_info', 'resize_image', 'compute_image_hash', 'compare_hashes', 'batch_resize'],
    # 'summarize': ['summarize_text', 'summarize_documents', 'get_provider_info'],  # Requires API key + HTTP
}

# Number of runs per tool
NUM_RUNS = 3


async def measure_tool(session, tool_name, tool_func, arguments, runs=NUM_RUNS):
    """Measure tool execution time using MCP client"""
    exec_times = []
    output_size = 0

    for run in range(runs):
        try:
            start = time.perf_counter()
            result = await tool_func.ainvoke(arguments)
            end = time.perf_counter()

            exec_times.append(end - start)
            output_size = len(str(result))

        except Exception as e:
            print(f"\n    Run {run+1} failed: {e}")
            continue

    return exec_times, output_size


async def measure_server_tools(server_name, tool_names, test_payloads, runs=NUM_RUNS):
    """Measure all tools for a single WASM server using MCP client"""

    wasm_file = WASM_PATH / SERVER_WASM_MAP.get(server_name, '')
    if not wasm_file.exists():
        print(f"  ⚠️  WASM file not found: {wasm_file}")
        return []

    print(f"\n{'='*60}")
    print(f"Server: {server_name} ({len(tool_names)} tools) - WASM")
    print(f"WASM: {wasm_file.name}")
    print(f"{'='*60}")

    results = []

    try:
        # Create MCP server config for WASM (same as 2b_measure_simple_tools.py)
        server_config = MCPServerConfig.wasmmcp_stdio("/tmp", str(wasm_file))

        # Create MCP client
        client = MultiServerMCPClient({server_name: server_config.config})

        async with client.session(server_name) as session:
            # Load tools
            tools = await load_mcp_tools(session)
            tool_map = {t.name: t for t in tools}

            available_tools = list(tool_map.keys())
            print(f"  Available tools: {available_tools}")

            for tool_name in tool_names:
                if tool_name not in test_payloads:
                    print(f"  ⚠️  {tool_name}: No test payload")
                    continue

                if tool_name not in tool_map:
                    print(f"  ⚠️  {tool_name}: Not found in server")
                    continue

                print(f"  Measuring {tool_name}...", end=' ', flush=True)

                payload = test_payloads[tool_name]

                # Calculate input size (same as Edge measurement)
                if tool_name in ['get_image_info', 'resize_image', 'compute_image_hash', 'batch_resize']:
                    input_size = 50 * 1024 * 1024  # 50MB image
                elif tool_name in ['read_file', 'read_text_file', 'read_media_file']:
                    input_size = 50 * 1024 * 1024  # 50MB file
                elif tool_name == 'read_multiple_files':
                    input_size = 100 * 1024 * 1024  # 2x 50MB files
                elif tool_name == 'sequentialthinking':
                    input_size = 50 * 1024 * 1024  # Record 50MB for fair comparison
                else:
                    input_size = len(json.dumps(payload))

                tool_func = tool_map[tool_name]
                exec_times, output_size = await measure_tool(session, tool_name, tool_func, payload, runs)

                if exec_times:
                    avg_exec_time = sum(exec_times) / len(exec_times)
                    results.append({
                        'tool_name': tool_name,
                        'server': server_name,
                        't_exec': avg_exec_time,  # seconds
                        'input_size': input_size,
                        'output_size': output_size,
                        'runs': len(exec_times),
                        'measurements': exec_times  # seconds
                    })
                    print(f"✓ {avg_exec_time:.3f}s ({avg_exec_time*1000:.1f}ms)")
                else:
                    print(f"❌ All runs failed")

    except Exception as e:
        print(f"  ❌ Server error: {e}")
        import traceback
        traceback.print_exc()

    return results


async def main():
    print("="*60)
    print("Phase 2E: Cloud WASM Tool Measurement")
    print("="*60)
    print()

    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print()

    print(f"WASM Path: {WASM_PATH}")
    if WASM_PATH and WASM_PATH.exists():
        wasm_files = list(WASM_PATH.glob('*.wasm'))
        print(f"  Found {len(wasm_files)} WASM files")
        for wf in sorted(wasm_files)[:5]:
            print(f"    ✓ {wf.name}")
        if len(wasm_files) > 5:
            print(f"    ... and {len(wasm_files) - 5} more")
    else:
        print("  ⚠️  WASM path does not exist!")
        return
    print()

    # Count total tools
    total_tools = sum(len(tools) for tools in TOOLS_BY_SERVER.values())
    print(f"Total tools to measure: {total_tools}")
    print(f"Runs per tool: {NUM_RUNS}")
    print()

    # Load standard payloads
    test_payloads = get_standard_payloads()
    all_results = []

    # Measure each server
    for server_name, tool_names in TOOLS_BY_SERVER.items():
        try:
            results = await measure_server_tools(server_name, tool_names, test_payloads, runs=NUM_RUNS)
            all_results.extend(results)
        except Exception as e:
            print(f"  ❌ Server {server_name} failed: {e}")

    # Save results
    output_file = f'cloud_wasm_tool_exec_time_{hostname}.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print()
    print("="*60)
    print(f"✓ Results saved: {output_file}")
    print(f"  Measured {len(all_results)}/{total_tools} tools")
    print("="*60)

    # Summary
    if all_results:
        print("\nSummary:")
        print(f"{'Tool':<30s} {'Time (ms)':>10s} {'Input':>14s} {'Output':>14s}")
        print("-" * 70)
        for r in all_results:
            print(f"  {r['tool_name']:<28s} {r['t_exec']*1000:>8.1f}ms {r['input_size']:>12,}B {r['output_size']:>12,}B")


if __name__ == "__main__":
    asyncio.run(main())
