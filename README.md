# Skills

Reusable agent skills and helper scripts for common automation workflows.

## Included Skills

| Skill | Purpose | Entry Files | Install |
| --- | --- | --- | --- |
| `battle-memory` | Store, distill, refine, and compress project task memory with redaction safeguards | `battle-memory/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill battle-memory` |
| `bilibili-video` | Fetch Bilibili metadata, hot comments, videos, and cover images | `bilibili-video/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill bilibili-video` |
| `chrome-devtools` | Use Chrome DevTools via MCP for browser automation, debugging, network inspection, and performance analysis | `chrome-devtools/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill chrome-devtools` |
| `imagegen-openai` | Generate and edit images through OpenAI or a compatible API, with streaming and batch support | `imagegen-openai/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill imagegen-openai` |
| `make-pdf` | Generate a compilable LaTeX document and final PDF from mixed source materials | `make-pdf/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill make-pdf` |
| `multica-cli` | Interact with Multica CLI for workspaces, issues, agents, daemon, runtimes, and automation | `multica-cli/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill multica-cli` |
| `obsidian-project-workflow` | Operate an Obsidian-backed project workflow with Kanban boards, task notes, and vault-aware helper scripts | `obsidian-project-workflow/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill obsidian-project-workflow` |
| `videogen-h3` | Generate, regenerate, track, and download videos through the MiniMax H3 V2 API | `videogen-h3/SKILL.md` | `npx skills add https://github.com/giarld/skills --skill videogen-h3` |

## Skill Details

### `battle-memory`

Store AI Agent task output and task-relevant dialogue as durable project memory.

- Install:

```bash
npx skills add https://github.com/giarld/skills --skill battle-memory
```

- Entry files:
  - `battle-memory/SKILL.md`
  - `battle-memory/agents/openai.yaml`
- Features:
  - initialize project-level `AGENTS.md` and `CLAUDE.md` guidance with `$battle-memory init`
  - perform relevance-first `.memory/` and project-doc context intake
  - distill important task dialogue without storing raw chat logs
  - create or update searchable task memory after durable project work
  - refine, compress, consolidate, or supersede existing memory records
  - redact secrets, credentials, private personal data, and raw confidential values
- Invocation:
  - may be enabled implicitly by project instructions such as `AGENTS.md`
  - can also be invoked explicitly through `$battle-memory`

Typical use case:

```text
Use $battle-memory to continue a feature from prior project memory, complete the work, and store a redacted continuation note.
Use $battle-memory init to add Battle Memory auto-loading guidance to AGENTS.md and CLAUDE.md.
```

### `bilibili-video`

Fetch and process Bilibili videos by BV id or URL.

- Install:

```bash
npx skills add https://github.com/giarld/skills --skill bilibili-video
```

- Entry files:
  - `bilibili-video/SKILL.md`
  - `bilibili-video/scripts/bili_fetch.py`
  - `bilibili-video/scripts/bili_grab.sh`
  - `bilibili-video/scripts/bili_download.sh`
- Features:
  - fetch structured metadata through the public API
  - fetch hot comments
  - download videos with `yt-dlp`
  - download cover images with matching filenames
- Optional environment variables:
  - `BILI_OUT_DIR` default `./video`
  - `YTDLP` default `yt-dlp`
  - `BILI_COOKIE` for logged-in access when needed
  - `BILI_OVERWRITE_COVER` default `0`

Quick examples:

```bash
python3 bilibili-video/scripts/bili_fetch.py "https://www.bilibili.com/video/BVxxxx"
bilibili-video/scripts/bili_grab.sh "https://www.bilibili.com/video/BVxxxx/"
```

### `chrome-devtools`

Use Chrome DevTools through MCP for browser automation and debugging.

- Install:

```bash
npx skills add https://github.com/giarld/skills --skill chrome-devtools
```

- Entry files:
  - `chrome-devtools/SKILL.md`
  - `chrome-devtools/mcp-config.example.json`
- Features:
  - browser automation through Chrome DevTools MCP
  - page snapshots and screenshots
  - console and network inspection
  - performance trace and Lighthouse workflows
- Requirements:
  - `node`
  - `npx`
  - MCP client support

Quick start:

```bash
npx skills add https://github.com/giarld/skills --skill chrome-devtools
cat chrome-devtools/mcp-config.example.json
```

### `imagegen-openai`

Generate or edit images through OpenAI or an OpenAI-compatible provider using Python 3.8+ (no third-party packages required). The helper supports model discovery, reference and masked edits, streaming previews, Responses, and Batch where the selected provider and model support them.

```bash
npx skills add https://github.com/giarld/skills --skill imagegen-openai
python imagegen-openai/scripts/imagegen.py --help
```

Set `IMAGEGEN_OPENAI_API_KEY` in the execution environment for live requests. Optionally set `IMAGEGEN_OPENAI_API_BASE_URL` to the complete API base of a compatible provider. Model IDs and capabilities are evaluated for the configured provider and endpoint. See [SKILL.md](imagegen-openai/SKILL.md) for selection and discovery, and [API examples](imagegen-openai/references/api.md) for request formats.

### `make-pdf`

