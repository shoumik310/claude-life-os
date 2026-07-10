# claude-life-os

A starter kit for running your personal life on [Claude Code](https://claude.com/claude-code): a script-driven task tracker and an Obsidian-based "second brain," both wired up to a Claude assistant that knows the rules and does the busywork for you.

**Own the folder, rent the engine.** Everything is local plain text — markdown notes, a markdown task file, a Python script. Claude Code is just the tool that reads and writes it. No accounts, no lock-in, nothing to export later.

## What's inside

| | |
|---|---|
| **`todo/`** | A personal task tracker. State lives in one markdown file (`TASKS.md`), all reads/writes go through `tasks.py` (recurring tasks, defer/prepone tracking, effort/energy metadata, a self-rendering HTML dashboard). No database, no server. |
| **`vault/`** | An [Obsidian](https://obsidian.md) vault pre-configured as a personal knowledge base — folders for people, projects, decisions, catchups, daily notes — plus a `vault-cleaner` skill that keeps it tidy. |
| **`CLAUDE.md`** | The setup script. Claude Code reads this automatically and runs a short interview to configure both systems for *you* — your assistant's name, its tone, your task categories, your life areas. Nothing about the original build is hardcoded in; you get your own. |

Take one piece or both — they're independent, and the interview asks which you want.

## Quickstart

```bash
git clone https://github.com/<your-username>/claude-life-os.git
cd claude-life-os
claude
```

Then just say **"go."** Claude Code will interview you — a handful of questions about how you want it to talk to you, what you're tracking, and what to call it — and generate everything else: identity files, folder structure, the assistant's own config, the works. Takes a few minutes.

### Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3 (for `todo/tasks.py` — standard library only, no dependencies to install)
- [Obsidian](https://obsidian.md) (optional — only needed if you want to *browse* the vault as a graph/linked notes app; the markdown files work fine without it)

## Why this exists

Built by pulling apart a working personal setup (task tracker + Obsidian vault, both driven by Claude Code) into the parts that are genuinely generic — the task engine, the Obsidian plugin config, the vault-cleaning skill — versus the parts that are inherently personal — tone, scope, an assistant's name and personality. The generic parts ship as-is. The personal parts get generated fresh, per user, by the interview in `CLAUDE.md`.

If you've watched Dan Martell's ["This AI System Will Make You So Smart It's Almost Unfair"](https://youtu.be/b4d32pBa3UY), the vault half of this is that idea, implemented and made portable.

## After setup

Each subsystem owns its own rules once generated:

- `todo/CLAUDE.md` — scope, tone, and command conventions for the task tracker.
- `vault/CLAUDE.md` — folder map and note conventions for the vault.

Edit those directly any time your preferences change — that's the whole point of owning the folder instead of renting someone else's app.

## License

MIT — see [LICENSE](LICENSE).
