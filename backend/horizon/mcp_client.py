"""Client MCP minimal (JSON-RPC 2.0 sur entrée/sortie standard).

Permet de brancher les outils exposés par un serveur MCP sans les recoder :
initialisation, liste des outils, appel d'un outil. Aucune réponse n'est
fabriquée : une erreur du serveur devient une `MCPError` explicite.
"""
from __future__ import annotations

import json
import subprocess
from typing import Any


class MCPError(RuntimeError):
    """Erreur MCP, message lisible et sans secret."""


class MCPClient:
    """Client d'un serveur MCP lancé en sous-processus (transport stdio)."""

    def __init__(self, command: str, args: list[str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self._proc: subprocess.Popen | None = None
        self._next_id = 0

    def __enter__(self) -> "MCPClient":
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def start(self) -> "MCPClient":
        try:
            self._proc = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
            )
        except OSError as error:
            raise MCPError(f"Serveur MCP introuvable : {error}") from error
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "horizon", "version": "1.0"},
            },
        )
        self._write({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        return self

    def _write(self, payload: dict[str, Any]) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise MCPError("Serveur MCP non démarré.")
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

    def _read(self) -> dict[str, Any]:
        if self._proc is None or self._proc.stdout is None:
            raise MCPError("Serveur MCP non démarré.")
        line = self._proc.stdout.readline()
        if not line:
            raise MCPError("Serveur MCP fermé sans réponse.")
        try:
            return json.loads(line)
        except ValueError as error:
            raise MCPError("Réponse MCP illisible.") from error

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        self._next_id += 1
        rid = self._next_id
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            message = self._read()
            if message.get("id") != rid:
                continue
            if "error" in message:
                detail = message["error"]
                text = detail.get("message") if isinstance(detail, dict) else str(detail)
                raise MCPError(str(text or "Erreur MCP."))
            return message.get("result")

    def list_tools(self) -> Any:
        return self._request("tools/list", {})

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        return self._request("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:  # pragma: no cover - fermeture best effort
                pass
            self._proc = None
