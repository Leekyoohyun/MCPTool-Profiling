#!/usr/bin/env python3
"""
Phase 2B: Measure Simple WASM Tools (no git/filesystem)

Git과 Filesystem을 제외한 나머지 도구들만 측정:
- Time (2개)
- Sequential Thinking (1개)
- Fetch (1개)
- Summarize (3개)
- Log Parser (5개)
- Data Aggregate (5개)
- Image Resize (6개)

총 23개 도구
"""

import asyncio
import json
import socket
import sys
import time
from pathlib import Path

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

# Load API keys
ENV_VARS = load_env_file()

# Import EdgeAgent's MCP comparator framework
sys.path.insert(0, str(Path.home() / "EdgeAgent/wasm_mcp/tests"))
from mcp_comparator import MCPServerConfig, TransportType

# Import MCP client
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# Import standard payloads
from standard_payloads import get_standard_payloads

# WASM path
WASM_PATH_CANDIDATES = [
    Path.home() / "EdgeAgent/wasm_mcp/target/wasm32-wasip2/release",  # Nodes
    Path.home() / "DDPS/undergraduated/CCGrid-2026/EdgeAgent/EdgeAgent/wasm_mcp/target/wasm32-wasip2/release",  # MacBook
]

WASM_PATH = None
for path in WASM_PATH_CANDIDATES:
    if path.exists():
        WASM_PATH = path
        break

if WASM_PATH is None:
    WASM_PATH = WASM_PATH_CANDIDATES[0]

# Server WASM mapping (no git/filesystem)
SERVER_WASM_MAP = {
    'time': 'mcp_server_time.wasm',
    'sequentialthinking': 'mcp_server_sequential_thinking.wasm',
    'fetch': 'mcp_server_fetch.wasm',
    'summarize': 'mcp_server_summarize.wasm',
    'log_parser': 'mcp_server_log_parser.wasm',
    'data_aggregate': 'mcp_server_data_aggregate.wasm',
    'image_resize': 'mcp_server_image_resize.wasm',
}

# Note: Using standard payloads from standard_payloads.py
# All payloads are standardized to ~2KB for fair comparison across nodes

# Tool definitions (no git/filesystem)
TOOLS_BY_SERVER = {
    'time': ['get_current_time', 'convert_time'],
    'sequentialthinking': ['sequentialthinking'],
    'fetch': ['fetch'],
    'summarize': ['summarize_text', 'summarize_documents', 'get_provider_info'],
    'log_parser': ['parse_logs', 'filter_entries', 'compute_log_statistics', 'search_entries', 'extract_time_range'],
    'data_aggregate': ['aggregate_list', 'merge_summaries', 'combine_research_results', 'deduplicate', 'compute_trends'],
    'image_resize': ['get_image_info', 'resize_image', 'compute_image_hash', 'compare_hashes', 'batch_resize'],
}


async def measure_server_tools(server_name, tool_names, test_payloads, runs=3):
    """Measure all tools for a single server"""

    wasm_file = WASM_PATH / SERVER_WASM_MAP.get(server_name)
    if not wasm_file.exists():
        print(f"  ⚠️  WASM file not found: {wasm_file}")
        return []

    print(f"\n{'='*60}")
    print(f"Server: {server_name} ({len(tool_names)} tools)")
    print(f"{'='*60}")

    results = []

    try:
        # Create MCP server config
        server_config = MCPServerConfig.wasmmcp_stdio("/tmp", str(wasm_file))

        # Add HTTP support for fetch/summarize
        if server_name in {'fetch', 'summarize'}:
            print(f"  ℹ️  Adding HTTP support for {server_name}")

            # Get API keys from .env file
            openai_key = ENV_VARS.get('OPENAI_API_KEY', '')
            anthropic_key = ENV_VARS.get('ANTHROPIC_API_KEY', '')

            args = ["run", "--wasi", "http", "--dir=/tmp"]
            if openai_key:
                print(f"  ✓ Using OpenAI API key: {openai_key[:10]}...")
                args.extend(["--env", f"OPENAI_API_KEY={openai_key}"])
            else:
                print(f"  ⚠️  No OpenAI API key found in .env file")

            if anthropic_key:
                print(f"  ✓ Using Anthropic API key: {anthropic_key[:10]}...")
                args.extend(["--env", f"ANTHROPIC_API_KEY={anthropic_key}"])

            args.append(str(wasm_file))
            server_config.config['args'] = args

        # Create client
        client = MultiServerMCPClient({server_name: server_config.config})

        async with client.session(server_name) as session:
            tools = await load_mcp_tools(session)
            tool_map = {t.name: t for t in tools}

            for tool_name in tool_names:
                if tool_name not in test_payloads:
                    print(f"  ⚠️  {tool_name}: No test payload")
                    continue

                if tool_name not in tool_map:
                    print(f"  ⚠️  {tool_name}: Not found in server")
                    continue

                print(f"  Measuring {tool_name}...", end=' ', flush=True)

                tool_obj = tool_map[tool_name]
                payload = test_payloads[tool_name]

                exec_times = []
                output_size = 0
                input_size = sys.getsizeof(json.dumps(payload))

                for run in range(runs):
                    try:
                        start = time.time()
                        result = await tool_obj.ainvoke(payload)
                        end = time.time()

                        exec_times.append(end - start)
                        output_size = sys.getsizeof(json.dumps(result))
                    except Exception as e:
                        print(f"\n    Run {run+1} failed: {e}")
                        continue

                if exec_times:
                    avg_exec_time = sum(exec_times) / len(exec_times)
                    results.append({
                        'tool_name': tool_name,
                        'server': server_name,
                        't_exec': avg_exec_time,
                        'input_size': input_size,
                        'output_size': output_size,
                        'runs': len(exec_times),
                        'measurements': exec_times
                    })
                    print(f"✓ {avg_exec_time:.3f}s")
                else:
                    print(f"❌ All runs failed")

        # Cleanup delay
        await asyncio.sleep(1.0)

    except Exception as e:
        print(f"  ❌ Server error: {e}")

    return results


async def main():
    print("="*60)
    print("Phase 2B: Simple Tools Measurement (no git/filesystem)")
    print("="*60)
    print()

    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print(f"WASM Path: {WASM_PATH}")
    print()

    # Count total tools
    total_tools = sum(len(tools) for tools in TOOLS_BY_SERVER.values())
    print(f"Total tools to measure: {total_tools}")
    print()

    test_payloads = get_standard_payloads()
    all_results = []

    # Measure each server
    for server_name, tool_names in TOOLS_BY_SERVER.items():
        results = await measure_server_tools(server_name, tool_names, test_payloads)
        all_results.extend(results)

    # Save results
    output_file = f'simple_tool_exec_time_{hostname}.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print()
    print("="*60)
    print(f"✓ Results saved: {output_file}")
    print(f"  Measured {len(all_results)}/{total_tools} tools")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
