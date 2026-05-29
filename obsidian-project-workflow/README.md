# obsidian-project-workflow

把 Obsidian 变成项目协作中枢：从点子入池、需求分析、任务执行、Review 到验收归档，都沉淀在可链接、可检索、可追溯的 vault 中。

## 前提条件

使用本 skill 前，需要准备：

1. 已安装并启动 Obsidian。

2. 在 Obsidian 设置中启用命令行界面。

   本 skill 优先通过 `obsidian` CLI 读写当前已启动的 Obsidian vault。启用后可在终端验证：

   ```bash
   obsidian help
   ```

3. 已安装并启用 Obsidian Kanban 插件。

   本 skill 创建和维护的 `*任务看板.md` 使用 Kanban 插件格式，需要插件识别以下 metadata：

   ```yaml
   ---

   kanban-plugin: board

   ---
   ```

4. 当前 Obsidian 窗口已聚焦到目标 vault。

   默认情况下，`obsidian` CLI 会操作最近聚焦的 vault。多 vault 同时打开时，需要确保目标 vault 是当前聚焦 vault，或在命令中显式使用 `vault=<name>`。

## 目录约定

项目初始化后会在 Obsidian vault 中创建：

```text
项目名称/
├── 文档/
└── 任务/
    ├── *任务看板.md
    └── Tasks/
```

`项目任务看板.md` 是默认看板名，也可以使用 `研发任务看板.md`、`客户端任务看板.md` 等 `*任务看板.md`。

## 路径约束

- 不把会话目录、源码目录或 skill 安装目录当作 Obsidian vault。
- 优先通过 `obsidian` CLI 操作当前已启动的 vault。
- 只有脚本初始化或 CLI 无法完成操作时，才解析 vault 文件系统路径。
