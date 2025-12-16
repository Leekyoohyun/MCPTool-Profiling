#!/usr/bin/env python3
"""
Standard Test Payloads for WASM Tool Profiling

All payloads are designed to have IDENTICAL input size (1MB)
for fair comparison across different nodes and tools.

This ensures Alpha value calculation is meaningful.
"""

import json

# Standard sizes - ALL INPUTS MUST BE 1MB
STANDARD_INPUT_SIZE = 1024 * 1024  # 1MB for all tools

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
    Generate standard test payloads - ALL 1MB input size

    Returns:
        dict: Tool name -> payload mapping
    """

    # Create 1MB standard text
    text_1mb = (STANDARD_TEXT_500B + "\n") * 2100  # ~1MB

    # Create 1MB standard log content
    log_entries_1mb = (STANDARD_LOG_ENTRY + "\n") * 10000  # ~1MB

    # Create standard list items for 1MB JSON payload
    # Each item ~85B due to JSON overhead
    # 12000 items = ~1MB
    list_items_12k = [
        {
            'id': i,
            'type': chr(65 + i % 5),
            'value': i * 10,
            'category': chr(65 + i % 5),  # Same as type for grouping
            'timestamp': f'2024-01-{(i%30)+1:02d}'  # For trends
        }
        for i in range(12000)
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
        # Sequential Thinking (1 tool) - 10KB thought
        # ============================================================
        'sequentialthinking': {
            'thought': text_3p5kb,
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
        # Summarize (3 tools) - All 10KB input
        # ============================================================
        'summarize_text': {
            'text': text_3p5kb,
            'max_length': 100
        },
        'summarize_documents': {
            'documents': [
                {'title': f'doc{i}', 'content': STANDARD_TEXT_500B}
                for i in range(20)
            ]  # 20 * 500B = ~10KB
        },
        'get_provider_info': {},

        # ============================================================
        # Log Parser (5 tools) - All 10KB input
        # ============================================================
        'parse_logs': {
            'log_content': log_entries_3p5kb,
            'format_type': 'auto'
        },
        'filter_entries': {
            'entries': [
                {
                    '_level': 'info' if i % 3 == 0 else 'error',
                    'message': f'msg {i}'
                }
                for i in range(240)  # ~10KB
            ],
            'min_level': 'warning'
        },
        'compute_log_statistics': {
            'entries': [
                {
                    '_level': 'info' if i % 3 == 0 else 'error',
                    'message': f'msg {i}'
                }
                for i in range(240)  # ~10KB
            ]
        },
        'search_entries': {
            'entries': [
                {
                    '_level': 'info' if i % 3 == 0 else 'error',
                    'message': f'msg {i}'
                }
                for i in range(240)  # ~10KB
            ],
            'pattern': 'error'
        },
        'extract_time_range': {
            'entries': [
                {
                    'timestamp': f'2024-01-{(i//10)+1:02d}T{(i%24):02d}:00:00Z',
                    '_level': 'info' if i % 3 == 0 else 'error',
                    'message': f'msg {i}'
                }
                for i in range(130)  # 130 entries * ~75B = ~9.75KB (timestamp adds size)
            ]
        },

        # ============================================================
        # Data Aggregate (5 tools) - All 10KB input
        # ============================================================
        'aggregate_list': {
            'items': list_items_42,  # 120 items = ~10KB
            'group_by': 'category'
        },
        'merge_summaries': {
            'summaries': [
                {
                    'count': i * 100,
                    'sum': i * 1000
                }
                for i in range(320)  # 320 items * ~32B = ~10KB
            ]
        },
        'combine_research_results': {
            'results': [
                {
                    'source': f'Database_{chr(65 + i % 26)}',
                    'data': STANDARD_TEXT_500B[:180],  # 180B each
                    'confidence': 0.95,
                    'timestamp': '2024-01-01T12:00:00Z'
                }
                for i in range(35)  # 35 results * ~270B = ~9.5KB
            ]
        },
        'deduplicate': {
            'items': [
                {
                    'id': i % 75,  # Creates duplicates
                    'name': f'item_{i % 75}',
                    'value': i * 10,
                    'metadata': 'x' * 10
                }
                for i in range(145)  # 145 items = ~10KB
            ],
            'key_fields': ['name']
        },
        'compute_trends': {
            'time_series': list_items_42,  # 120 items = ~10KB
            'bucket_count': 10
        },

        # ============================================================
        # Image Resize (5 tools) - All use 10KB image file
        # Note: Payload is small, but processed file is 10KB
        # ============================================================
        'get_image_info': {
            'image_path': '/tmp/test_50mb.png'
        },
        'resize_image': {
            'image_path': '/tmp/test_50mb.png',
            'max_size': 800
        },
        'compute_image_hash': {
            'image_path': '/tmp/test_50mb.png'
        },
        'compare_hashes': {
            'hashes': [
                {
                    'hash': f'hash_{i:04d}_' + 'a' * 50,
                    'path': f'/tmp/image_{i}.png'
                }
                for i in range(100)  # 100 hashes * ~100B = ~10KB
            ]
        },
        'batch_resize': {
            'image_paths': ['/tmp/test_50mb.png'] * 5,  # 5 images
            'max_size': 800
        },

        # ============================================================
        # Filesystem (14 tools) - All use 10KB files
        # Note: Payload is small, but processed file is 10KB
        # ============================================================
        'read_file': {
            'path': '/tmp/test_50mb.txt'
        },
        'read_text_file': {
            'path': '/tmp/test_50mb.txt'
        },
        'read_media_file': {
            'path': '/tmp/test_50mb.png'
        },
        'read_multiple_files': {
            'paths': ['/tmp/test_50mb.txt', '/tmp/test_50mb.json']
        },
        'write_file': {
            'path': '/tmp/test_write.txt',
            'content': text_3p5kb  # 10KB content
        },
        'edit_file': {
            'path': '/tmp/test_50mb.txt',
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
    """Validate payload sizes - ALL should be ~10KB for fair comparison"""
    payloads = get_standard_payloads()

    print("Payload Size Validation")
    print("=" * 60)
    print(f"Target size: {STANDARD_INPUT_SIZE} bytes (10KB) for ALL tools")
    print("This ensures fair Alpha value calculation across nodes")
    print()

    for tool_name, payload in sorted(payloads.items()):
        size = len(json.dumps(payload))

        # Show size relative to target
        percent = (size / STANDARD_INPUT_SIZE) * 100
        if size > STANDARD_INPUT_SIZE * 1.5:  # More than 50% over
            size_str = f"{size:6d}B ({percent:5.1f}% of target) ⚠️  TOO LARGE"
        elif size < STANDARD_INPUT_SIZE * 0.5:  # Less than 50%
            size_str = f"{size:6d}B ({percent:5.1f}% of target) ⚠️  TOO SMALL"
        else:
            size_str = f"{size:6d}B ({percent:5.1f}% of target)"

        print(f"  {tool_name:30s} {size_str}")

    print()
    print("=" * 60)
    print("Note: File-based tools (filesystem, git, image) have small")
    print("      payloads but process 10KB files. This is expected.")
    print("=" * 60)


if __name__ == "__main__":
    validate_payload_sizes()
