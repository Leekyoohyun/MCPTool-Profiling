#!/bin/bash
# Storage Performance Benchmark using fio
#
# Measures:
#   - Sequential Read/Write (MB/s)
#   - Random Read/Write IOPS
#
# Usage:
#   ./storage_benchmark.sh [test_dir]
#
# Requirements:
#   - fio (install: brew install fio / apt-get install fio)

set -e

TEST_DIR="${1:-.}"
TEST_FILE="$TEST_DIR/fio_test_file"
FILE_SIZE="1G"

# Check if fio is installed
if ! command -v fio &> /dev/null; then
    echo "Error: fio is not installed"
    echo ""
    echo "Install fio:"
    echo "  macOS:  brew install fio"
    echo "  Ubuntu: sudo apt-get install fio"
    echo "  Fedora: sudo dnf install fio"
    exit 1
fi

echo "=========================================="
echo "Storage Performance Benchmark"
echo "=========================================="
echo "Test directory: $TEST_DIR"
echo "File size: $FILE_SIZE"
echo ""

# Sequential Read
echo "1. Sequential Read..."
SEQ_READ=$(fio --name=seq_read \
    --filename="$TEST_FILE" \
    --size=$FILE_SIZE \
    --rw=read \
    --bs=1M \
    --direct=1 \
    --numjobs=1 \
    --ioengine=libaio \
    --iodepth=32 \
    --runtime=10 \
    --time_based \
    --group_reporting \
    --output-format=json 2>/dev/null | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['jobs'][0]['read']['bw_mean']/1024:.2f}\")")

echo "   Sequential Read: $SEQ_READ MB/s"

# Sequential Write
echo "2. Sequential Write..."
SEQ_WRITE=$(fio --name=seq_write \
    --filename="$TEST_FILE" \
    --size=$FILE_SIZE \
    --rw=write \
    --bs=1M \
    --direct=1 \
    --numjobs=1 \
    --ioengine=libaio \
    --iodepth=32 \
    --runtime=10 \
    --time_based \
    --group_reporting \
    --output-format=json 2>/dev/null | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['jobs'][0]['write']['bw_mean']/1024:.2f}\")")

echo "   Sequential Write: $SEQ_WRITE MB/s"

# Random Read IOPS
echo "3. Random Read IOPS..."
RAND_READ=$(fio --name=rand_read \
    --filename="$TEST_FILE" \
    --size=$FILE_SIZE \
    --rw=randread \
    --bs=4k \
    --direct=1 \
    --numjobs=1 \
    --ioengine=libaio \
    --iodepth=256 \
    --runtime=10 \
    --time_based \
    --group_reporting \
    --output-format=json 2>/dev/null | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['jobs'][0]['read']['iops_mean']:.0f}\")")

echo "   Random Read IOPS: $RAND_READ"

# Random Write IOPS
echo "4. Random Write IOPS..."
RAND_WRITE=$(fio --name=rand_write \
    --filename="$TEST_FILE" \
    --size=$FILE_SIZE \
    --rw=randwrite \
    --bs=4k \
    --direct=1 \
    --numjobs=1 \
    --ioengine=libaio \
    --iodepth=256 \
    --runtime=10 \
    --time_based \
    --group_reporting \
    --output-format=json 2>/dev/null | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['jobs'][0]['write']['iops_mean']:.0f}\")")

echo "   Random Write IOPS: $RAND_WRITE"

# Cleanup
rm -f "$TEST_FILE"

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Sequential Read:  $SEQ_READ MB/s"
echo "Sequential Write: $SEQ_WRITE MB/s"
echo "Random Read IOPS: $RAND_READ"
echo "Random Write IOPS: $RAND_WRITE"
echo ""
echo "Update node.yaml with these values:"
echo "  sequential_read_mbps: $SEQ_READ"
echo "  sequential_write_mbps: $SEQ_WRITE"
echo "  random_read_iops: $RAND_READ"
echo "  random_write_iops: $RAND_WRITE"
