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

# Test data path - use local test_data directory
TEST_DATA_PATH = Path(__file__).parent / "test_data"

# Fallback to other locations if local doesn't exist
if not TEST_DATA_PATH.exists():
    TEST_DATA_CANDIDATES = [
        Path.home() / "EdgeAgent-Profile-for-Schedule-v2/test_data",  # Home directory
        Path.home() / "EdgeAgent-Profiling-for-coremark-v1/test_data",  # Old location
        Path.home() / "DDPS/undergraduated/CCGrid-2026/EdgeAgent/EdgeAgent-Profiling-for-coremark-v1/test_data",  # MacBook
    ]

    for path in TEST_DATA_CANDIDATES:
        if path.exists():
            TEST_DATA_PATH = path
            break

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

def get_test_payloads():
    """Generate test payloads using real test data"""

    # Use /tmp paths (WASM only has access to --dir=/tmp)
    # Make sure to copy test data to /tmp first:
    # cp -r ~/EdgeAgent-Profiling-for-coremark-v1/test_data/* /tmp/
    test_text = '/tmp/files/test_medium.txt'
    test_json = '/tmp/files/test_medium.json'
    test_log = '/tmp/files/test_medium.log'
    test_image = '/tmp/images/size_test/test_4mp.png'
    test_large_image = '/tmp/images/size_test/test_9mp.png'
    test_git_repo = '/tmp/git_repo'
    test_files_dir = '/tmp/files'
    test_images_dir = '/tmp/images/size_test'

    # Read actual log content for log parser tests
    try:
        with open(test_log, 'r') as f:
            log_content = f.read()
    except:
        log_content = 'ERROR test\n' * 100

    return {
        # Filesystem (14)
        'read_file': {'path': test_text},
        'read_text_file': {'path': test_text},
        'read_media_file': {'path': test_image},
        'read_multiple_files': {'paths': [test_text, test_json]},
        'write_file': {'path': '/tmp/test_write.txt', 'content': 'test' * 1000},
        'edit_file': {'path': test_text, 'edits': [{'oldText': 'the', 'newText': 'THE'}], 'dryRun': True},
        'create_directory': {'path': '/tmp/test_dir_new'},
        'list_directory': {'path': test_files_dir},
        'list_directory_with_sizes': {'path': test_files_dir},
        'directory_tree': {'path': test_files_dir},
        'move_file': {'source': '/tmp/test_move_src.txt', 'destination': '/tmp/test_move_dst.txt'},
        'search_files': {'path': test_files_dir, 'pattern': '*.txt'},
        'get_file_info': {'path': test_text},
        'list_allowed_directories': {},

        # Git (12)
        'git_status': {'repo_path': test_git_repo},
        'git_diff_unstaged': {'repo_path': test_git_repo},
        'git_diff_staged': {'repo_path': test_git_repo},
        'git_diff': {'repo_path': test_git_repo, 'target': 'HEAD~1'},
        'git_commit': {'repo_path': test_git_repo, 'message': 'test commit'},
        'git_add': {'repo_path': test_git_repo, 'files': ['test.txt']},
        'git_reset': {'repo_path': test_git_repo},
        'git_log': {'repo_path': test_git_repo, 'max_count': 10},
        'git_create_branch': {'repo_path': test_git_repo, 'branch_name': 'test-branch'},
        'git_checkout': {'repo_path': test_git_repo, 'branch_name': 'main'},
        'git_show': {'repo_path': test_git_repo, 'revision': 'HEAD'},
        'git_branch': {'repo_path': test_git_repo, 'branch_type': 'all'},

        # Fetch (1)
        'fetch': {'url': 'https://example.com'},

        # Sequential Thinking (1)
        'sequentialthinking': {
            'thought': 'Analyzing the problem of edge computing resource allocation',
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
        'get_image_info': {'image_path': test_image},
        'resize_image': {'image_path': test_image, 'max_width': 800, 'max_height': 600},
        'scan_directory': {'directory': test_images_dir},
        'compute_image_hash': {'image_path': test_image},
        'compare_hashes': {
            'hashes': [
                'abc123def456',
                'abc124def456',
                '123456789abc'
            ]
        },
        'batch_resize': {
            'image_paths': [test_image, test_large_image],
            'max_width': 800,
            'max_height': 600
        },
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

            if proc.returncode == 0:
                # Parse response
                try:
                    response = json.loads(proc.stdout)
                    output_size = sys.getsizeof(json.dumps(response))
                    exec_times.append(end - start)
                except json.JSONDecodeError:
                    output_size = len(proc.stdout)
                    exec_times.append(end - start)
            else:
                print(f"    ⚠️  wasmtime failed (returncode={proc.returncode})")
                print(f"    STDERR: {proc.stderr}")
                print(f"    STDOUT: {proc.stdout[:200]}")
                # 실패한 경우 측정하지 않음

        except subprocess.TimeoutExpired:
            print(f"    ⚠️  Timeout")
            # Timeout은 측정 불가
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
    print("Test data location:")
    print(f"  {TEST_DATA_PATH}")
    if not TEST_DATA_PATH.exists():
        print(f"  ⚠️  Test data path does not exist!")
        print(f"  Please copy test_data to the correct location")
    print()

    # Generate test payloads with real data
    TEST_PAYLOADS = get_test_payloads()

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
