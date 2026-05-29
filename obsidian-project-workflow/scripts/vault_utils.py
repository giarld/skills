"""Vault path resolution helpers for Obsidian workflow scripts."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


VAULT_PATH_JS = """
(() => {
  const adapter = app && app.vault && app.vault.adapter;
  if (adapter && typeof adapter.getBasePath === "function") {
    return adapter.getBasePath();
  }
  if (adapter && typeof adapter.basePath === "string") {
    return adapter.basePath;
  }
  return "";
})()
""".strip()


def _clean_eval_output(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ""
    value = lines[-1]
    value = re.sub(r"^(?:=>|result:|return:)\s*", "", value, flags=re.IGNORECASE)
    try:
        parsed = json.loads(value)
        if isinstance(parsed, str):
            return parsed.strip()
    except json.JSONDecodeError:
        pass
    return value.strip().strip('"').strip("'")


def _resolve_from_obsidian_cli() -> Path | None:
    try:
        result = subprocess.run(
            ["obsidian", "eval", f"code={VAULT_PATH_JS}"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return None

    if result.returncode != 0:
        return None

    raw_path = _clean_eval_output(result.stdout)
    if not raw_path or raw_path in {"undefined", "null"}:
        return None
    return Path(raw_path).expanduser().resolve()


def resolve_vault_path(explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()

    obsidian_path = _resolve_from_obsidian_cli()
    if obsidian_path is not None:
        return obsidian_path

    env_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    raise RuntimeError(
        "Cannot resolve Obsidian vault path. Start Obsidian with obsidian-cli available, "
        "set OBSIDIAN_VAULT_PATH, or pass --vault-path explicitly."
    )
