#!/usr/bin/env python3
"""
Phase 2B: Measure WASM Tool Execution Time

각 tool을 WASM 서버로 실행하고 T_exec 측정

Requirements:
    - wasmtime 설치
    - WASM 서버들이 빌드되어 있어야 함
    - EdgeAgent/wasm_mcp/ 디렉토리 접근 가능

Usage:
    python3 2b_measure_wasm_tools.py

Output:
    - wasm_tool_exec_time.json
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

# WASM server path (adjust based on environment)
# Check multiple possible locations
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
    WASM_PATH = WASM_PATH_CANDIDATES[0]  # Default to first

# Server name mapping
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

# Test payloads for all 49 tools
TEST_PAYLOADS = {
    # Filesystem (14)
    'read_file': {'path': '/tmp/test.txt'},
    'read_text_file': {'path': '/tmp/test.txt'},
    'read_media_file': {'path': '/tmp/test.jpg'},
    'read_multiple_files': {'paths': ['/tmp/test.txt', '/tmp/test2.txt']},
    'write_file': {'path': '/tmp/test_write.txt', 'content': 'test' * 100},
    'edit_file': {'path': '/tmp/test.txt', 'edits': [{'oldText': 'old', 'newText': 'new'}], 'dryRun': True},
    'create_directory': {'path': '/tmp/test_dir'},
    'list_directory': {'path': '/tmp'},
    'list_directory_with_sizes': {'path': '/tmp'},
    'directory_tree': {'path': '/tmp'},
    'move_file': {'source': '/tmp/test.txt', 'destination': '/tmp/test_moved.txt'},
    'search_files': {'path': '/tmp', 'pattern': '*.txt'},
    'get_file_info': {'path': '/tmp/test.txt'},
    'list_allowed_directories': {},

    # Git (12)
    'git_status': {'repo_path': '/tmp/test_repo'},
    'git_diff_unstaged': {'repo_path': '/tmp/test_repo'},
    'git_diff_staged': {'repo_path': '/tmp/test_repo'},
    'git_diff': {'repo_path': '/tmp/test_repo', 'target': 'HEAD~1'},
    'git_commit': {'repo_path': '/tmp/test_repo', 'message': 'test commit'},
    'git_add': {'repo_path': '/tmp/test_repo', 'files': ['test.txt']},
    'git_reset': {'repo_path': '/tmp/test_repo'},
    'git_log': {'repo_path': '/tmp/test_repo', 'max_count': 10},
    'git_create_branch': {'repo_path': '/tmp/test_repo', 'branch_name': 'test-branch'},
    'git_checkout': {'repo_path': '/tmp/test_repo', 'branch_name': 'main'},
    'git_show': {'repo_path': '/tmp/test_repo', 'revision': 'HEAD'},
    'git_branch': {'repo_path': '/tmp/test_repo'},

    # Fetch (1)
    'fetch': {'url': 'https://example.com'},

    # Sequential Thinking (1)
    'sequentialthinking': {
        'thought': 'test thought',
        'nextThoughtNeeded': False,
        'thoughtNumber': 1,
        'totalThoughts': 1
    },

    # Time (2)
    'get_current_time': {'timezone': 'Asia/Seoul'},
    'convert_time': {'source_timezone': 'Asia/Seoul', 'time': '12:00', 'target_timezone': 'America/New_York'},

    # Summarize (3)
    'summarize_text': {'text': 'test ' * 100, 'max_length': 50},
    'summarize_documents': {'documents': [{'title': 'doc1', 'content': 'test ' * 50}]},
    'get_provider_info': {},

    # Log Parser (5)
    'parse_logs': {'log_content': 'ERROR test\n' * 100, 'format_type': 'auto'},
    'filter_entries': {'entries': [{'level': 'ERROR', 'message': 'test'}], 'min_level': 'WARNING'},
    'compute_log_statistics': {'entries': [{'level': 'ERROR', 'message': 'test'} for _ in range(10)]},
    'search_entries': {'entries': [{'message': 'test error'}], 'pattern': 'error'},
    'extract_time_range': {'entries': [{'timestamp': '2024-01-01T00:00:00Z', 'message': 'test'}]},

    # Data Aggregate (5)
    'aggregate_list': {'items': [{'type': 'A', 'value': i} for i in range(100)]},
    'merge_summaries': {'summaries': [{'key': 'test', 'value': 1}, {'key': 'test', 'value': 2}]},
    'combine_research_results': {'results': [{'source': 'A', 'data': 'test1'}, {'source': 'B', 'data': 'test2'}]},
    'deduplicate': {'items': [{'id': 1, 'name': 'test'}, {'id': 1, 'name': 'test'}], 'key_fields': ['id']},
    'compute_trends': {'data': [{'timestamp': '2024-01-01', 'value': 10}, {'timestamp': '2024-01-02', 'value': 20}]},

    # Image Resize (6)
    'get_image_info': {'image_path': '/tmp/test.jpg'},
    'resize_image': {'image_path': '/tmp/test.jpg', 'max_width': 800, 'max_height': 600},
    'scan_directory': {'directory_path': '/tmp'},
    'compute_image_hash': {'image_path': '/tmp/test.jpg'},
    'compare_hashes': {'hash1': 'abc123', 'hash2': 'abc124'},
    'batch_resize': {'image_paths': ['/tmp/test.jpg'], 'max_width': 800, 'max_height': 600},
}


def get_payload_size(payload):
    """Calculate payload size in bytes"""
    import sys
    return sys.getsizeof(json.dumps(payload))


def measure_tool_wasm(tool_name, server_name, payload, runs=3):
    """
    Measure WASM tool execution time using wasmtime

    Returns:
        dict with t_exec, input_size, output_size, runs
    """
    print(f"  Measuring {tool_name} (WASM)...")

    # Get WASM file
    wasm_file = WASM_PATH / SERVER_WASM_MAP.get(server_name)

    if not wasm_file.exists():
        print(f"    ⚠️  WASM file not found: {wasm_file}")
        print(f"    Build with: cd wasm_mcp && cargo build --target wasm32-wasip2 --release -p mcp-server-{server_name.replace('_', '-')}")
        return None

    # Build JSON-RPC request
    request = {
        'jsonrpc': '2.0',
        'method': f'tools/call',
        'params': {
            'name': tool_name,
            'arguments': payload
        },
        'id': 1
    }

    request_json = json.dumps(request)
    input_size = sys.getsizeof(request_json)

    exec_times = []
    output_size = 0

    for run in range(runs):
        try:
            # Run wasmtime
            cmd = ['wasmtime', 'run', '--dir=/tmp', str(wasm_file)]
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
                print(f"    ⚠️  wasmtime failed: {proc.stderr[:100]}")

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


def check_wasmtime():
    """Check if wasmtime is available"""
    try:
        result = subprocess.run(['wasmtime', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ wasmtime: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("❌ wasmtime not found!")
    print("\nInstall wasmtime:")
    print("  curl https://wasmtime.dev/install.sh -sSf | bash")
    return False


def main():
    print("="*60)
    print("Phase 2B: WASM Tool Execution Time Measurement")
    print("="*60)
    print()

    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print()

    # Check wasmtime
    if not check_wasmtime():
        return

    print()
    print("WASM servers location:")
    print(f"  {WASM_PATH}")
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
            result = measure_tool_wasm(tool_name, server_name, payload)
            if result:
                results.append(result)
        except Exception as e:
            print(f"  ❌ {tool_name}: {e}")

    # Save results
    output_file = f'wasm_tool_exec_time_{hostname}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print()
    print("="*60)
    print(f"✓ Results saved: {output_file}")
    print(f"  Measured {len(results)} tools")
    print("="*60)


if __name__ == "__main__":
    main()
