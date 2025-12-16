#!/usr/bin/env python3
"""
Phase 2D: Measure Cloud Tool Execution Time (Native Python MCP Servers)

클라우드에서 Native Python MCP 서버로 tool 실행 시간 측정
- WASM이 아닌 Native Python 서버 사용
- 동일한 50MB 표준 payload 사용
- Edge 노드와 동일한 JSON 형식으로 저장

Usage:
    python3 2d_measure_cloud_tools.py

Output:
    - cloud_tool_exec_time_<hostname>.json

Requirements:
    pip install mcp
"""

import asyncio
import json
import socket
import sys
import time
import os
from pathlib import Path

# Import MCP client (same as EdgeAgent-Profiling-for-coremark-v1)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import standard payloads
sys.path.insert(0, str(Path(__file__).parent))
from standard_payloads import get_standard_payloads

# Load .env file
def load_env_file(env_path=None):
    """Load API keys from .env file"""
    if env_path is None:
        env_path = Path(__file__).parent / ".env"

    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

ENV_VARS = load_env_file()

# Set environment variables for API keys
if ENV_VARS.get('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY'] = ENV_VARS['OPENAI_API_KEY']
if ENV_VARS.get('ANTHROPIC_API_KEY'):
    os.environ['ANTHROPIC_API_KEY'] = ENV_VARS['ANTHROPIC_API_KEY']

# EdgeAgent path (for Python MCP servers)
# Can be overridden with EDGEAGENT_PATH environment variable
EDGEAGENT_PATH_CANDIDATES = [
    Path(os.environ.get('EDGEAGENT_PATH', '')),  # Environment variable (highest priority)
    Path.home() / "CCGrid-2026/EdgeAgent/EdgeAgent",  # AWS EC2: /home/ubuntu/CCGrid-2026/EdgeAgent/EdgeAgent
    Path.home() / "EdgeAgent",  # Cloud: ~/EdgeAgent
    Path.home() / "DDPS/undergraduated/CCGrid-2026/EdgeAgent/EdgeAgent",  # MacBook
]

EDGEAGENT_PATH = None
for path in EDGEAGENT_PATH_CANDIDATES:
    if path and path.exists() and (path / "servers").exists():
        EDGEAGENT_PATH = path
        break

if EDGEAGENT_PATH is None:
    print("❌ EdgeAgent not found!")
    print("   Set EDGEAGENT_PATH environment variable:")
    print("   export EDGEAGENT_PATH=/path/to/EdgeAgent")
    print()
    print("   Or ensure EdgeAgent is in one of these locations:")
    for p in EDGEAGENT_PATH_CANDIDATES[1:]:
        print(f"   - {p}")
    EDGEAGENT_PATH = EDGEAGENT_PATH_CANDIDATES[1]  # Default fallback


# Python-based servers (custom EdgeAgent servers)
PYTHON_SERVERS = {
    'log_parser': 'log_parser_server.py',
    'data_aggregate': 'data_aggregate_server.py',
    'image_resize': 'image_resize_server.py',
    'summarize': 'summarize_server.py',
}

# Tools by server (Python servers only - no NPM servers for cloud)
TOOLS_BY_SERVER = {
    'log_parser': ['parse_logs', 'filter_entries', 'compute_log_statistics', 'search_entries', 'extract_time_range'],
    'data_aggregate': ['aggregate_list', 'merge_summaries', 'combine_research_results', 'deduplicate', 'compute_trends'],
    'image_resize': ['get_image_info', 'resize_image', 'compute_image_hash', 'compare_hashes', 'batch_resize'],
    # 'summarize': ['summarize_text', 'summarize_documents', 'get_provider_info'],  # Optional: requires API key
}

# Number of runs per tool
NUM_RUNS = 3


async def measure_tool(session, tool_name, arguments, runs=NUM_RUNS):
    """Measure tool execution time"""
    exec_times = []
    output_size = 0

    for run in range(runs):
        try:
            start = time.perf_counter()
            result = await session.call_tool(tool_name, arguments=arguments)
            end = time.perf_counter()

            exec_times.append(end - start)

            # Calculate output size from result
            if result and hasattr(result, 'content'):
                output_size = len(json.dumps([c.text if hasattr(c, 'text') else str(c) for c in result.content]))
            else:
                output_size = len(str(result))

        except Exception as e:
            print(f"\n    Run {run+1} failed: {e}")
            continue

    return exec_times, output_size


async def measure_server_tools(server_name, tool_names, test_payloads, runs=NUM_RUNS):
    """Measure all tools for a single server"""

    if server_name not in PYTHON_SERVERS:
        print(f"  ⚠️  Server not supported: {server_name}")
        return []

    server_file = EDGEAGENT_PATH / 'servers' / PYTHON_SERVERS[server_name]
    if not server_file.exists():
        print(f"  ⚠️  Server not found: {server_file}")
        return []

    print(f"\n{'='*60}")
    print(f"Server: {server_name} ({len(tool_names)} tools) - Native Python")
    print(f"Path: {server_file}")
    print(f"{'='*60}")

    results = []

    # Create server params
    server_params = StdioServerParameters(
        command="python3",
        args=[str(server_file)],
        env=os.environ.copy()
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await asyncio.sleep(0.5)  # Warmup

                # Get available tools
                tools_response = await session.list_tools()
                available_tools = [t.name for t in tools_response.tools]
                print(f"  Available tools: {available_tools}")

                for tool_name in tool_names:
                    if tool_name not in test_payloads:
                        print(f"  ⚠️  {tool_name}: No test payload")
                        continue

                    if tool_name not in available_tools:
                        print(f"  ⚠️  {tool_name}: Not found in server")
                        continue

                    print(f"  Measuring {tool_name}...", end=' ', flush=True)

                    payload = test_payloads[tool_name]

                    # Calculate input size
                    if tool_name in ['get_image_info', 'resize_image', 'compute_image_hash', 'batch_resize']:
                        input_size = 50 * 1024 * 1024  # 50MB image
                    else:
                        input_size = len(json.dumps(payload))

                    exec_times, output_size = await measure_tool(session, tool_name, payload, runs)

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
    print("Phase 2D: Cloud Tool Measurement (Native Python)")
    print("="*60)
    print()

    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print(f"EdgeAgent Path: {EDGEAGENT_PATH}")
    print()

    # Check Python servers
    servers_path = EDGEAGENT_PATH / 'servers'
    if servers_path.exists():
        print(f"✓ Python servers found at: {servers_path}")
        # List available servers
        for name, script in PYTHON_SERVERS.items():
            server_file = servers_path / script
            status = "✓" if server_file.exists() else "✗"
            print(f"  {status} {name}: {script}")
    else:
        print(f"⚠️  Python servers not found at: {servers_path}")
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
            results = await measure_server_tools(server_name, tool_names, test_payloads)
            all_results.extend(results)
        except Exception as e:
            print(f"  ❌ Server {server_name} failed: {e}")

    # Save results
    output_file = f'cloud_tool_exec_time_{hostname}.json'
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
