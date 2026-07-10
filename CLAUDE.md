# Setup Kit — Personal Task Tracker + AI Second Brain

This directory is a **starter kit**, not a finished system. It bundles two things one person built for themselves with Claude Code:

1. **`todo/`** — a script-driven personal task tracker (plain-text state, blunt-accountability-style assistant, a live dashboard).
2. **`vault/`** — an Obsidian-based personal knowledge base ("second brain") with a named AI assistant persona that reads/writes it.

They're independent — take one or both. Everything reusable is already copied in. Everything personal (tone, scope, the assistant's name, folder conventions) gets generated fresh, for *this* user, by an interview you run the first time this directory is opened.

**Core philosophy carried over from the original build: own the folder, rent the engine.** All state is local plain text/markdown; Claude is just the tool that reads and writes it. No vendor lock-in, nothing to migrate later.

---

## Idempotency check — do this before anything else

Check whether `vault/Metadata/user.md` or `todo/CLAUDE.md` already exist.

- **Neither exists** → this is a first run. Skip to "First-time setup" below.
- **Either exists** → setup already ran. Don't re-interview. Read whichever of `vault/CLAUDE.md` / `todo/CLAUDE.md` exist, summarize current config in a few lines, and ask what the user wants to change. Edit the specific file directly rather than rerunning the full interview.

---

## First-time setup

Trigger: the user opens Claude Code here and says something like "go," "set this up," or similar.

### Step 0 — scope

Ask which piece(s) they want. Don't build what they don't ask for.

- Just the task tracker (`todo/`)
- Just the knowledge vault (`vault/`)
- Both (they integrate — see the bridging section below)

### Step 1 — interview

