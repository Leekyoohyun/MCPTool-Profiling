#!/usr/bin/env python3
"""
Generate test data for MCP tool profiling

File-based tools use 50MB files for meaningful execution time
"""

import os
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

try:
    import numpy as np
    from PIL import Image
    HAS_IMAGE_LIBS = True
except ImportError:
    HAS_IMAGE_LIBS = False
    print("⚠️  PIL/numpy not installed. Skipping image generation.")
    print("   Install: pip install Pillow numpy")


def generate_images(output_dir):
    """Generate 50MB test image"""
    if not HAS_IMAGE_LIBS:
        print("Skipping image generation (PIL/numpy required)")
        return

    print("Generating 50MB test image...")
    os.makedirs(output_dir, exist_ok=True)

    # Generate a large image ~50MB
    # 4000x4000 pixels RGB = ~48MB uncompressed
    filename = "test_50mb.png"
    output_path = output_dir / filename

    if output_path.exists():
        print(f"  ✓ {filename} already exists")
        return

    print(f"  Generating {filename} (4000x4000 pixels for ~50MB file)...")
    np.random.seed(42)
    data = np.random.randint(0, 255, (4000, 4000, 3), dtype=np.uint8)
    img = Image.fromarray(data)
    img.save(output_path, "PNG", compress_level=0)  # No compression
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    → {size_mb:.1f} MB")


def generate_logs(output_dir):
    """Generate 50MB log file"""
    print("Generating 50MB log file...")
    os.makedirs(output_dir, exist_ok=True)

    filename = "test_50mb.log"
    target_bytes = 50 * 1024 * 1024  # 50MB

    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    workers = range(1, 10)

    output_path = output_dir / filename
    if output_path.exists():
        print(f"  ✓ {filename} already exists")
        return

    print(f"  Generating {filename} (~50MB)...")

    current_bytes = 0
    req_id = 1000
    dt = datetime(2024, 12, 1, 0, 0, 0)

    with open(output_path, 'w') as f:
        while current_bytes < target_bytes:
            level = random.choice(levels)
            worker = random.choice(workers)
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

            line = f"{timestamp} {level} [worker-{worker}] service - Processing request {req_id}\n"
            f.write(line)

            current_bytes += len(line)
            req_id += 1
            dt += timedelta(seconds=random.randint(1, 5))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    → {size_mb:.1f} MB")


def generate_json_data(output_dir):
    """Generate 50MB JSON file"""
    print("Generating 50MB JSON file...")
    os.makedirs(output_dir, exist_ok=True)

    filename = "test_50mb.json"
    # ~400K items = ~50MB JSON (with indent=2)
    item_count = 400000

    categories = ["A", "B", "C", "D", "E"]
    base_date = datetime(2024, 12, 1, 0, 0, 0)

    output_path = output_dir / filename
    if output_path.exists():
        print(f"  ✓ {filename} already exists")
        return

    print(f"  Generating {filename} ({item_count} items)...")

    items = []
    for i in range(item_count):
        dt = base_date + timedelta(hours=i)
        items.append({
            "id": i,
            "timestamp": dt.isoformat(),
            "value": random.randint(100, 1000),
            "category": random.choice(categories),
            "name": f"item_{i % 60}"  # Creates duplicates for dedup testing
        })

    with open(output_path, 'w') as f:
        json.dump(items, f, indent=2)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    → {size_mb:.1f} MB")


def generate_text_files(output_dir):
    """Generate 50MB text file"""
    print("Generating 50MB text file...")
    os.makedirs(output_dir, exist_ok=True)

    filename = "test_50mb.txt"
    target_bytes = 50 * 1024 * 1024  # 50MB

    sample_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10

    output_path = output_dir / filename
    if output_path.exists():
        print(f"  ✓ {filename} already exists")
        return

    print(f"  Generating {filename}...")

    with open(output_path, 'w') as f:
        current_bytes = 0
        while current_bytes < target_bytes:
            f.write(sample_text + "\n")
            current_bytes += len(sample_text) + 1

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    → {size_mb:.1f} MB")


def create_git_repo(output_dir):
    """Create a simple git repository for testing"""
    print("Creating test git repository...")
    os.makedirs(output_dir, exist_ok=True)

    # Simple test file
    test_file = output_dir / "README.md"
    if not test_file.exists():
        with open(test_file, 'w') as f:
            f.write("# Test Repository\n\nThis is a test git repository for MCP git tools.\n")

    print(f"  ✓ Created {output_dir}")
    print("  ⚠️  Run manually: cd test_data/git_repo && git init && git add . && git commit -m 'Initial commit'")


def main():
    print("="*60)
    print("Test Data Generation - ALL 50MB Files")
    print("="*60)
    print()

    # Create base directory
    base_dir = Path("test_data")
    base_dir.mkdir(exist_ok=True)

    # Generate each type of test data - ALL 50MB
    generate_images(base_dir)
    generate_logs(base_dir)
    generate_json_data(base_dir)
    generate_text_files(base_dir)
    create_git_repo(base_dir / "git_repo")

    print()
    print("="*60)
    print("✓ Test data generation complete!")
    print("  All files are 50MB for meaningful execution time")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Initialize git repo:")
    print("   cd test_data/git_repo && git init && git add . && git commit -m 'Initial'")
    print()
    print("2. Copy to /tmp for WASM testing:")
    print("   ./setup_test_data_for_wasm.sh")
    print()


if __name__ == "__main__":
    main()
