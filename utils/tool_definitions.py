"""
49개 MCP Tool 정의 (all_tool_schemas.json 기반)

실제 MCP 서버의 tool 스키마를 바탕으로 정의
"""

# Tool 서버별 분류
TOOLS = {
    # Filesystem Server (14개)
    "filesystem": [
        {
            "name": "read_file",
            "description": "Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.",
        },
        {
            "name": "read_text_file",
            "description": "Read the complete contents of a file from the file system as text.",
        },
        {
            "name": "read_media_file",
            "description": "Read an image or audio file. Returns the base64 encoded data and MIME type.",
        },
        {
            "name": "read_multiple_files",
            "description": "Read the contents of multiple files simultaneously.",
        },
        {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file with new content.",
        },
        {
            "name": "edit_file",
            "description": "Make line-based edits to a text file.",
        },
        {
            "name": "create_directory",
            "description": "Create a new directory or ensure a directory exists.",
        },
        {
            "name": "list_directory",
            "description": "Get a detailed listing of all files and directories in a specified path.",
        },
        {
            "name": "list_directory_with_sizes",
            "description": "Get a detailed listing of all files and directories with sizes.",
        },
        {
            "name": "directory_tree",
            "description": "Get a recursive tree view of files and directories as a JSON structure.",
        },
        {
            "name": "move_file",
            "description": "Move or rename files and directories.",
        },
        {
            "name": "search_files",
            "description": "Recursively search for files and directories matching a pattern.",
        },
        {
            "name": "get_file_info",
            "description": "Retrieve detailed metadata about a file or directory.",
        },
        {
            "name": "list_allowed_directories",
            "description": "Returns the list of directories that this server is allowed to access.",
        },
    ],

    # Git Server (12개)
    "git": [
        {
            "name": "git_status",
            "description": "Shows the working tree status",
        },
        {
            "name": "git_diff_unstaged",
            "description": "Shows changes in the working directory that are not yet staged",
        },
        {
            "name": "git_diff_staged",
            "description": "Shows changes that are staged for commit",
        },
        {
            "name": "git_diff",
            "description": "Shows differences between branches or commits",
        },
        {
            "name": "git_commit",
            "description": "Records changes to the repository",
        },
        {
            "name": "git_add",
            "description": "Adds file contents to the staging area",
        },
        {
            "name": "git_reset",
            "description": "Unstages all staged changes",
        },
        {
            "name": "git_log",
            "description": "Shows the commit logs",
        },
        {
            "name": "git_create_branch",
            "description": "Creates a new branch from an optional base branch",
        },
        {
            "name": "git_checkout",
            "description": "Switches branches",
        },
        {
            "name": "git_show",
            "description": "Shows the contents of a commit",
        },
        {
            "name": "git_branch",
            "description": "List Git branches",
        },
    ],

    # Fetch Server (1개)
    "fetch": [
        {
            "name": "fetch",
            "description": "Fetches a URL from the internet and optionally extracts its contents as markdown.",
        },
    ],

    # Sequential Thinking Server (1개)
    "sequentialthinking": [
        {
            "name": "sequentialthinking",
            "description": "A detailed tool for dynamic and reflective problem-solving through thoughts.",
        },
    ],

    # Time Server (2개)
    "time": [
        {
            "name": "get_current_time",
            "description": "Get current time in a specific timezones",
        },
        {
            "name": "convert_time",
            "description": "Convert time between timezones",
        },
    ],

    # Summarize Server (3개)
    "summarize": [
        {
            "name": "summarize_text",
            "description": "Summarize the given text.",
        },
        {
            "name": "summarize_documents",
            "description": "Summarize multiple documents.",
        },
        {
            "name": "get_provider_info",
            "description": "Get information about the current summarization provider.",
        },
    ],

    # Log Parser Server (5개)
    "log_parser": [
        {
            "name": "parse_logs",
            "description": "Parse raw log content into structured entries.",
        },
        {
            "name": "filter_entries",
            "description": "Filter log entries by severity level.",
        },
        {
            "name": "compute_log_statistics",
            "description": "Compute statistics from parsed log entries.",
        },
        {
            "name": "search_entries",
            "description": "Search log entries by regex pattern.",
        },
        {
            "name": "extract_time_range",
            "description": "Extract time range information from log entries.",
        },
    ],

    # Data Aggregate Server (5개)
    "data_aggregate": [
        {
            "name": "aggregate_list",
            "description": "Aggregate a list of dictionaries by grouping, counting, or summing.",
        },
        {
            "name": "merge_summaries",
            "description": "Merge multiple summary dictionaries into one.",
        },
        {
            "name": "combine_research_results",
            "description": "Combine multiple research/search results into a coherent summary.",
        },
        {
            "name": "deduplicate",
            "description": "Remove duplicate items based on key fields.",
        },
        {
            "name": "compute_trends",
            "description": "Compute trends from time-series data.",
        },
    ],

    # Image Resize Server (6개)
    "image_resize": [
        {
            "name": "get_image_info",
            "description": "Get detailed information about an image.",
        },
        {
            "name": "resize_image",
            "description": "Resize an image and return as base64.",
        },
        {
            "name": "scan_directory",
            "description": "Scan a directory for image files.",
        },
        {
            "name": "compute_image_hash",
            "description": "Compute perceptual hash of an image for duplicate detection.",
        },
        {
            "name": "compare_hashes",
            "description": "Compare image hashes to find duplicates/similar images.",
        },
        {
            "name": "batch_resize",
            "description": "Resize multiple images at once (e.g., create thumbnails).",
        },
    ],
}


def get_all_tools():
    """모든 tool을 flat list로 반환"""
    all_tools = []
    for server_name, tools in TOOLS.items():
        for tool in tools:
            tool['server'] = server_name
            all_tools.append(tool)
    return all_tools


def get_tool_count():
    """전체 tool 개수"""
    return sum(len(tools) for tools in TOOLS.values())


def get_tools_by_server(server_name):
    """특정 서버의 tool 목록"""
    return TOOLS.get(server_name, [])


if __name__ == "__main__":
    # 테스트
    all_tools = get_all_tools()
    print(f"Total tools: {len(all_tools)}")

    print("\nTools by server:")
    for server, tools in TOOLS.items():
        print(f"  {server:20s}: {len(tools):2d} tools")
