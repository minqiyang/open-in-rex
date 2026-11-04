#!/usr/bin/env python3
"""Continue a Claude Code session (also one from the Claude desktop app) here.

Usage:
  cresume [TITLE | SESSION_ID] [--print] [claude options...]

TITLE is the session title in the desktop app sidebar, or a part of it.
SESSION_ID is a Claude Code session ID (a UUID).
With no TITLE or ID, cresume uses $CLAUDE_CODE_SESSION_ID (the session that runs it).
--print   Print the command for the session. Do not run it.
Other options (for example --fork-session) go to `claude`.

When the app is busy with the session, cresume waits until it is idle,
then runs `claude --resume` in the session's folder.
"""
import glob
import json
import os
import re
import shlex
import sys
import time
from typing import NoReturn

PROJECTS = os.path.expanduser("~/.claude/projects")
REGISTRY = os.path.expanduser("~/.claude/sessions")
APP_STORE = os.path.expanduser("~/Library/Application Support/Claude/claude-code-sessions")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
CWD_FIELD = re.compile(r'"cwd":"((?:[^"\\]|\\.)*)"')


def die(msg: str, code: int = 1) -> NoReturn:
    print(f"cresume: {msg}", file=sys.stderr)
    sys.exit(code)


def encode(path):
    """Folder name that Claude Code uses under ~/.claude/projects for path."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def app_sessions():
    """Desktop app sessions: title, CLI session ID, folders, last activity."""
    for path in glob.glob(os.path.join(APP_STORE, "*", "*", "local_*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if d.get("cliSessionId"):
            yield {"id": d["cliSessionId"], "title": d.get("title") or "",
                   "cwds": [c for c in (d.get("cwd"), d.get("originCwd")) if c],
                   "archived": bool(d.get("isArchived")),
                   "time": (d.get("lastActivityAt") or 0) / 1000}


def transcript_cwds(path):
    """Folders recorded in a transcript, for a session the app does not know."""
    cwds = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = CWD_FIELD.search(line)
            if m:
                cwd = json.loads('"' + m.group(1) + '"')
                if cwd not in cwds:
                    cwds.append(cwd)
                if encode(cwd) == os.path.basename(os.path.dirname(path)):
                    break
    return cwds


def find(query):
    if UUID.match(query):
        found = [s for s in app_sessions() if s["id"] == query]
        return found or [{"id": query, "title": "", "cwds": [], "archived": False, "time": 0}]
    q = query.casefold()
    found = [s for s in app_sessions() if q in s["title"].casefold()]
    return [s for s in found if s["title"].casefold() == q] or found


def app_status(session_id):
    """Status of a live process that has the session open, or None."""
    for path in glob.glob(os.path.join(REGISTRY, "*.json")):
        try:
            with open(path) as f:
                d = json.load(f)
            if d.get("sessionId") != session_id:
                continue
            os.kill(d["pid"], 0)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        return d.get("status") or "idle"
    return None


def main(argv):
    show = "--print" in argv
    rest = [a for a in argv if a != "--print"]
    if rest and rest[0] in ("-h", "--help"):
        print((__doc__ or "").strip())
        return
    query = rest.pop(0) if rest and not rest[0].startswith("-") else os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not query:
        die('give a session title or ID, for example: cresume "Context bloat"')

    matches = find(query)
    if not matches:
        die(f'no session in the Claude app has a title that contains "{query}"')
    if len(matches) > 1:
        matches.sort(key=lambda s: s["time"], reverse=True)
        rows = [f'  {time.strftime("%m-%d %H:%M", time.localtime(s["time"]))}  {s["id"]}  {s["title"]}'
                + ("  (archived)" if s["archived"] else "") for s in matches[:15]]
        die("more than one session matches. Run cresume again with one ID:\n" + "\n".join(rows), 2)

    s = matches[0]
    name = s["title"] or s["id"]
    transcripts = glob.glob(os.path.join(PROJECTS, "*", s["id"] + ".jsonl"))
    if not transcripts:
        die(f'no transcript for "{name}" ({s["id"]})')
    # `claude --resume` looks for the transcript under the folder it starts in.
    folder = os.path.basename(os.path.dirname(transcripts[0]))
    cwds = s["cwds"] or transcript_cwds(transcripts[0])
    cwd = next((c for c in cwds if encode(c) == folder), cwds[0] if cwds else None)
    if not cwd or not os.path.isdir(cwd):
        die(f'the folder of "{name}" does not exist any more: {cwd}')

    cmd = ["claude", "--resume", s["id"], *rest]
    if show:
        print(f"cd {shlex.quote(cwd)} && {shlex.join(cmd)}")
        return

    status = app_status(s["id"])
    if status not in (None, "idle") and "--fork-session" not in rest:
        print(f'"{name}" is busy in another window. Waiting until it stops (Ctrl-C cancels)...', file=sys.stderr)
        while status not in (None, "idle"):
            time.sleep(1)
            status = app_status(s["id"])
    if status:
        print(f'Note: "{name}" is still open in another window. Do not type in both places at the same time.',
              file=sys.stderr)
    print(f'Continuing "{name}" in {cwd}', file=sys.stderr)
    os.chdir(cwd)
    os.execvp("claude", cmd)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(130)
