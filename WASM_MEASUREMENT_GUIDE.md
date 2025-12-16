# WASM Tool Measurement Guide

## Fixed Issues

### 1. Image Resize Parameters
**Problem**: `resize_image` failed with "No resize parameters provided (width, height, or max_size)"

**Fix**: Changed from `max_width/max_height` to `max_size`:
```python
# Before:
'resize_image': {'image_path': '/tmp/test_4mp.png', 'max_width': 800, 'max_height': 600}

# After:
'resize_image': {'image_path': '/tmp/test_4mp.png', 'max_size': 800}
```

### 2. Compare Hashes Format
**Problem**: `compare_hashes` expected structured objects, not plain strings

**Fix**: Changed to object format with `hash` and `path` fields:
```python
# Before:
'compare_hashes': {
    'hashes': ['abc123def456', 'abc124def456', '123456789abc']
}

# After:
'compare_hashes': {
    'hashes': [
        {'hash': 'abc123def456', 'path': '/tmp/test_4mp.png'},
        {'hash': 'abc124def456', 'path': '/tmp/test_9mp.png'},
        {'hash': '123456789abc', 'path': '/tmp/test_16mp.png'}
    ]
}
```

### 3. Batch Resize Parameters
**Fix**: Also changed to `max_size` for consistency

## How to Run on Edge Nodes

### Step 1: Copy files to edge node
```bash
# On your laptop:
scp -r EdgeAgent-Profile-for-Schedule-v2/ edge-nuc:~/
```

### Step 2: Setup test data on edge node
```bash
# SSH to edge node:
ssh edge-nuc

cd EdgeAgent-Profile-for-Schedule-v2/

# Run setup script:
./setup_test_data_for_wasm.sh
```

This script will:
- Generate test data (images, logs, JSON, text files)
- Copy all files to `/tmp/` (WASM can only access `/tmp`)
- Initialize `/tmp/git_repo` as a git repository with initial commit
- Create test files for move/write operations

### Step 3: Run WASM tool measurements
```bash
python3 2b_measure_wasm_tools_mcp.py
```

Output: `wasm_tool_exec_time_<hostname>.json`

## Expected Results

### Tools that should work:
- **Filesystem**: read_file, read_text_file, write_file, list_directory, get_file_info, list_allowed_directories
- **Git**: All git tools (if repo is initialized properly)
- **Time**: get_current_time, convert_time
- **Log Parser**: parse_logs, filter_entries, compute_log_statistics, search_entries, extract_time_range
- **Data Aggregate**: All 5 tools
- **Image Resize**: get_image_info, compute_image_hash, compare_hashes, resize_image (if images exist)
- **Sequential Thinking**: sequentialthinking
- **Fetch**: fetch (with --wasi http support)
- **Summarize**: summarize_text, summarize_documents, get_provider_info (with --wasi http support)

### Tools that might fail:
- **read_media_file**: May have encoding issues in WASM
- **read_multiple_files**: May fail if files don't exist
- **edit_file**: May be disabled in WASM for safety
- **create_directory**: May fail due to WASM permissions
- **move_file**: May be disabled in WASM for safety
- **search_files**: May fail with permission denied (WASM restrictions)
- **directory_tree**: May fail with permission denied
- **scan_directory**: May fail with permission denied
- **batch_resize**: May fail if images are too large

## Troubleshooting

### Issue: "os error 44" or "File not found"
- Make sure test data is in `/tmp/` directly (not `/tmp/files/` or `/tmp/images/`)
- Run `ls -lh /tmp/*.png /tmp/*.txt /tmp/*.log` to verify

### Issue: Git tools failing
- Check if git repo is initialized: `cd /tmp/git_repo && git status`
- Re-run setup script: `./setup_test_data_for_wasm.sh`

### Issue: Image tools failing
- Check if images exist: `ls -lh /tmp/*.png`
- Verify image files are accessible: `file /tmp/test_4mp.png`
- Large images (>10MB) might timeout in WASM

### Issue: "Permission denied" errors
- Some filesystem operations are restricted in WASM for security
- This is expected behavior - these tools will be skipped

## Measured Values Needed for Alpha Calculation

For each successful tool measurement, you need:
1. **T_exec**: Execution time (measured by script)
2. **Input_size**: Request payload size (measured by script)
3. **Output_size**: Response size (measured by script)
4. **Bandwidth**: Network bandwidth to target (from 1_benchmark_node.py)
5. **Latency**: Network latency to target (from 1_benchmark_node.py)

Alpha formula:
```
T_comm = (Input_size + Output_size) / Bandwidth + Latency
Alpha = T_exec / (T_exec + T_comm)
```

## Next Steps

1. Run measurements on all edge nodes:
   - edge-nuc
   - edge-orin
   - device-rpi

2. Collect results:
   - `wasm_tool_exec_time_edge-nuc.json`
   - `wasm_tool_exec_time_edge-orin.json`
   - `wasm_tool_exec_time_device-rpi.json`

3. Calculate Alpha values for each tool on each node

4. Use Alpha values in scheduling decisions
