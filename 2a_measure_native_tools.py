#!/usr/bin/env python3
"""
Phase 2A: Measure Native Tool Execution Time

각 tool을 Native Python 서버로 실행하고 T_exec 측정

Requirements:
    - Python MCP 서버들이 설치되어 있어야 함
    - EdgeAgent/servers/ 디렉토리 접근 가능

Usage:
    python3 2a_measure_native_tools.py

Output:
    - native_tool_exec_time.json
"""

import subprocess
import json
import time
import sys
import socket
from pathlib import Path

# Import tool definitions
sys.path.insert(0, str(Path(__file__).parent))
from utils.tool_definitions import get_all_tools

# Server path candidates
EDGEAGENT_PATH_CANDIDATES = [
    Path.home() / "EdgeAgent",  # Nodes
    Path.home() / "DDPS/undergraduated/CCGrid-2026/EdgeAgent/EdgeAgent",  # MacBook
]

EDGEAGENT_PATH = None
for path in EDGEAGENT_PATH_CANDIDATES:
    if path.exists():
        EDGEAGENT_PATH = path
        break

if EDGEAGENT_PATH is None:
    EDGEAGENT_PATH = EDGEAGENT_PATH_CANDIDATES[0]  # Default to first

# Test payloads for each tool
TEST_PAYLOADS = {
    # Filesystem
    'read_file': {'path': '/tmp/test.txt'},
    'read_text_file': {'path': '/tmp/test.txt'},
    'write_file': {'path': '/tmp/test_write.txt', 'content': 'test' * 100},
    'list_directory': {'path': '/tmp'},

    # Git
    'git_status': {'repo_path': '/tmp/test_repo'},
    'git_log': {'repo_path': '/tmp/test_repo', 'max_count': 10},

    # Time
    'get_current_time': {'timezone': 'Asia/Seoul'},
    'convert_time': {'source_timezone': 'Asia/Seoul', 'time': '12:00', 'target_timezone': 'America/New_York'},

    # Data aggregate
    'aggregate_list': {'items': [{'type': 'A', 'value': i} for i in range(100)]},

    # Image resize (requires test image)
    'get_image_info': {'image_path': '/tmp/test.jpg'},

    # Log parser
    'parse_logs': {'log_content': 'ERROR test\n' * 100, 'format_type': 'auto'},

    # Summarize
    'get_provider_info': {},

    # Fetch
    'fetch': {'url': 'https://example.com'},

    # Sequential thinking
    'sequentialthinking': {
        'thought': 'test thought',
        'nextThoughtNeeded': False,
        'thoughtNumber': 1,
        'totalThoughts': 1
    },
}


def get_payload_size(payload):
    """Calculate payload size in bytes"""
    import sys
    return sys.getsizeof(json.dumps(payload))


def measure_tool_native(tool_name, server_name, payload, runs=3):
    """
    Measure native tool execution time by directly calling MCP server

    Returns:
        dict with t_exec, input_size, output_size, runs
    """
    print(f"  Measuring {tool_name} (Native)...")

    # Build JSON-RPC request
    request = {
        'jsonrpc': '2.0',
        'method': 'tools/call',
        'params': {
            'name': tool_name,
            'arguments': payload
        },
        'id': 1
    }

    request_json = json.dumps(request)
    input_size = sys.getsizeof(request_json)

    # Determine command based on server
    cmd = get_server_command(server_name)

    if not cmd:
        print(f"    ⚠️  Server not supported: {server_name}")
        return None

    exec_times = []
    output_size = 0

    for run in range(runs):
        try:
            start = time.time()

            proc = subprocess.run(
                cmd,
                input=request_json,
                capture_output=True,
                text=True,
                timeout=10
            )

            end = time.time()
            exec_times.append(end - start)

            if proc.returncode == 0:
                # Parse response
                try:
                    response = json.loads(proc.stdout)
                    output_size = sys.getsizeof(json.dumps(response))
                except json.JSONDecodeError:
                    output_size = len(proc.stdout)
            else:
                print(f"    ⚠️  Command failed: {proc.stderr[:100]}")

        except subprocess.TimeoutExpired:
            print(f"    ⚠️  Timeout")
            exec_times.append(10.0)
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
            return None

    if not exec_times:
        return None

    avg_exec_time = sum(exec_times) / len(exec_times)

    return {
        'tool_name': tool_name,
        'server': server_name,
        't_exec': avg_exec_time,
        'input_size': input_size,
        'output_size': output_size,
        'runs': runs,
        'measurements': exec_times
    }


def get_server_command(server_name):
    """
    Get command to execute MCP server

    Returns:
        list: Command and arguments
    """
    # npm-based servers
    npm_servers = {
        'filesystem': ['mcp-server-filesystem', '/tmp'],
        'git': ['mcp-server-git'],
        'fetch': ['mcp-server-fetch'],
        'time': ['mcp-server-time'],
        'sequentialthinking': ['mcp-server-sequential-thinking'],
    }

    if server_name in npm_servers:
        return npm_servers[server_name]

    # Python-based servers
    python_servers = {
        'summarize': 'summarize_server.py',
        'log_parser': 'log_parser_server.py',
        'data_aggregate': 'data_aggregate_server.py',
        'image_resize': 'image_resize_server.py',
    }

    if server_name in python_servers:
        server_path = EDGEAGENT_PATH / 'servers' / python_servers[server_name]
        if server_path.exists():
            return ['python3', str(server_path)]
        else:
            print(f"    ⚠️  Python server not found: {server_path}")
            return None

    return None


def main():
    print("="*60)
    print("Phase 2A: Native Tool Execution Time Measurement")
    print("="*60)
    print()

    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print()

    # Check npm servers
    print("Checking MCP servers...")
    npm_check = subprocess.run(['which', 'mcp-server-filesystem'], capture_output=True)
    if npm_check.returncode != 0:
        print("⚠️  npm MCP servers not found!")
        print("   Install: npm install -g @modelcontextprotocol/server-*")
        print()

    # Check Python servers
    python_servers_path = EDGEAGENT_PATH / 'servers'
    if not python_servers_path.exists():
        print(f"⚠️  Python servers not found at: {python_servers_path}")
        print(f"   Make sure EdgeAgent is cloned to: {EDGEAGENT_PATH.parent}")
        print()

    all_tools = get_all_tools()
    results = []

    print(f"Total tools to measure: {len(all_tools)}")
    print()

    for tool in all_tools:
        tool_name = tool['name']
        server_name = tool['server']

        # Get test payload
        if tool_name not in TEST_PAYLOADS:
            print(f"  ⚠️  {tool_name}: No test payload, skipping")
            continue

        payload = TEST_PAYLOADS[tool_name]

        try:
            result = measure_tool_native(tool_name, server_name, payload)
            if result:
                results.append(result)
        except Exception as e:
            print(f"  ❌ {tool_name}: {e}")

    # Save results
    output_file = f'native_tool_exec_time_{hostname}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print()
    print("="*60)
    print(f"✓ Results saved: {output_file}")
    print(f"  Measured {len(results)} tools")
    print("="*60)


if __name__ == "__main__":
    main()
