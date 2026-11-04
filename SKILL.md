---
name: open-in-rex
description: "Use when the user wants to continue a Claude desktop app session in the Rex terminal (the CLI): 在 Rex 里打开这个会话, 在 CLI 里续上, 在终端里继续这个会话, 把这个会话转到 Rex, 复制续接命令, open this session in Rex, continue this in the CLI. Opens a new Rex tab that runs claude --resume for this session, or for another session the user names by its sidebar title. Can also copy the resume command."
---

# Open in Rex

`cresume` is on PATH (source: `scripts/cresume.py` in this skill). It finds a session by its title in the app sidebar, or by its Claude Code session ID. Then it runs `claude --resume` in the session's folder. While the app is busy with that session, it waits. So a Rex tab that you open for this session continues the same session after this turn ends.

## Steps

1. Choose the session.
   - The user names no session: use this session. Its ID is `$CLAUDE_CODE_SESSION_ID`.
   - The user names a session: run `cresume "<title>" --print`. If it lists more than one session, show the list and ask which one. Use the ID of that session.
   - The user only wants the command (for example, to copy it): run `cresume ["<title>"] --print | pbcopy`. Tell the user that the command is on the clipboard, and stop here.
2. Open the tab in Rex. Run `rex ls --json`.
   - One Rex session: use its `session_id` as `S`, then run:
     `rex run -s "$S" --label "<session title>" -- cresume <session ID>`
   - More than one Rex session: ask the user which one. Then do as for one session.
   - No Rex session: run `rex new --json -- cresume <session ID>`. Its first tab runs `cresume`. Use `.session_id` as `S`.
3. Show it in the Rex app. `open -a` comes first, because the app cannot select a session when it has no window:
   ```sh
   open -a "Rex Beta"
   C=$(rex client ls --json | jq -r '[.clients[] | select(.info.kind=="app")][0].client_id')
   rex -C "$C" do session.select session_id="$S"
   ```
   If `session.select` fails, continue. The tab is in Rex, and the user can select it.
4. Tell the user in one or two sentences that the session is open in Rex. For this session, say that the Rex tab starts when this turn ends. Then end the turn at once. Do no other work, because the Rex tab waits for this turn to end.

## Rules

- Do not add `--fork-session` unless the user asks for a copy. Without it, Rex continues the same session ID.
- When the session continues in Rex, the user must not type in the app and in Rex at the same time, because both write to the same transcript. Tell the user this once.
- If `cresume` fails, show its message. Do not guess a folder or a session ID.