Generate a professional LaTeX document and compile it into a final PDF.

- Install:

```bash
npx skills add https://github.com/giarld/skills --skill make-pdf
```

- Entry files:
  - `make-pdf/SKILL.md`
  - `make-pdf/assets/document-template.tex`
- Features:
  - start from a reusable LaTeX template
  - support notes, reports, tutorials, explainers, and figure-rich documents
  - handle mixed source inputs such as outlines, transcripts, screenshots, and code
  - require final PDF compilation as part of delivery
- Preferred toolchain:
  - `latexmk -xelatex`
  - fallback to repeated `xelatex` runs if needed

Typical use case:

```text
Use this skill when source materials need to be turned into a complete,
compilable `.tex` file and a polished PDF.
```

### `multica-cli`

Interact with Multica through the local `multica` CLI.

- Install:

```bash
npx skills add https://github.com/giarld/skills --skill multica-cli
```

- Entry files:
  - `multica-cli/SKILL.md`
  - `multica-cli/references/cli.md`
- Features:
  - verify CLI installation, authentication, workspace, daemon, and runtime status
  - manage issues, projects, comments, agents, skills, squads, and autopilots
  - inspect agent runs and daemon logs
  - prefer local `multica <command> --help` to handle CLI version drift

Quick examples:

```bash
multica version
multica auth status
multica workspace list --output json
multica daemon status --output json
multica issue list --limit 20 --output json
```

### `obsidian-project-workflow`

Operate an Obsidian-backed project workflow with `obsidian` CLI and the Obsidian Kanban plugin.

- Install:

```bash
npx skills add https://github.com/giarld/skills --skill obsidian-project-workflow
```

- Entry files:
  - `obsidian-project-workflow/SKILL.md`
  - `obsidian-project-workflow/README.md`
  - `obsidian-project-workflow/scripts/board_utils.py`
  - `obsidian-project-workflow/scripts/init_project.py`
  - `obsidian-project-workflow/scripts/create_task.py`
  - `obsidian-project-workflow/scripts/move_task.py`
  - `obsidian-project-workflow/scripts/record_commit.py`
  - `obsidian-project-workflow/scripts/resolve_vault.py`
  - `obsidian-project-workflow/references/obsidian-cli-quickref.md`
  - `obsidian-project-workflow/references/workflow-model.md`
- Features:
  - query project task boards through the `obsidian` CLI
  - scaffold project folders, Kanban boards, and task notes
  - move tasks through `需求池 -> 待执行 -> 执行中 -> Review -> 完成 -> Archive`
  - preserve Obsidian vault paths and Kanban plugin metadata
- Requirements:
  - Obsidian installed and running
  - Obsidian CLI enabled
  - Obsidian Kanban plugin enabled

Quick examples:

```bash
obsidian search query="任务看板" limit=20
python3 obsidian-project-workflow/scripts/init_project.py --project-name "项目名称" --board-name "任务看板.md"
python3 obsidian-project-workflow/scripts/create_task.py --project-name "项目名称" --title "登录流程优化" --column "需求池" --board-name "任务看板.md"
python3 obsidian-project-workflow/scripts/move_task.py --project-name "项目名称" --title "登录流程优化" --to-column "Review" --board-name "任务看板.md"
```

On Windows, use `python` and set `PYTHONUTF8=1` when working with non-ASCII project or task names.

### `videogen-h3`

Generate videos from text, frame images, or multimodal references with the MiniMax H3 V2 API. The Python 3.8+ helper also tracks tasks, downloads completed videos, and regenerates eligible 768P outputs at 2K.

```bash
npx skills add https://github.com/giarld/skills --skill videogen-h3
python videogen-h3/scripts/h3.py --help
```

Set `VIDEOGEN_H3_API_KEY` in the execution environment for live requests. Optionally set `VIDEOGEN_H3_API_BASE_URL` to a compatible base URL. See [SKILL.md](videogen-h3/SKILL.md) for model selection and the workflow, and [API examples](videogen-h3/references/api.md) for request formats.

## Repository Layout

```text
.
|-- README.md
|-- battle-memory/
|   |-- SKILL.md
|   `-- agents/
|-- bilibili-video/
|   |-- SKILL.md
|   `-- scripts/
|-- chrome-devtools/
|   |-- SKILL.md
|   `-- mcp-config.example.json
|-- imagegen-openai/
|   |-- LICENSE
|   |-- SKILL.md
|   |-- agents/
|   |-- references/
|   `-- scripts/
|-- make-pdf/
|   |-- SKILL.md
|   `-- assets/
|-- multica-cli/
|   |-- SKILL.md
|   |-- agents/
|   `-- references/
|-- obsidian-project-workflow/
|   |-- SKILL.md
|   |-- README.md
|   |-- agents/
|   |-- assets/
|   |-- references/
|   `-- scripts/
`-- videogen-h3/
    |-- LICENSE
    |-- SKILL.md
    |-- agents/
    |-- references/
    `-- scripts/
```

## Notes

- Each skill directory contains its own detailed `SKILL.md`.
- Prefer using the bundled scripts and templates instead of re-implementing the workflow from scratch.
- Follow applicable laws, licenses, and platform terms when downloading or transforming third-party content.
