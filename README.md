# open-in-rex

`open-in-rex` is a Claude Code skill and a small command-line tool called `cresume`. It lets you take a conversation from the Claude desktop app's Code tab and continue it in the [Rex](https://www.superlogical.com/rex) terminal with the Claude Code CLI.

## Why

The Claude desktop app has a Code tab where you run Claude Code sessions, listed in the sidebar by title. Sometimes you want to continue one of those conversations in a real terminal using `claude --resume <session-id>`.

To do that, you need two things the desktop app does not show: the session's folder and the CLI session ID. There is no button to copy the session ID or show the folder, and sessions started without a folder live in hidden temporary directories (there can be dozens of them).

`open-in-rex` finds both the folder and the session ID from the session title, then continues the session in Rex.

## Requirements

- macOS
- Claude desktop app (Code tab) and the Claude Code CLI (`claude` on `PATH`)
- [Rex](https://www.superlogical.com/rex) (the app is named "Rex Beta") with the `rex` CLI
- Python 3 and `jq`

## Install

```sh
git clone https://github.com/minqiyang/open-in-rex ~/.claude/skills/open-in-rex
mkdir -p ~/.local/bin
ln -s ~/.claude/skills/open-in-rex/scripts/cresume.py ~/.local/bin/cresume
```

Make sure `~/.local/bin` is on your `PATH`. Claude Code loads skills from `~/.claude/skills/`, so the skill will be ready in new sessions.

## Usage

### From a Claude session

Inside a Claude desktop session, type `/open-in-rex`, or ask in plain words (for example, "open this session in Rex" or "在 CLI 里打开这个会话"). Claude will open a new Rex tab that continues the current session.

You can also ask Claude to open a different session by giving its sidebar title, or ask it to just copy the resume command to the clipboard.

### From the terminal (`cresume`)

`scripts/cresume.py` is a single Python 3 file using only the standard library. You can run it directly in any terminal:

```sh
cresume "Context bloat"            # continue the session whose title contains "Context bloat"
cresume "Context bloat" --print    # only print the command: cd '<folder>' && claude --resume <id>
cresume "Context bloat" --print | pbcopy   # copy that command
cresume 90ae6653-1c14-4e7d-8ca6-779d10984a7c   # continue a session by its Claude Code session ID
cresume "HW3" --fork-session       # extra options go to claude; this one starts a copy of the session
cresume                            # inside a Claude session: use the current session ($CLAUDE_CODE_SESSION_ID)
```

## How it works

### `cresume`

- **Title search:** Reads the Claude desktop app's session files in `~/Library/Application Support/Claude/claude-code-sessions/`. Each file holds the sidebar title, the CLI session ID, and the folder. Matching is case-insensitive and accepts partial titles, though an exact title match wins over a partial one. Lookups take about 0.1 seconds.
- **Multiple matches:** If more than one session matches the title, `cresume` prints a list showing the last activity time, session ID, title, and `(archived)` if archived, then stops. You can then run it again with the specific session ID.
- **Session ID lookup:** When given a session ID, it also works for plain CLI sessions that the desktop app does not know about, reading the folder from the transcript in `~/.claude/projects/`.
- **Folder matching:** It starts `claude` in the folder that matches where Claude Code stored the transcript, so `claude --resume` can find it.
- **Waiting for active turns:** Before starting `claude`, it checks `~/.claude/sessions/` to see if another process (like the desktop app) has the session open. If that process is busy in a turn, `cresume` waits until it is idle (`Ctrl-C` cancels) before continuing the same session ID. Passing `--fork-session` skips waiting.
- **Concurrent use warning:** If the session is still open in the desktop app, `cresume` prints a reminder not to type in both places at once, since both write to the same transcript.
- **Error handling:** It stops with a clear message if no title matches, if the transcript is missing, or if the folder no longer exists (such as a deleted session's temporary folder).

### The Claude Code skill (`SKILL.md`)

- If Rex already has a session, the skill runs `rex run -s <rex-session> --label "<title>" -- cresume <session-id>` to open a new tab. If Rex has more than one session, Claude asks which one to use. If Rex has no session, it runs `rex new -- cresume <session-id>`.
- Next, it runs `open -a "Rex Beta"` and selects that Rex session in the app.
- When you run the skill for the session you are currently talking in, the new Rex tab waits until Claude's current turn finishes, then continues the session.

## Notes and limits

- This tool reads internal files written by the Claude desktop app and Claude Code. Their format is not a public API and may change.
- Tested on one Mac with Claude Code 2.1.318 and Rex Beta 0.1.0.
- It does not move sessions between machines; it only works on the Mac where the session ran.
