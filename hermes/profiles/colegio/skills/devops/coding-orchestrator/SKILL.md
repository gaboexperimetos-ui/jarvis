---
name: coding-orchestrator
description: Orchestrate Kilo Code and OpenCode coding sessions as subagents from Hermes.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [coding, kilo, opencode, delegation, orchestration, subagents]
    category: devops
    requires_toolsets: [terminal]
prerequisites:
  commands: [ocshepherd]
---

# Coding Orchestrator

Hermes is the orchestrator. Kilo Code and OpenCode are the coding subagents: they
do the long, token-heavy work (multi-file edits, refactors, test runs) in their own
session, while Hermes keeps the conversation, decides the task, and reports the
outcome.

Two headless servers run as user services on this machine:

| Server | URL | What it is |
|---|---|---|
| OpenCode | `http://127.0.0.1:44001` | `opencode serve`, the OpenCode CLI |
| Kilo Code | `http://127.0.0.1:44002` | `kilo serve`, the Kilo fork of OpenCode |

Both are driven with the `ocshepherd` CLI (`~/.local/bin/ocshepherd`).

## When to use this instead of doing the work yourself

Delegate when the task is **big, mechanical, or needs many tool calls**: a refactor
across many files, writing tests for an existing module, a dependency upgrade,
a bug hunt that needs dozens of greps, a scaffold.

Do it yourself when the task is **small or needs the conversation**: one-line
answer, one-file edit you can do in two calls, anything needing back-and-forth
with the user mid-way.

## Procedure

### 1. Pick the server

Default to Kilo (`44002`) for code work; use OpenCode (`44001`) when the task
needs its own configuration or you want a second opinion on the same task.

### 2. Create the session with the task inline

```bash
ocshepherd new --url http://127.0.0.1:44002 \
  --dir /ruta/al/proyecto \
  --title "refactor auth" \
  --prompt "Tarea completa y autocontenida: qué cambiar, en qué archivos, y cómo verificar que funciona."
```

`--dir` is the working directory of the subagent: always name the project
explicitly, never leave it to the default. `--prompt` carries the whole task, so
the subagent needs no further input.

Write the prompt like a ticket: goal, constraints, files in play, and the command
that proves it works. A vague prompt returns vague work.

The command prints the new session id (`ses_...`). Keep it: everything below
refers to that session.

### 3. Watch it, do not block

```bash
ocshepherd tail   --url http://127.0.0.1:44002 <ses_id>   # last messages
ocshepherd forms  --url http://127.0.0.1:44002 <ses_id>   # questions waiting
ocshepherd perms  --url http://127.0.0.1:44002 <ses_id>   # permissions waiting
```

A subagent may stop and wait: a permission request, or a question it cannot
answer alone. Then:

```bash
ocshepherd perm       --url http://127.0.0.1:44002 <ses_id> --allow
ocshepherd form-reply --url http://127.0.0.1:44002 <ses_id> --reply "respuesta"
ocshepherd send       --url http://127.0.0.1:44002 <ses_id> "aclaración"
```

Approve a permission only when the action is one the user already authorized for
this task. A request outside that scope goes back to the user.

### 4. Report the result

When the session goes quiet, read the tail and report: what changed, what was
verified, what is left. Verify before claiming — read the diff or run the test
command yourself rather than trusting the subagent's summary:

```bash
cd /ruta/al/proyecto && git diff --stat
```

## Background watching

`ocshepherd watch --loop 60` runs as a user service for each server
(`ocshepherd.service` for OpenCode, `ocshepherd-kilo.service` for Kilo) and sends
Telegram alerts when any session stops, asks a question or requests a permission.
The user can answer from the phone; Hermes is not required in that loop.

## Sessions to inspect

```bash
ocshepherd list --url http://127.0.0.1:44002    # recent sessions
ocshepherd tail --url http://127.0.0.1:44002 <ses_id>
ocshepherd abort --url http://127.0.0.1:44002 <ses_id>   # interrupt
ocshepherd close --url http://127.0.0.1:44002 <ses_id> --yes   # delete
```

## Rules

- One task per session. Reusing a session for an unrelated task drags its whole
  history along and degrades the work.
- Never leave `--dir` at its default for a code task: a subagent editing the wrong
  tree is worse than no subagent.
- `abort` a session that is going in circles instead of letting it burn tokens.
- The servers listen on localhost with no password. Do not expose them without
  setting a password first.