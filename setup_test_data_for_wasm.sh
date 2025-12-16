#!/bin/bash
# Setup test data in /tmp for WASM tool measurements
# Run this before running 2b_measure_wasm_tools_mcp.py

set -e

echo "=========================================="
echo "Setting up test data in /tmp for WASM"
echo "=========================================="
echo ""

# 1. Generate test data locally first
echo "Step 1: Generating test data..."
python3 generate_test_data.py
echo ""

# 2. Copy test data to /tmp (WASM can only access /tmp)
echo "Step 2: Copying test data to /tmp..."
cp -rv test_data/* /tmp/
echo ""

# 3. Initialize git repository
echo "Step 3: Initializing git repository..."
if [ -d "/tmp/git_repo" ]; then
    cd /tmp/git_repo

    # Initialize if not already a git repo
    if [ ! -d ".git" ]; then
        git init
        echo "Git repo initialized"
    fi

    # Configure git user for this repo
    git config user.name "Test User"
    git config user.email "test@example.com"
    echo "Git user configured"

    # Create README if it doesn't exist
    if [ ! -f "README.md" ]; then
        echo "# Test Repository" > README.md
        echo "" >> README.md
        echo "This is a test git repository for MCP git tools." >> README.md
    fi

    # Create a test file
    echo "test content" > test.txt

    # Make initial commit if no commits exist
    if ! git rev-parse HEAD >/dev/null 2>&1; then
        git add .
        git commit -m "Initial commit"
        echo "Initial commit created"
    fi

    # Show repo status
    echo ""
    echo "Git repository status:"
    git status
    git log --oneline -n 3
else
    echo "⚠️  /tmp/git_repo not found!"
    echo "   Run generate_test_data.py first"
fi
echo ""

# 4. Create test files for move/write operations
echo "Step 4: Creating test files for filesystem operations..."
echo "test source content" > /tmp/test_move_src.txt
echo ""

# 5. List what's in /tmp
echo "=========================================="
echo "Test data ready in /tmp:"
echo "=========================================="
ls -lh /tmp/*.txt /tmp/*.log /tmp/*.json /tmp/*.png 2>/dev/null | head -20
echo ""
echo "Git repo:"
ls -lh /tmp/git_repo/ 2>/dev/null
echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Now you can run: python3 2b_measure_wasm_tools_mcp.py"
echo ""
