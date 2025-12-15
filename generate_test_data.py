#!/usr/bin/env python3
"""
Generate test data for MCP tool profiling

Based on EdgeAgent-Profiling-for-coremark-v1/test_data/README.md
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
    """Generate test images"""
    if not HAS_IMAGE_LIBS:
        print("Skipping image generation (PIL/numpy required)")
        return

    print("Generating test images...")
    os.makedirs(output_dir, exist_ok=True)

    image_sizes = [
        ("test_1mp.png", 1000, 1000, 1),
        ("test_4mp.png", 2000, 2000, 4),
        ("test_9mp.png", 3000, 3000, 9),
        ("test_16mp.png", 4000, 4000, 16),
        ("test_25mp.png", 5000, 5000, 25),
    ]

    for filename, width, height, mp in image_sizes:
        output_path = output_dir / filename
        if output_path.exists():
            print(f"  ✓ {filename} already exists")
            continue

        print(f"  Generating {filename} ({mp}MP, {width}x{height})...")
        np.random.seed(42)
        data = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        img = Image.fromarray(data)
        img.save(output_path, "PNG")
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"    → {size_mb:.1f} MB")


def generate_logs(output_dir):
    """Generate test log files"""
    print("Generating test log files...")
    os.makedirs(output_dir, exist_ok=True)

    log_sizes = [
        ("test_tiny.log", 1_000),        # ~1KB
        ("test_small.log", 100_000),     # ~100KB
        ("test_medium.log", 500_000),    # ~500KB
        ("test_large.log", 1_000_000),   # ~1MB
        ("test_xlarge.log", 10_000_000), # ~10MB
    ]

    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    workers = range(1, 10)

    for filename, target_bytes in log_sizes:
        output_path = output_dir / filename
        if output_path.exists():
            print(f"  ✓ {filename} already exists")
            continue

        print(f"  Generating {filename} (~{target_bytes/1000:.0f}KB)...")

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

        size_kb = output_path.stat().st_size / 1024
        print(f"    → {size_kb:.1f} KB")


def generate_json_data(output_dir):
    """Generate test JSON data"""
    print("Generating test JSON files...")
    os.makedirs(output_dir, exist_ok=True)

    json_sizes = [
        ("test_1k.json", 1_000),
        ("test_5k.json", 5_000),
        ("test_10k.json", 10_000),
        ("test_50k.json", 50_000),
        ("test_100k.json", 100_000),
    ]

    categories = ["A", "B", "C", "D", "E"]
    base_date = datetime(2024, 12, 1, 0, 0, 0)

    for filename, item_count in json_sizes:
        output_path = output_dir / filename
        if output_path.exists():
            print(f"  ✓ {filename} already exists")
            continue

        print(f"  Generating {filename} ({item_count} items)...")

        items = []
        for i in range(item_count):
            dt = base_date + timedelta(hours=i)
            items.append({
                "id": i,
                "timestamp": dt.isoformat(),
                "value": random.randint(100, 1000),
                "category": random.choice(categories),
                "name": f"item_{i % 100}"  # Creates duplicates for dedup testing
            })

        with open(output_path, 'w') as f:
            json.dump(items, f, indent=2)

        size_kb = output_path.stat().st_size / 1024
        print(f"    → {size_kb:.1f} KB")


def generate_text_files(output_dir):
    """Generate test text files"""
    print("Generating test text files...")
    os.makedirs(output_dir, exist_ok=True)

    text_sizes = [
        ("test_tiny.txt", 1_000),
        ("test_small.txt", 100_000),
        ("test_medium.txt", 500_000),
        ("test_large.txt", 1_000_000),
    ]

    sample_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10

    for filename, target_bytes in text_sizes:
        output_path = output_dir / filename
        if output_path.exists():
            print(f"  ✓ {filename} already exists")
            continue

        print(f"  Generating {filename}...")

        with open(output_path, 'w') as f:
            current_bytes = 0
            while current_bytes < target_bytes:
                f.write(sample_text + "\n")
                current_bytes += len(sample_text) + 1

        size_kb = output_path.stat().st_size / 1024
        print(f"    → {size_kb:.1f} KB")


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
    print("Test Data Generation")
    print("="*60)
    print()

    # Create base directory
    base_dir = Path("test_data")
    base_dir.mkdir(exist_ok=True)

    # Generate each type of test data
    generate_images(base_dir / "images" / "size_test")
    generate_logs(base_dir / "files")
    generate_json_data(base_dir / "files" / "aggregate_test")
    generate_text_files(base_dir / "files")
    create_git_repo(base_dir / "git_repo")

    print()
    print("="*60)
    print("✓ Test data generation complete!")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Initialize git repo:")
    print("   cd test_data/git_repo && git init && git add . && git commit -m 'Initial'")
    print()
    print("2. Copy to /tmp for WASM testing:")
    print("   cp -r test_data/* /tmp/")
    print()


if __name__ == "__main__":
    main()
