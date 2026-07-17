# obsidian-cli quick reference

Use `obsidian help` as the source of truth because installed command support can vary.

## Command shape

Parameters use `key=value`. Quote values containing spaces.

```bash
obsidian eval code="app.vault.adapter.getBasePath ? app.vault.adapter.getBasePath() : app.vault.adapter.basePath"
obsidian read path="Project Name/Planning/Task Board.md"
obsidian create name="Project Name/Planning/Task Board" content="..." silent
obsidian append path="Project Name/Planning/Task Board.md" content="- [ ] [[Project Name/Planning/Tasks/Task Title|Task Title]]"
obsidian search query="status: Review" limit=20
obsidian backlinks path="Project Name/Planning/Tasks/Task Title.md"
obsidian property:set path="Project Name/Planning/Tasks/Task Title.md" name="status" value="In Progress"
```

## Targeting

- Prefer `obsidian` CLI over filesystem access for note reads, searches, and edits.
- Commands target the most recently focused vault by default.
- Do not use the current working/session directory as a fallback vault.
- Prefer `path=<vault-relative path>` for deterministic project operations.
- Use `file=<note name>` only when the note name is unique enough.
- Add `vault=<vault name>` first when multiple vaults are open.
- Use `silent` for automation to avoid opening each created note.
- Resolve the active running vault with `obsidian eval` only when direct filesystem access is necessary.

## Fallback

If Obsidian is closed or the CLI is unavailable, use direct filesystem operations only after resolving a vault path from explicit user input or `OBSIDIAN_VAULT_PATH`. Preserve UTF-8 without BOM and Obsidian Markdown syntax.
