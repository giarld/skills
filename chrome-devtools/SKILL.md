---
name: chrome-devtools
description: "Uses Chrome DevTools via MCP for efficient debugging, troubleshooting and browser automation. Use when debugging web pages, automating browser interactions, analyzing performance, or inspecting network requests. This skill does not apply to --slim mode (MCP configuration)."
metadata:
  requires:
    bins:
      - node
      - npx
---

# Chrome DevTools via MCP

Use this skill when the agent needs a real browser through Chrome DevTools MCP rather than shell-only or HTTP-only inspection.

## Bundled MCP config

This skill ships with:

- `mcp-config.example.json`

Use that file as the starting point for your MCP client config. The default config launches the official server with:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

If your client already provides a Chrome instance, add `--browser-url=http://127.0.0.1:9222` to `args` and point it at the correct DevTools port.

## Core concepts

- Browser lifecycle: the browser is started or attached when a tool actually needs it, not merely when the MCP server connects.
- Page selection: tools operate on the currently selected page. Use `list_pages`, then `select_page` before interacting.
- Element interaction: use `take_snapshot` to get fresh `uid` values before `click`, `fill`, or other element actions.

## Workflow pattern

Before interacting with a page:

1. Navigate with `navigate_page` or `new_page`.
2. Wait with `wait_for` when you know the page text or state you need.
3. Snapshot with `take_snapshot` to inspect the current accessibility tree.
4. Interact using the returned element `uid`s.

## Tool selection

- Use `take_snapshot` for reliable automation and DOM-like inspection.
- Use `take_screenshot` when the user needs the visual state.
- Use `evaluate_script` when the needed data is not exposed in the accessibility tree.
- Use network, console, performance, and Lighthouse tools when debugging runtime issues.

## Efficient usage

- Prefer `filePath` for large snapshots, screenshots, and traces.
- Use pagination and filtering for console or network output.
- Keep action order correct: navigate -> wait -> snapshot -> interact.
- Avoid stale element ids by taking a fresh snapshot after page changes.

## Troubleshooting

- If `chrome-devtools-mcp` cannot launch Chrome, verify local Chrome installation and check the official troubleshooting guide.
- If the MCP client already controls a browser, prefer attaching with `--browser-url` instead of launching a separate instance.
- If the MCP route is insufficient, fall back to Chrome DevTools UI:
  - https://developer.chrome.com/docs/devtools
  - https://developer.chrome.com/docs/devtools/ai-assistance
