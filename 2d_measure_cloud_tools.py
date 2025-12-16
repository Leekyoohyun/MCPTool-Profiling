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

# NPM-based MCP servers
NPM_SERVERS = {
    'filesystem': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-filesystem', '/tmp'],
    },
    'git': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-git', '--repository', '/tmp/git_repo'],
    },
    'fetch': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-fetch'],
    },
    'time': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-time'],
    },
    'sequentialthinking': {
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-sequential-thinking'],
    },
}

# Tools by server - ALL servers (same as Edge measurement)
TOOLS_BY_SERVER = {
    # NPM servers
    'time': ['get_current_time', 'convert_time'],
    'sequentialthinking': ['sequentialthinking'],
    'fetch': ['fetch'],
    'filesystem': ['read_file', 'read_text_file', 'read_media_file', 'read_multiple_files', 'write_file',
                   'edit_file', 'create_directory', 'list_directory', 'list_directory_with_sizes',
                   'move_file', 'list_allowed_directories'],
    'git': ['git_status', 'git_diff_unstaged', 'git_diff_staged', 'git_diff', 'git_commit',
            'git_add', 'git_reset', 'git_log', 'git_show', 'git_branch'],
    # Python servers
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

    # Determine server type and create params
    if server_name in PYTHON_SERVERS:
        server_file = EDGEAGENT_PATH / 'servers' / PYTHON_SERVERS[server_name]
        if not server_file.exists():
            print(f"  ⚠️  Server not found: {server_file}")
            return []
        server_params = StdioServerParameters(
            command="python3",
            args=[str(server_file)],
            env=os.environ.copy()
        )
        server_type = "Native Python"
        server_info = str(server_file)
    elif server_name in NPM_SERVERS:
        npm_config = NPM_SERVERS[server_name]
        server_params = StdioServerParameters(
            command=npm_config['command'],
            args=npm_config['args'],
            env=os.environ.copy()
        )
        server_type = "NPM"
        server_info = f"{npm_config['command']} {' '.join(npm_config['args'][:2])}..."
    else:
        print(f"  ⚠️  Server not supported: {server_name}")
        return []

    print(f"\n{'='*60}")
    print(f"Server: {server_name} ({len(tool_names)} tools) - {server_type}")
    print(f"Command: {server_info}")
    print(f"{'='*60}")

    results = []

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
        for name, script in PYTHON_SERVERS.items():
            server_file = servers_path / script
            status = "✓" if server_file.exists() else "✗"
            print(f"  {status} {name}: {script}")
    else:
        print(f"⚠️  Python servers not found at: {servers_path}")

    # Check NPM servers
    print(f"\n✓ NPM servers (will be downloaded on first use):")
    for name in NPM_SERVERS.keys():
        print(f"  ✓ {name}")
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
