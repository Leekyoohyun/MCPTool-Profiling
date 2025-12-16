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

# HTTP client for direct JSON-RPC calls (wasmtime serve uses plain HTTP, not MCP streamable)
import httpx

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
# wasmtime serve는 *_http.wasm 버전이 필요 (wasi:http/incoming-handler export)
SERVER_WASM_MAP = {
    'summarize': 'mcp_server_summarize_http.wasm',
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
    import os

    # Get API keys first (need them for command line)
    openai_key = ENV_VARS.get('OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
    anthropic_key = ENV_VARS.get('ANTHROPIC_API_KEY', '') or os.environ.get('ANTHROPIC_API_KEY', '')

    # Build command
    cmd = ['wasmtime', 'serve']

    # Add WASM-specific args
    # wasmtime 21+: use -S for WASI options (not --wasi)
    cmd.extend([
        '--addr', f'127.0.0.1:{port}',
        '-S', 'cli',   # CLI support (env vars, etc.)
        '-S', 'http',  # HTTP outgoing support (for external API calls)
        '--dir=/tmp',
    ])

    # Pass env vars to WASM via --env (subprocess env is NOT enough!)
    if openai_key:
        cmd.extend(['--env', f'OPENAI_API_KEY={openai_key}'])
        print(f"  ✓ OPENAI_API_KEY: {openai_key[:20]}...")
    else:
        print(f"  ⚠️  OPENAI_API_KEY not found (check .env or export)")

    if anthropic_key:
        cmd.extend(['--env', f'ANTHROPIC_API_KEY={anthropic_key}'])
        print(f"  ✓ ANTHROPIC_API_KEY: {anthropic_key[:20]}...")

    cmd.append(str(wasm_file))

    print(f"  Starting wasmtime serve on port {port}...")
    print(f"  Command: {' '.join(cmd[:8])}... {wasm_file.name}")  # Don't print API keys

    # Prepare environment (for subprocess itself, not WASM)
    env = os.environ.copy()

    # Start process with environment variables
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
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


async def call_tool_jsonrpc(client: httpx.AsyncClient, url: str, tool_name: str, arguments: dict) -> dict:
    """Call a tool via JSON-RPC over HTTP"""
    request_id = int(time.time() * 1000)
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": request_id
    }
    response = await client.post(url, json=payload)
    response.raise_for_status()
    result = response.json()

    if "error" in result:
        raise Exception(result["error"].get("message", str(result["error"])))

    return result.get("result", {})


async def measure_server_tools(server_name, tool_names, test_payloads, port=8000, runs=3):
    """Measure all tools for a single server via HTTP (direct JSON-RPC)"""

    wasm_file = WASM_PATH / SERVER_WASM_MAP.get(server_name)
    if not wasm_file.exists():
        print(f"  ⚠️  WASM file not found: {wasm_file}")
        return []

    print(f"\n{'='*60}")
    print(f"Server: {server_name} ({len(tool_names)} tools) - HTTP (no 4KB limit)")
    print(f"{'='*60}")

    results = []

    # Start wasmtime serve
    server_process = start_wasmtime_server(wasm_file, port=port)
    if server_process is None:
        print(f"  ❌ Failed to start HTTP server")
        return []

    url = f"http://127.0.0.1:{port}"

    try:
        # Use httpx for direct JSON-RPC calls (wasmtime serve uses plain HTTP)
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Verify server is responding
            try:
                test_resp = await client.post(url, json={
                    "jsonrpc": "2.0", "method": "tools/list", "id": 1
                })
                if test_resp.status_code != 200:
                    print(f"  ❌ Server not responding properly")
                    return []
                available_tools = [t["name"] for t in test_resp.json().get("result", {}).get("tools", [])]
                print(f"  Available tools: {available_tools}")
            except Exception as e:
                print(f"  ❌ Failed to connect to server: {e}")
                return []

            for tool_name in tool_names:
                if tool_name not in test_payloads:
                    print(f"  ⚠️  {tool_name}: No test payload")
                    continue

                if tool_name not in available_tools:
                    print(f"  ⚠️  {tool_name}: Not found in server")
                    continue

                print(f"  Measuring {tool_name}...", end=' ', flush=True)

                payload = test_payloads[tool_name]
                input_size = len(json.dumps(payload))

                exec_times = []
                output_size = 0

                for run in range(runs):
                    try:
                        start = time.time()
                        result = await call_tool_jsonrpc(client, url, tool_name, payload)
                        end = time.time()

                        exec_times.append(end - start)
                        output_size = len(json.dumps(result))
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
        await asyncio.sleep(0.5)

    except Exception as e:
        print(f"  ❌ Client error: {e}")
        import traceback
        traceback.print_exc()

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
