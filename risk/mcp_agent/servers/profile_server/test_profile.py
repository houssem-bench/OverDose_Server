#!/usr/bin/env python3
"""
Automated test for IngredientGuard MCP server.
Sends JSON-RPC requests and validates responses.
"""

import json
import subprocess
import sys
import time

SERVER_SCRIPT = "server.py"
USER_TYPE = "Asthma"
INGREDIENT = "sugar"
USE_LLM = True  # Set to True to test LLM (requires GROQ_API_KEY)

def print_result(name, response, is_error=False):
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}")
    if is_error:
        print(f"ERROR: {response}")
    else:
        try:
            parsed = json.loads(response) if isinstance(response, str) else response
            print(json.dumps(parsed, indent=2))
        except:
            print(response)

def main():
    # Start server
    proc = subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    time.sleep(2)  # Allow server to start (not strictly needed but safe)

    def send(req):
        req_str = json.dumps(req) + "\n"
        proc.stdin.write(req_str)
        proc.stdin.flush()
        return proc.stdout.readline().strip()

    # 1. Initialize
    print_result("1. Initialize", send({
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {"protocolVersion": "0.1.0", "capabilities": {}}
    }))

    # 2. tools/list
    print_result("2. Tools list", send({
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    }))

    # 3. retrieve_ingredient
    print_result("3. Retrieve ingredient", send({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 3,
        "params": {
            "name": "retrieve_ingredient",
            "arguments": {"user_type": USER_TYPE, "ingredient": INGREDIENT}
        }
    }))

    # 4. analyze_ingredient (without LLM)
    print_result("4. Analyze ingredient (no LLM)", send({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 4,
        "params": {
            "name": "analyze_ingredient",
            "arguments": {
                "user_type": USER_TYPE,
                "ingredient": INGREDIENT,
                "generate_llm": False
            }
        }
    }))

    # 5. (Optional) analyze_ingredient with LLM
    if USE_LLM:
        print_result("5. Analyze ingredient (with LLM)", send({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 5,
            "params": {
                "name": "analyze_ingredient",
                "arguments": {
                    "user_type": USER_TYPE,
                    "ingredient": INGREDIENT,
                    "generate_llm": True
                }
            }
        }))

    # Wait a moment for stderr to flush
    time.sleep(1)
    proc.terminate()
    stderr = proc.stderr.read()
    if stderr:
        print("\n--- Server stderr (non‑fatal) ---")
        print(stderr)

if __name__ == "__main__":
    main()