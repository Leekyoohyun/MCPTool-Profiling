#!/usr/bin/env python3
"""
Phase 2C: Measure WASM Tools via HTTP (no stdio buffer limit)

wasmtime serve를 사용해 HTTP로 WASM 서버 실행
- stdio 4KB 버퍼 제한 없음
- 50MB payload 전송 가능
- summarize, sequentialthinking 측정 가능

Usage:
    python3 2c_measure_http_tools.py

Output:
    - http_tool_exec_time_<hostname>.json
"""

import asyncio
import json
import socket
import sys
import time
import subprocess
import signal
from pathlib import Path

# Load .env file
def load_env_file(env_path=None):
    """Load API keys from .env file"""
    if env_path is None:
        env_path = Path(__file__).parent / ".env"

    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

# Load API keys
ENV_VARS = load_env_file()

# Import EdgeAgent's MCP comparator framework
sys.path.insert(0, str(Path.home() / "EdgeAgent/wasm_mcp/tests"))
from mcp_comparator import MCPServerConfig, TransportType

# Import MCP client
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# Import standard payloads
from standard_payloads import get_standard_payloads

# WASM path
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
    WASM_PATH = WASM_PATH_CANDIDATES[0]

# Server WASM mapping (HTTP로 측정할 도구들)
SERVER_WASM_MAP = {
    'summarize': 'mcp_server_summarize.wasm',
}

# Tools to measure via HTTP
TOOLS_BY_SERVER = {
    'summarize': ['summarize_text', 'get_provider_info'],  # summarize_documents는 제외 (너무 큼)
}


def start_wasmtime_server(wasm_file, port=8000):
    """
    Start wasmtime serve in background

    Args:
        wasm_file: Path to WASM file
        port: HTTP port (default: 8000)

    Returns:
        subprocess.Popen: Server process
    """
    # Build command
    cmd = ['wasmtime', 'serve']

    # Add environment variables for API keys
    env = {}
    openai_key = ENV_VARS.get('OPENAI_API_KEY', '')
    anthropic_key = ENV_VARS.get('ANTHROPIC_API_KEY', '')

    if openai_key:
        env['OPENAI_API_KEY'] = openai_key

    if anthropic_key:
        env['ANTHROPIC_API_KEY'] = anthropic_key

    # Add WASM-specific args
    cmd.extend([
        '--addr', f'127.0.0.1:{port}',
        '--wasi', 'http',
        '--dir=/tmp',
    ])

    # Add env vars
    for key, value in env.items():
        cmd.extend(['--env', f'{key}={value}'])

    cmd.append(str(wasm_file))

    print(f"  Starting wasmtime serve on port {port}...")
    print(f"  Command: {' '.join(cmd)}")

    # Start process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**subprocess.os.environ, **env}
    )

    # Wait for server to start (2 seconds)
    time.sleep(2)

    # Check if process is still running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"  ❌ Server failed to start!")
        print(f"  stdout: {stdout.decode()}")
        print(f"  stderr: {stderr.decode()}")
        return None

    print(f"  ✓ Server started (PID: {process.pid})")
    return process


def stop_wasmtime_server(process):
    """Stop wasmtime serve process"""
    if process and process.poll() is None:
        print(f"  Stopping server (PID: {process.pid})...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print(f"  ✓ Server stopped")
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Force killing server...")
            process.kill()
            process.wait()


async def measure_server_tools(server_name, tool_names, test_payloads, port=8000, runs=3):
    """Measure all tools for a single server via HTTP"""

    wasm_file = WASM_PATH / SERVER_WASM_MAP.get(server_name)
    if not wasm_file.exists():
        print(f"  ⚠️  WASM file not found: {wasm_file}")
        return []

    print(f"\n{'='*60}")
    print(f"Server: {server_name} ({len(tool_names)} tools) - HTTP")
    print(f"{'='*60}")

    results = []

    # Start wasmtime serve
    server_process = start_wasmtime_server(wasm_file, port=port)
    if server_process is None:
        print(f"  ❌ Failed to start HTTP server")
        return []

    try:
        # Create HTTP MCP server config
        server_config = MCPServerConfig.wasmmcp_http(url=f"http://127.0.0.1:{port}")

        # Create client
        client = MultiServerMCPClient({server_name: server_config.config})

        async with client.session(server_name) as session:
            tools = await load_mcp_tools(session)
            tool_map = {t.name: t for t in tools}

            for tool_name in tool_names:
                if tool_name not in test_payloads:
                    print(f"  ⚠️  {tool_name}: No test payload")
                    continue

                if tool_name not in tool_map:
                    print(f"  ⚠️  {tool_name}: Not found in server")
                    continue

                print(f"  Measuring {tool_name}...", end=' ', flush=True)

                tool_obj = tool_map[tool_name]
                payload = test_payloads[tool_name]

                exec_times = []
                output_size = 0
                input_size = sys.getsizeof(json.dumps(payload))

                for run in range(runs):
                    try:
                        start = time.time()
                        result = await tool_obj.ainvoke(payload)
                        end = time.time()

                        exec_times.append(end - start)
                        output_size = sys.getsizeof(json.dumps(result))
                    except Exception as e:
                        print(f"\n    Run {run+1} failed: {e}")
                        continue

                if exec_times:
                    avg_exec_time = sum(exec_times) / len(exec_times)
                    results.append({
                        'tool_name': tool_name,
                        'server': server_name,
                        't_exec_ms': avg_exec_time * 1000,  # Convert to ms
                        'input_size': input_size,
                        'output_size': output_size,
                        'runs': len(exec_times),
                        'measurements_ms': [t * 1000 for t in exec_times],  # Convert to ms
                        'transport': 'http'
                    })
                    print(f"✓ {avg_exec_time*1000:.1f}ms")
                else:
                    print(f"❌ All runs failed")

        # Cleanup delay
        await asyncio.sleep(1.0)

    except Exception as e:
        print(f"  ❌ Client error: {e}")

    finally:
        # Stop server
        stop_wasmtime_server(server_process)

    return results


async def main():
    print("="*60)
    print("Phase 2C: HTTP Tools Measurement (no stdio limit)")
    print("="*60)
    print()

    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print(f"WASM Path: {WASM_PATH}")
    print()

    # Count total tools
    total_tools = sum(len(tools) for tools in TOOLS_BY_SERVER.values())
    print(f"Total tools to measure: {total_tools}")
    print()

    test_payloads = get_standard_payloads()
    all_results = []

    # Measure each server on different ports
    port = 8000
    for server_name, tool_names in TOOLS_BY_SERVER.items():
        results = await measure_server_tools(server_name, tool_names, test_payloads, port=port)
        all_results.extend(results)
        port += 1  # Next server uses next port

    # Save results
    output_file = f'http_tool_exec_time_{hostname}.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print()
    print("="*60)
    print(f"✓ Results saved: {output_file}")
    print(f"  Measured {len(all_results)}/{total_tools} tools via HTTP")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
