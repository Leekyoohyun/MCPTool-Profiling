#!/usr/bin/env python3
"""
Standard Test Payloads for WASM Tool Profiling

All payloads are designed to have approximately 2KB input size
for fair comparison across different nodes and tools.

WASM stdio has 4KB buffer limit, so we use 2KB as standard to be safe.
"""

import json

# Standard sizes
STANDARD_INPUT_SIZE = 2048  # 2KB target
WASM_BUFFER_LIMIT = 4096    # 4KB hard limit

# Standard test text (approximately 500 bytes)
STANDARD_TEXT_500B = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
Nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in.
Reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla.
Excepteur sint occaecat cupidatat non proident, sunt in culpa qui.
Officia deserunt mollit anim id est laborum consectetur adipiscing.
""".strip()

# Standard log entry (approximately 100 bytes each)
STANDARD_LOG_ENTRY = "2024-01-01 12:00:00 ERROR [worker-1] service - Processing request failed with error code 500"


def get_standard_payloads():
    """
    Generate standard test payloads - all approximately 2KB input size

    Returns:
        dict: Tool name -> payload mapping
    """

    # Create standard text (repeat to reach ~2KB)
    text_2kb = (STANDARD_TEXT_500B + "\n") * 4  # ~2KB

    # Create standard log content (~2KB)
    log_entries_2kb = (STANDARD_LOG_ENTRY + "\n") * 20  # ~2KB

    # Create standard list items (each ~40B, 40 items = ~1.6KB)
    list_items_40 = [
        {
            'id': i,
            'type': chr(65 + i % 5),
            'value': i * 10,
            'name': f'item_{i:03d}',
            'status': 'active'
        }
        for i in range(40)
    ]

    return {
        # ============================================================
        # Time (2 tools) - Minimal input, inherently small
        # ============================================================
        'get_current_time': {
            'timezone': 'Asia/Seoul'
        },
        'convert_time': {
            'source_timezone': 'Asia/Seoul',
            'time': '12:00',
            'target_timezone': 'America/New_York'
        },

        # ============================================================
        # Sequential Thinking (1 tool) - ~2KB thought
        # ============================================================
        'sequentialthinking': {
            'thought': text_2kb,
            'nextThoughtNeeded': False,
            'thoughtNumber': 1,
            'totalThoughts': 1
        },

        # ============================================================
        # Fetch (1 tool) - Minimal input
        # ============================================================
        'fetch': {
            'url': 'https://example.com'
        },

        # ============================================================
        # Summarize (3 tools) - All ~2KB input
        # ============================================================
        'summarize_text': {
            'text': text_2kb,
            'max_length': 100
        },
        'summarize_documents': {
            'documents': [
                {'title': 'doc1', 'content': STANDARD_TEXT_500B},
                {'title': 'doc2', 'content': STANDARD_TEXT_500B},
                {'title': 'doc3', 'content': STANDARD_TEXT_500B},
                {'title': 'doc4', 'content': STANDARD_TEXT_500B}
            ]  # 4 * 500B = ~2KB
        },
        'get_provider_info': {},

        # ============================================================
        # Log Parser (5 tools) - All ~2KB input
        # ============================================================
        'parse_logs': {
            'log_content': log_entries_2kb,
            'format_type': 'auto'
        },
        'filter_entries': {
            'entries': [
                {
                    'level': 'ERROR' if i % 3 == 0 else 'WARNING' if i % 3 == 1 else 'INFO',
                    'message': f'Log message {i}: ' + 'x' * 30
                }
                for i in range(30)  # 30 entries * ~70B = ~2KB
            ],
            'min_level': 'WARNING'
        },
        'compute_log_statistics': {
            'entries': [
                {
                    'level': 'ERROR' if i % 4 == 0 else 'WARNING',
                    'message': f'test message {i:03d}',
                    'timestamp': f'2024-01-01T{i%24:02d}:00:00Z'
                }
                for i in range(30)  # 30 entries * ~50B = ~1.5KB
            ]
        },
        'search_entries': {
            'entries': [
                {
                    'message': f'test error occurred in module {i}',
                    'timestamp': f'2024-01-01T12:{i:02d}:00Z'
                }
                for i in range(40)  # 40 entries * ~40B = ~1.6KB
            ],
            'pattern': 'error'
        },
        'extract_time_range': {
            'entries': [
                {
                    'timestamp': f'2024-01-{(i//10)+1:02d}T{(i%24):02d}:00:00Z',
                    'message': f'message {i:03d}'
                }
                for i in range(35)  # 35 entries * ~40B = ~1.4KB
            ]
        },

        # ============================================================
        # Data Aggregate (5 tools) - All ~2KB input
        # ============================================================
        'aggregate_list': {
            'items': list_items_40  # 40 items * ~40B = ~1.6KB
        },
        'merge_summaries': {
            'summaries': [
                {
                    'category': chr(65 + i % 10),
                    'count': i * 10,
                    'total': i * 100,
                    'average': i * 10.5
                }
                for i in range(30)  # 30 items * ~50B = ~1.5KB
            ]
        },
        'combine_research_results': {
            'results': [
                {
                    'source': f'Database_{chr(65 + i)}',
                    'data': STANDARD_TEXT_500B[:200],  # 200B each
                    'confidence': 0.95,
                    'timestamp': '2024-01-01T12:00:00Z'
                }
                for i in range(8)  # 8 results * ~250B = ~2KB
            ]
        },
        'deduplicate': {
            'items': [
                {
                    'id': i % 25,  # Creates duplicates
                    'name': f'item_{i % 25}',
                    'value': i * 10,
                    'metadata': 'x' * 20
                }
                for i in range(40)  # 40 items * ~40B = ~1.6KB
            ],
            'key_fields': ['id']
        },
        'compute_trends': {
            'time_series': [
                {
                    'timestamp': f'2024-01-{(i//2)+1:02d}T{(i%24):02d}:00:00Z',
                    'value': 100 + i * 2.5,
                    'label': f'data_point_{i:03d}'
                }
                for i in range(30)  # 30 points * ~50B = ~1.5KB
            ]
        },

        # ============================================================
        # Image Resize (5 tools) - File paths (inherently small)
        # Note: Image content size is determined by file, not payload
        # ============================================================
        'get_image_info': {
            'image_path': '/tmp/test_4mp.png'
        },
        'resize_image': {
            'image_path': '/tmp/test_4mp.png',
            'max_size': 800
        },
        'compute_image_hash': {
            'image_path': '/tmp/test_4mp.png'
        },
        'compare_hashes': {
            'hashes': [
                {
                    'hash': f'hash_{i:04d}_' + 'a' * 50,
                    'path': f'/tmp/image_{i}.png'
                }
                for i in range(20)  # 20 hashes * ~100B = ~2KB
            ]
        },
        'batch_resize': {
            'image_paths': ['/tmp/test_4mp.png', '/tmp/test_9mp.png'],
            'max_size': 800
        },

        # ============================================================
        # Filesystem (14 tools) - File paths (inherently small)
        # Note: File content size is determined by file, not payload
        # ============================================================
        'read_file': {
            'path': '/tmp/test_2kb.txt'
        },
        'read_text_file': {
            'path': '/tmp/test_2kb.txt'
        },
        'read_media_file': {
            'path': '/tmp/test_4mp.png'
        },
        'read_multiple_files': {
            'paths': ['/tmp/test_2kb.txt', '/tmp/test_1kb.json']
        },
        'write_file': {
            'path': '/tmp/test_write.txt',
            'content': text_2kb  # ~2KB content
        },
        'edit_file': {
            'path': '/tmp/test_2kb.txt',
            'edits': [{'oldText': 'Lorem', 'newText': 'LOREM'}],
            'dryRun': True
        },
        'create_directory': {
            'path': '/tmp/test_dir_new'
        },
        'list_directory': {
            'path': '/tmp'
        },
        'list_directory_with_sizes': {
            'path': '/tmp'
        },
        'directory_tree': {
            'path': '/tmp'
        },
        'move_file': {
            'source': '/tmp/test_move_src.txt',
            'destination': '/tmp/test_move_dst.txt'
        },
        'search_files': {
            'path': '/tmp',
            'pattern': '*.txt'
        },
        'get_file_info': {
            'path': '/tmp/test_2kb.txt'
        },
        'list_allowed_directories': {},

        # ============================================================
        # Git (12 tools) - Repository paths (inherently small)
        # ============================================================
        'git_status': {
            'repo_path': '/tmp/git_repo'
        },
        'git_diff_unstaged': {
            'repo_path': '/tmp/git_repo'
        },
        'git_diff_staged': {
            'repo_path': '/tmp/git_repo'
        },
        'git_diff': {
            'repo_path': '/tmp/git_repo',
            'target': 'HEAD~1'
        },
        'git_commit': {
            'repo_path': '/tmp/git_repo',
            'message': 'test commit'
        },
        'git_add': {
            'repo_path': '/tmp/git_repo',
            'files': ['README.md']
        },
        'git_reset': {
            'repo_path': '/tmp/git_repo'
        },
        'git_log': {
            'repo_path': '/tmp/git_repo',
            'max_count': 10
        },
        'git_create_branch': {
            'repo_path': '/tmp/git_repo',
            'branch_name': 'test-branch'
        },
        'git_checkout': {
            'repo_path': '/tmp/git_repo',
            'branch_name': 'main'
        },
        'git_show': {
            'repo_path': '/tmp/git_repo',
            'revision': 'HEAD'
        },
        'git_branch': {
            'repo_path': '/tmp/git_repo',
            'branch_type': 'all'
        },
    }


def validate_payload_sizes():
    """Validate that all payloads are within WASM buffer limit"""
    payloads = get_standard_payloads()

    print("Payload Size Validation")
    print("=" * 60)
    print(f"Target size: {STANDARD_INPUT_SIZE} bytes (2KB)")
    print(f"Hard limit: {WASM_BUFFER_LIMIT} bytes (4KB)")
    print()

    oversized = []

    for tool_name, payload in sorted(payloads.items()):
        size = len(json.dumps(payload))
        status = "✓" if size <= WASM_BUFFER_LIMIT else "❌"

        if size > WASM_BUFFER_LIMIT:
            oversized.append((tool_name, size))

        # Show size relative to target
        if size > STANDARD_INPUT_SIZE * 1.2:  # More than 20% over target
            size_str = f"{size:5d}B (⚠️  {size/STANDARD_INPUT_SIZE:.1f}x target)"
        else:
            size_str = f"{size:5d}B"

        print(f"{status} {tool_name:30s} {size_str}")

    print()
    print("=" * 60)
    if oversized:
        print(f"❌ {len(oversized)} payloads exceed 4KB limit:")
        for name, size in oversized:
            print(f"   {name}: {size} bytes")
    else:
        print("✓ All payloads within 4KB limit!")

    return len(oversized) == 0


if __name__ == "__main__":
    validate_payload_sizes()
