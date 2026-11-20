"""Serveur MCP minimal pour les tests (transport stdio, JSON-RPC 2.0).

Expose un unique outil `echo` qui renvoie le texte reçu, préfixé. Sert à
vérifier que le client MCP de HORIZON parle bien le protocole.
"""
from __future__ import annotations

import json
import sys


def _send(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        method = message.get("method")
        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "echo", "version": "1.0"},
                },
            })
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _send({
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {"tools": [{"name": "echo", "description": "renvoie le texte", "inputSchema": {"type": "object"}}]},
            })
        elif method == "tools/call":
            arguments = message.get("params", {}).get("arguments", {})
            text = str(arguments.get("text", ""))
            _send({
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {"content": [{"type": "text", "text": "echo:" + text}]},
            })
        elif "id" in message:
            _send({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "methode inconnue"}})


if __name__ == "__main__":
    main()
