import asyncio
import json
import sys
from pathlib import Path

# Add parent to path so we can import SERVER_PATHS
sys.path.insert(0, str(Path(__file__).parent))
from agent.agent import SERVER_PATHS

async def test_server(name, path):
    print(f"\n=== Testing {name} server ===")
    server_dir = str(Path(path).parent)
    env = {
        "CHROMA_LOG_LEVEL": "WARNING",
        "GRPC_VERBOSITY": "ERROR",
        "TRANSFORMERS_VERBOSITY": "error",
        "TOKENIZERS_PARALLELISM": "false",
        "OMP_NUM_THREADS": "1",
    }
    proc = await asyncio.create_subprocess_exec(
        sys.executable, path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=server_dir,
        env={**env, **dict(os.environ)}   # merge with current env
    )
    try:
        # Send initialize request
        init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        proc.stdin.write((json.dumps(init_req) + "\n").encode())
        await proc.stdin.drain()
        # Wait for response
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
        if not line:
            print(f"❌ {name}: No response (process died?)")
            stderr = await proc.stderr.read()
            if stderr:
                print(f"stderr: {stderr.decode()}")
            return
        resp = json.loads(line.decode())
        print(f"✅ {name}: initialize response received: {resp.get('result', {}).get('serverInfo', {}).get('name', 'unknown')}")
        # Send tools/list
        tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        proc.stdin.write((json.dumps(tools_req) + "\n").encode())
        await proc.stdin.drain()
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
        resp = json.loads(line.decode())
        tools = resp.get('result', {}).get('tools', [])
        print(f"✅ {name}: {len(tools)} tools found")
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        stderr = await proc.stderr.read()
        if stderr:
            print(f"stderr: {stderr.decode()}")
    finally:
        proc.terminate()
        await proc.wait()

async def main():
    for name, path in SERVER_PATHS.items():
        await test_server(name, path)

if __name__ == "__main__":
    import os
    asyncio.run(main())