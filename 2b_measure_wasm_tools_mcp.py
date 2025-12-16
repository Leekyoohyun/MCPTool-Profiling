#!/usr/bin/env python3
"""
Phase 2B: Measure WASM Tool Execution Time (using MCP client)

Uses EdgeAgent's MCP client framework to properly measure WASM tools
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

# Import tool definitions
sys.path.insert(0, str(Path(__file__).parent))
from utils.tool_definitions import get_all_tools

# Import standard payloads
from standard_payloads import get_standard_payloads

# Test data path
TEST_DATA_PATH = Path(__file__).parent / "test_data"

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

# Server WASM mapping
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

# Note: Using standard payloads from standard_payloads.py
# All payloads are standardized to ~2KB for fair comparison across nodes

# Removed get_test_payloads() - now using get_standard_payloads() instead


async def measure_server_tools(server_name, tools_to_measure, test_payloads, runs=3):
    """Measure all tools for a single server in one session"""

    # Get WASM file
    wasm_file = WASM_PATH / SERVER_WASM_MAP.get(server_name)
    if not wasm_file.exists():
        print(f"  ⚠️  WASM file not found for {server_name}: {wasm_file}")
        return []

    print(f"\n{'='*60}")
    print(f"Server: {server_name} ({len(tools_to_measure)} tools)")
    print(f"{'='*60}")

    results = []

    try:
        # Create MCP server config
        server_config = MCPServerConfig.wasmmcp_stdio("/tmp", str(wasm_file))

        # Add HTTP support for fetch/summarize servers
        http_required_servers = {'fetch', 'summarize'}
        if server_name in http_required_servers:
            print(f"  ℹ️  Adding HTTP support for {server_name}")

            # Get API keys from .env file
            openai_key = ENV_VARS.get('OPENAI_API_KEY', '')
            anthropic_key = ENV_VARS.get('ANTHROPIC_API_KEY', '')

            # Build args with environment variables
            args = ["run", "--wasi", "http", "--dir=/tmp"]

            # Pass API keys to WASM if available
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

        # Create client and open session once for all tools
        client = MultiServerMCPClient({server_name: server_config.config})

        async with client.session(server_name) as session:
            # Load tools once
            tools = await load_mcp_tools(session)

            # Create tool map
            tool_map = {t.name: t for t in tools}

            # Measure each tool
            for tool_info in tools_to_measure:
                tool_name = tool_info['name']

                if tool_name not in test_payloads:
                    print(f"  ⚠️  {tool_name}: No test payload, skipping")
                    continue

                payload = test_payloads[tool_name]

                if tool_name not in tool_map:
                    print(f"  ⚠️  {tool_name}: Tool not found in server")
                    continue

                print(f"  Measuring {tool_name}...")

                tool_obj = tool_map[tool_name]
                exec_times = []
                output_size = 0
                input_size = sys.getsizeof(json.dumps(payload))

                # Run multiple times
                for run in range(runs):
                    try:
                        start = time.time()
                        result = await tool_obj.ainvoke(payload)
                        end = time.time()

                        exec_times.append(end - start)
                        output_size = sys.getsizeof(json.dumps(result))
                    except Exception as e:
                        print(f"    ⚠️  Run {run+1} failed: {e}")
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
                    print(f"    ✓ {avg_exec_time*1000:.1f}ms (avg of {len(exec_times)} runs)")
                else:
                    print(f"    ❌ All runs failed")

        # Give WASM time to clean up resources
        await asyncio.sleep(2.0)

    except Exception as e:
        print(f"  ❌ Server error: {e}")

    return results


async def main():
    print("="*60)
    print("Phase 2B: WASM Tool Execution Time Measurement (MCP)")
    print("="*60)
    print()

    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print()

    print("WASM servers location:")
    print(f"  {WASM_PATH}")
    print()

    print("Test data location:")
    print(f"  /tmp/")
    print()

    # Get test payloads
    TEST_PAYLOADS = get_standard_payloads()

    # Group tools by server
    all_tools = get_all_tools()
    tools_by_server = {}
    for tool in all_tools:
        server_name = tool['server']
        if server_name not in tools_by_server:
            tools_by_server[server_name] = []
        tools_by_server[server_name].append(tool)

    print(f"Total: {len(all_tools)} tools across {len(tools_by_server)} servers")
    print()

    all_results = []

    # Measure each server
    for server_name, tools in tools_by_server.items():
        results = await measure_server_tools(server_name, tools, TEST_PAYLOADS)
        all_results.extend(results)

    # Save results
    output_file = f'wasm_tool_exec_time_{hostname}.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print()
    print("="*60)
    print(f"✓ Results saved: {output_file}")
    print(f"  Measured {len(all_results)}/{len(all_tools)} tools")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
