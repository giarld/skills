#!/usr/bin/env python3
"""Print the resolved Obsidian vault root path."""

from __future__ import annotations

import argparse

from vault_utils import resolve_vault_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", help="Explicit vault path override.")
    args = parser.parse_args()

    print(resolve_vault_path(args.vault_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
