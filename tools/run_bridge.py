#!/usr/bin/env python3
"""Run a Ghidra script through the GhidraMCP bridge over stdio.

One MCP session covers initialize, connect and execution, because reconnecting
per call adds noise and can race project selection. The script's println output
comes back as console_output.

    python3 run_bridge.py --project mcpsamplebin ResearchDecompile.java 0x17580d0
    python3 run_bridge.py --project mcpsamplebin --program knob.bin HpssRefs.java 0x153ed40
"""
import argparse
import json
import shutil
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("script", help="Ghidra script file name, e.g. ResearchDecompile.java")
    ap.add_argument("args", nargs="*", help="script arguments, e.g. Ghidra VAs")
    ap.add_argument(
        "--bridge",
        default=None,
        help="path to bridge-mcp-ghidra (default: look it up on PATH)",
    )
    ap.add_argument(
        "--project",
        default=None,
        help="Ghidra project to connect to (required by bridge 1.30.0)",
    )
    ap.add_argument("--program", default=None, help="program name, when several are open")
    ap.add_argument("--timeout", type=int, default=300, help="script timeout, seconds (default 300)")
    a = ap.parse_args()

    bridge = a.bridge or shutil.which("bridge-mcp-ghidra")
    if not bridge:
        sys.exit(
            "bridge-mcp-ghidra not found: install it, put it on PATH, or pass --bridge"
        )

    p = subprocess.Popen(
        [bridge, "--transport", "stdio", "--no-lazy"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    def call(i, method, params):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n")
        p.stdin.flush()
        while True:
            line = p.stdout.readline()
            if not line:
                sys.exit("bridge closed the connection during %s" % method)
            try:
                msg = json.loads(line)
            except ValueError:
                continue  # the bridge may log to stdout before the reply
            if msg.get("id") == i:
                return msg

    def tool(i, name, arguments):
        """Call one MCP tool and return (is_error, text)."""
        r = call(i, "tools/call", {"name": name, "arguments": arguments})
        if r.get("error"):
            sys.exit("MCP error calling %s: %s" % (name, r["error"]))
        res = r.get("result", {})
        content = res.get("content") or [{}]
        text = content[0].get("text", "") if content else ""
        return bool(res.get("isError")), text

    try:
        call(1, "initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "ghidra-decompile", "version": "1"},
        })
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        p.stdin.flush()

        err, text = tool(2, "connect_instance", {"project": a.project} if a.project else {})
        if err:
            hint = ""
            if "project" in text.lower():
                hint = "\n  -> pass --project <name>"
            elif "instance" in text.lower():
                hint = "\n  -> start Ghidra, open the project, then retry"
            sys.exit("connect_instance failed: %s%s" % (text.strip().splitlines()[0], hint))

        script_args = {
            "script_name": a.script,
            "args": " ".join(a.args),
            "timeout_seconds": a.timeout,
            "capture_output": True,
        }
        if a.program:
            script_args["program"] = a.program
        err, text = tool(3, "run_ghidra_script", script_args)

        if "unknown tool" in text.lower():
            sys.exit(
                "run_ghidra_script is not exposed by this bridge build: check that a Ghidra "
                "instance is connected (list_instances), then load_tool_group() if needed"
            )

        try:
            decoded = json.loads(text)
        except (ValueError, TypeError):
            decoded = None
        print(decoded.get("console_output", text) if isinstance(decoded, dict) else text)

        if err or (isinstance(decoded, dict) and decoded.get("success") is False):
            sys.exit(1)
    finally:
        p.terminate()


if __name__ == "__main__":
    main()
