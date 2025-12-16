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

# Import EdgeAgent's MCP comparator framework
sys.path.insert(0, str(Path.home() / "EdgeAgent/wasm_mcp/tests"))
from mcp_comparator import MCPServerConfig, TransportType

# Import MCP client
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# Import tool definitions
sys.path.insert(0, str(Path(__file__).parent))
from utils.tool_definitions import get_all_tools

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


def get_test_payloads():
    """Generate test payloads using /tmp paths"""

    # Read log content
    try:
        with open('/tmp/test_medium.log', 'r') as f:
            log_content = f.read()
    except:
        log_content = 'ERROR test\n' * 100

    return {
        # Filesystem (14)
        'read_file': {'path': '/tmp/test_medium.txt'},
        'read_text_file': {'path': '/tmp/test_medium.txt'},
        'read_media_file': {'path': '/tmp/images/test_4mp.png'},
        'read_multiple_files': {'paths': ['/tmp/test_medium.txt', '/tmp/test_1k.json']},
        'write_file': {'path': '/tmp/test_write.txt', 'content': 'test' * 1000},
        'edit_file': {'path': '/tmp/test_medium.txt', 'edits': [{'oldText': 'Lorem', 'newText': 'LOREM'}], 'dryRun': True},
        'create_directory': {'path': '/tmp/test_dir_new'},
        'list_directory': {'path': '/tmp'},
        'list_directory_with_sizes': {'path': '/tmp'},
        'directory_tree': {'path': '/tmp'},
        'move_file': {'source': '/tmp/test_move_src.txt', 'destination': '/tmp/test_move_dst.txt'},
        'search_files': {'path': '/tmp', 'pattern': '*.txt'},
        'get_file_info': {'path': '/tmp/test_medium.txt'},
        'list_allowed_directories': {},

        # Git (12)
        'git_status': {'repo_path': '/tmp/git_repo'},
        'git_diff_unstaged': {'repo_path': '/tmp/git_repo'},
        'git_diff_staged': {'repo_path': '/tmp/git_repo'},
        'git_diff': {'repo_path': '/tmp/git_repo', 'target': 'HEAD~1'},
        'git_commit': {'repo_path': '/tmp/git_repo', 'message': 'test commit'},
        'git_add': {'repo_path': '/tmp/git_repo', 'files': ['README.md']},
        'git_reset': {'repo_path': '/tmp/git_repo'},
        'git_log': {'repo_path': '/tmp/git_repo', 'max_count': 10},
        'git_create_branch': {'repo_path': '/tmp/git_repo', 'branch_name': 'test-branch'},
        'git_checkout': {'repo_path': '/tmp/git_repo', 'branch_name': 'main'},
        'git_show': {'repo_path': '/tmp/git_repo', 'revision': 'HEAD'},
        'git_branch': {'repo_path': '/tmp/git_repo', 'branch_type': 'all'},

        # Fetch (1)
        'fetch': {'url': 'https://example.com'},

        # Sequential Thinking (1)
        'sequentialthinking': {
            'thought': 'Analyzing edge computing resource allocation',
            'nextThoughtNeeded': False,
            'thoughtNumber': 1,
            'totalThoughts': 1
        },

        # Time (2)
        'get_current_time': {'timezone': 'Asia/Seoul'},
        'convert_time': {'source_timezone': 'Asia/Seoul', 'time': '12:00', 'target_timezone': 'America/New_York'},

        # Summarize (3)
        'summarize_text': {'text': 'Lorem ipsum ' * 500, 'max_length': 100},
        'summarize_documents': {'documents': [
            {'title': 'doc1', 'content': 'Lorem ipsum ' * 200},
            {'title': 'doc2', 'content': 'Dolor sit amet ' * 200}
        ]},
        'get_provider_info': {},

        # Log Parser (5)
        'parse_logs': {'log_content': log_content, 'format_type': 'auto'},
        'filter_entries': {
            'entries': [
                {'level': 'ERROR', 'message': 'Error occurred'},
                {'level': 'WARNING', 'message': 'Warning message'},
                {'level': 'INFO', 'message': 'Info message'}
            ],
            'min_level': 'WARNING'
        },
        'compute_log_statistics': {
            'entries': [{'level': 'ERROR', 'message': f'test {i}'} for i in range(100)]
        },
        'search_entries': {
            'entries': [
                {'message': 'test error occurred'},
                {'message': 'test warning'},
                {'message': 'normal message'}
            ],
            'pattern': 'error'
        },
        'extract_time_range': {
            'entries': [
                {'timestamp': '2024-01-01T00:00:00Z', 'message': 'test1'},
                {'timestamp': '2024-01-01T12:00:00Z', 'message': 'test2'},
                {'timestamp': '2024-01-02T00:00:00Z', 'message': 'test3'}
            ]
        },

        # Data Aggregate (5)
        'aggregate_list': {'items': [{'type': chr(65 + i % 5), 'value': i} for i in range(1000)]},
        'merge_summaries': {
            'summaries': [
                {'category': 'A', 'count': 10, 'total': 100},
                {'category': 'B', 'count': 20, 'total': 200},
                {'category': 'A', 'count': 5, 'total': 50}
            ]
        },
        'combine_research_results': {
            'results': [
                {'source': 'Database A', 'data': 'Result set 1 with ' + 'data ' * 50},
                {'source': 'Database B', 'data': 'Result set 2 with ' + 'data ' * 50},
                {'source': 'API C', 'data': 'Result set 3 with ' + 'data ' * 50}
            ]
        },
        'deduplicate': {
            'items': [
                {'id': 1, 'name': 'item1'},
                {'id': 2, 'name': 'item2'},
                {'id': 1, 'name': 'item1'},
                {'id': 3, 'name': 'item3'},
                {'id': 2, 'name': 'item2'}
            ],
            'key_fields': ['id']
        },
        'compute_trends': {
            'time_series': [
                {'timestamp': f'2024-01-{i:02d}', 'value': 10 + i * 2}
                for i in range(1, 31)
            ]
        },

        # Image Resize (6)
        'get_image_info': {'image_path': '/tmp/test_4mp.png'},
        'resize_image': {'image_path': '/tmp/test_4mp.png', 'max_size': 800},
        'scan_directory': {'directory': '/tmp'},
        'compute_image_hash': {'image_path': '/tmp/test_4mp.png'},
        'compare_hashes': {
            'hashes': [
                {'hash': 'abc123def456', 'path': '/tmp/test_4mp.png'},
                {'hash': 'abc124def456', 'path': '/tmp/test_9mp.png'},
                {'hash': '123456789abc', 'path': '/tmp/test_16mp.png'}
            ]
        },
        'batch_resize': {
            'image_paths': ['/tmp/test_4mp.png', '/tmp/test_9mp.png'],
            'max_size': 800
        },
    }


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
            # Modify args to add --wasi http flag
            server_config.config['args'] = ["run", "--wasi", "http", "--dir=/tmp", str(wasm_file)]

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
                    print(f"    ✓ {avg_exec_time:.3f}s (avg of {len(exec_times)} runs)")
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
    TEST_PAYLOADS = get_test_payloads()

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