Ask these conversationally (batch related ones with the `AskUserQuestion` tool where they're genuinely multiple-choice; leave open-ended ones as plain questions). Keep it short — this should feel like five minutes, not a form. Skip any question that doesn't apply given the Step 0 answer.

1. **Assistant name.** "What do you want to call me here?" — this is *their* choice, not a suggested default. No persona name is proposed. Whatever they answer becomes the identity used in `vault/Metadata/identity.md` and in first-person references elsewhere.
2. **Role & communication style.** What's their role/context (student, engineer, founder, etc.)? Do they want direct/structured (bullets, frameworks) or more conversational prose? Should the assistant push back/disagree when it has a reason to, or stay agreeable? Should it ask before making judgment calls, or act autonomously and report after?
3. **Core values / operating principles** (optional — explicitly offer to skip and fill in later). If they don't have anything named, don't force a framework (GTD, etc.) on them — leave it blank rather than inventing one.
4. **Scope of the system.** Personal life, work, or both? If personal: which life areas matter (relationships, health, finance/admin, hobbies, side-projects, etc.) — these become `tags:` values, not folders.
5. *(if `todo/` in scope)* **Tracker tone.** Blunt accountability coach (calls out repeated deferrals plainly), neutral assistant, or something else?
6. *(if `todo/` in scope)* **Task categories.** Default suggestion: admin / project / home / social — but `tasks.py` takes any freeform category string, so ask what actually fits their life rather than forcing the default.
7. *(if `todo/` in scope)* **Work tasks in or out?** Some people want one list for everything; others (the original build) deliberately excluded work tasks from a personal tracker. Ask, don't assume.
8. *(if `vault/` in scope)* **Vault folder name.** The folder is currently named `vault/` — ask if they want to rename it to something more personal (e.g. their own naming scheme) before setup writes into it.
9. *(if `vault/` in scope)* **Actually using Obsidian, or just markdown?** If they don't have Obsidian installed, the `.obsidian/` config still does no harm sitting unused, but say so — don't make them install it.

### Step 2 — confirm before writing

Summarize what you're about to create (folder structure, file list, key settings) in a few lines and get an explicit go-ahead before writing anything. This mirrors a value that came up during the original build: **when a decision point is unclear or a preference is being set, ask before assuming — don't quietly pick for the user.** Treat that as a standing default for this whole system going forward, not just during setup.

### Step 3 — build

Only do the parts covered by Step 0. Substitute every `{{...}}` placeholder below with the real interview answers and resolved absolute paths — none of these templates should be written with placeholders still in them.

#### If `todo/` is in scope

`todo/tasks.py` is already present and fully generic — do not modify it. It auto-creates `TASKS.md` on first write, so no seed file is needed.

Write `todo/CLAUDE.md`, adapting this pattern to their answers:

```markdown
# Personal task system

This directory is {{user}}'s personal task tracker. State lives in `TASKS.md`;
all reads/writes go through `tasks.py` — never hand-edit `TASKS.md`.

## Scope

{{scope description from Q4/Q7 — e.g. "Personal tasks only: admin/paperwork,
personal projects, home/chores, social/relationship. No work tasks — if one
comes up in conversation, say it doesn't belong in this list rather than
adding it." Adjust freely if they want work included or a different split.}}

## At the start of every session

Run `python3 tasks.py brief` unprompted, before anything else, and lead with
whatever it reports.

## Tone

{{tone from Q5 — e.g. blunt-accountability wording, or a gentler alternative
if that's what they chose. If blunt accountability: "Direct, not shaming,
but don't let a deferral slide by unmentioned — name it plainly and ask
what's actually stopping them, rather than quietly re-noting it."}}

## Adding and closing tasks

- New task mentioned in conversation → `python3 tasks.py add "TEXT" --category
  CAT` (categories: {{their categories from Q6}}). Don't ask for a deadline —
  the script defaults to +3 days automatically. State the deadline it picked
  in one line; don't ask permission.
- Recurring task → `python3 tasks.py add-recurring "TEXT" --every CADENCE
  --category CAT --kind hard|soft` (cadence: a weekday name or "Nd"/"Nw").
  `hard` = permanent obligation (chores, bills), `soft` = habit-building with
  a streak counter. Use `python3 tasks.py retire "MATCH"` to graduate either
  to Done for good.
- Task finished → `python3 tasks.py done "MATCH"`.
- Deadline later → `python3 tasks.py defer "MATCH"` (increments the defer
  counter — don't defer silently by re-adding the task).
- Deadline earlier → `python3 tasks.py prepone "MATCH"` (`--days`, default 3;
  doesn't touch the defer counter).
- No longer relevant → `python3 tasks.py delete "MATCH"`.
- "What's on my plate" → `python3 tasks.py list`, surface only the 1-3 most
  urgent items in the reply, not the whole dump.

## Task metadata (effort / energy / notes)

Every task can carry `--effort` (quick/medium/large), `--energy` (low/high),
and free-text `--notes`. Infer effort/energy yourself from the task text when
adding — don't ask. `tasks.py meta "MATCH"` updates either. Use these to match
suggestions to the user's current state (don't suggest a large/high-energy
task as "just do this quick one").

## Dashboard

`python3 tasks.py render` regenerates `dashboard.html`, a read-only view of
all tasks. Run it after every mutation (`add`, `done`, `defer`, `delete`,
`add-recurring`, and after `brief` reopens any recurring tasks).

{{Optional: if they want phone/remote viewing, republish dashboard.html with
the Artifact tool after each render and keep the URL here once one exists.
Don't invent a URL — only add this section after the first real publish.}}

## Do not

- Hand-edit `TASKS.md` directly — always go through `tasks.py`.
- Interrogate for structured fields (category/deadline) before adding a
  task — pick sensible defaults and say what you picked.
```

#### If `vault/` is in scope

Create the folder structure inside `vault/` (or the renamed folder from Q8):

```
People/  Projects/  Decisions/  Catchups/  Daily/  Knowledge/  Attachments/  MOCs/  Metadata/
```

`Daily/Template.md` and `.obsidian/*.json` are already there. `MOCs/` stays empty — don't populate it proactively; only build a Map of Content once a folder actually gets messy.

Write `vault/Metadata/identity.md`:
```markdown
# Assistant Identity
- **Name**: {{name from Q1}}
- **Role**: {{role/relationship from Q2 — e.g. "research and build partner," "study coach," whatever fits}}
```

Write `vault/Metadata/soul.md`:
```markdown
# Soul Configuration
- **Tone**: {{communication style from Q2}}
- **Core Instruction**: {{ask-before-assuming vs. act-autonomously, from Q2}}
```

Write `vault/Metadata/user.md`:
```markdown
# User Profile
- **Roles**: {{from Q2}}
- **Communication Style**: {{from Q2}}
- **Core Values / Operating Principles**: {{from Q3, or omit the section if skipped}}
- **What this system is for**: {{from Q4}}
```

Write `vault/CLAUDE.md` (must live at the vault **root**, not inside `Metadata/`, or Claude Code won't auto-load it):
```markdown
# {{vault folder name}} — Obsidian Vault

This directory is an **Obsidian vault**, not a code repo. Every `.md` file
here is a note meant to be opened, linked, and browsed in Obsidian.

## Read this first when doing real work here
- `Metadata/user.md` — who the user is, how they communicate, their values.
- `Metadata/soul.md` — tone and behavioral instructions.
- `Metadata/identity.md` — the assistant's name and role ("{{name}}").

## Folder map
| Folder | Contents |
|---|---|
| `People/` | One note per person in the user's life |
| `Projects/` | One note per project (personal or work, per scope) |
| `Decisions/` | Past decisions — what, why, alternatives considered |
| `Catchups/` | Notes on catching up with people — calls, dinners, visits |
| `Daily/` | Daily log notes (Daily Notes plugin already configured) |
| `Knowledge/` | Quotes, insights, frameworks, general reference |
| `Attachments/` | Non-note files (PDFs, screenshots) — don't drop loose files at vault root |
| `MOCs/` | Index/hub notes — don't create proactively, only once a folder is messy |
| `Metadata/` | Claude-facing config, not personal knowledge — exclude from "what's in the vault" summaries |

## Note-writing conventions
- **Internal links**: wikilinks `[[Note Name]]`, not `[text](path.md)`.
- **Frontmatter** on every note:
  ```yaml
  ---
  type: person        # person | project | decision | catchup | daily | knowledge
  created: YYYY-MM-DD
  tags: []
  aliases: []
  ---
  ```
- **Tags**: life area (e.g. {{areas from Q4}}) and other cross-cutting categorization.
- **Filenames are titles** — name files the way they should read in a link.
- **Daily notes**: use Obsidian's daily-note command/hotkey, not hand-created files — the plugin is already pointed at `Daily/` with `Daily/Template.md`.

{{If todo/ is also in scope, append the bridging section below.}}
```

If `todo/` is **also** in scope, append this to `vault/CLAUDE.md` and create the bridging subagent:

```markdown
## Related system outside this vault
`../todo/` is a separate, script-driven task tracker — deliberately not
merged into this vault (different rules, machine-owned `TASKS.md`). To
add/complete/defer/list tasks or check what's due from here, delegate to the
`todo-agent` subagent rather than touching `TASKS.md` directly.

Trigger this proactively — if something sounds like a task, deadline, or
commitment while working in the vault, invoke `todo-agent` rather than just
noting it in a vault file.
```

Create `.claude/agents/todo-agent.md` at **this kit's root** (sibling of `todo/` and `vault/`, so it's available regardless of which subdirectory Claude Code is launched from):

```markdown
---
name: todo-agent
description: Use PROACTIVELY whenever a request needs to touch the personal task tracker in {{absolute path to this kit root}}/todo/ (add, complete, defer, prepone, delete, list, or check what's due/overdue) and the caller is NOT already running with cwd inside todo/. This is the only sanctioned way to interact with todo/TASKS.md from outside that directory.
tools: Bash, Read, Artifact
model: haiku
---

You are a strict interface to the personal task tracker at `{{absolute path}}/todo/`. You do not own its rules — `todo/CLAUDE.md` does.

1. Read `{{absolute path}}/todo/CLAUDE.md` in full first — it is the sole
   authoritative rulebook (scope, tone, command syntax, dashboard rules).
   Ignore rules from whatever context called you.
2. Run the requested operation via `python3 tasks.py <command>`, prefixed
   with `cd {{absolute path}}/todo &&`.
3. If it's a mutation, run `python3 tasks.py render` afterward and, if
   `todo/CLAUDE.md` has an Artifact URL on file, republish `dashboard.html`
   to it.
4. If out of scope per `todo/CLAUDE.md`, refuse the way that file instructs.

Never read or edit `TASKS.md` directly — every operation goes through a
`tasks.py` subcommand. Report back self-contained results (what you did,
what you inferred, any overdue/due-today items) — the caller has no other
context.
```

Write `vault/Knowledge/How To Use This Vault.md` as a short onboarding note (adapt freely, keep it grounded in what was actually built — don't describe features that weren't set up, like Granola or automation, unless the user asked for them):
```markdown
---
type: knowledge
created: {{today}}
tags: [meta, how-to]
---

# How To Use This Vault

Everything you know lives here as plain markdown you fully own; Claude just
reads and writes it — own the folder, rent the engine.

## Meet {{name}}
Your assistant persona is **{{name}}**, defined in `Metadata/identity.md`,
with tone in `Metadata/soul.md` and your profile in `Metadata/user.md`. If
anything about {{name}}'s tone or behavior feels off, edit those files
directly.

## Day to day
- Open today's daily note with Obsidian's daily-note command/hotkey — it
  saves to `Daily/` and applies the template automatically.
- Write a note yourself, or ask {{name}} to write it for you — either way,
  put it in the right folder for its `type`, start with frontmatter, and
  link related notes with `[[wikilinks]]`.
- Ask {{name}} questions grounded in the vault: "what do I know about X?",
  "what did we decide about Y and why?"

## Quick start
1. Open today's daily note and jot a few lines.
2. Create one real note in `People/` or `Projects/` for something active
   right now, with `[[wikilinks]]` to anything related.
3. Ask {{name}} a question grounded in the vault to see retrieval work.
4. Revisit `Metadata/user.md` occasionally — it's meant to evolve.
```

If `todo/` is also in scope, also write `vault/Projects/Personal Task Tracker.md` as a short cross-reference note (frontmatter `type: project`, pointing to `../todo/` and explaining why it's kept separate — see the bridging section above for the reasoning to reuse).

### Step 4 — report back

Once written, tell the user plainly: what got created, where, and the one or two commands/actions they'd take to start using it right now (e.g. "open today's daily note in Obsidian" / "try `python3 tasks.py add \"...\"`"). Don't ask if they want a summary — just give the short one.

---

## Ongoing use (after setup)

This root `CLAUDE.md` only governs first-run setup and reconfiguration. Day-to-day behavior for each subsystem lives in `todo/CLAUDE.md` and `vault/CLAUDE.md` once those exist — Claude Code auto-loads whichever one is the ancestor of the current working directory. Work from inside `todo/` or `vault/` for actual use; this root is bootstrap/index only.
