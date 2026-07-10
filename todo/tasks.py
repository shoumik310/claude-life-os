#!/usr/bin/env python3
import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

TASKS_FILE = Path(__file__).parent / "TASKS.md"

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DEFAULT_DEADLINE_DAYS = 3
DEFAULT_DEFER_DAYS = 3
DEFAULT_CATEGORY = "misc"

DELIMITER = " — "
EFFORT_LEVELS = ("quick", "medium", "large")
ENERGY_LEVELS = ("low", "high")


def today():
    return date.today().isoformat()


def add_days(iso, n):
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def check_field(value, label):
    if DELIMITER in value:
        print(f"{label} can't contain '{DELIMITER.strip()}' (breaks the file format). Rephrase without it.")
        sys.exit(1)
    return value


def parse_date(value, label):
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        print(f"{label} must be a YYYY-MM-DD date, got '{value}'.")
        sys.exit(1)


def check_enum(value, allowed, label):
    if value is None:
        return None
    v = value.strip().lower()
    if v not in allowed:
        print(f"{label} must be one of {', '.join(allowed)}, got '{value}'.")
        sys.exit(1)
    return v


def parse_cadence_days(cadence):
    c = cadence.strip().lower()
    if c in WEEKDAYS:
        return 7
    if c in ("weekly",):
        return 7
    if c in ("biweekly", "fortnightly"):
        return 14
    if c in ("monthly",):
        return 30
    m = re.fullmatch(r"(\d+)\s*d(ays?)?", c)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"(\d+)\s*w(eeks?)?", c)
    if m:
        return int(m.group(1)) * 7
    raise ValueError(
        f"Can't parse cadence '{cadence}'. Use a weekday name (e.g. 'Sunday'), "
        f"'weekly', 'biweekly', 'monthly', or an interval like '10d' / '2w'."
    )


RECURRING_KINDS = ("hard", "soft")


class Task:
    __slots__ = ("text", "due", "category", "deferred", "recurring_cadence", "effort", "energy", "notes",
                 "recurring_kind", "recurring_streak", "recurring_last_done")

    def __init__(self, text, due, category, deferred=0, recurring_cadence=None,
                 effort=None, energy=None, notes=None,
                 recurring_kind=None, recurring_streak=0, recurring_last_done=None):
        self.text = text
        self.due = due
        self.category = category
        self.deferred = deferred
        self.recurring_cadence = recurring_cadence
        self.effort = effort
        self.energy = energy
        self.notes = notes
        # Carried over from the Recurring definition when a due cycle is
        # reopened into Open (see cmd_brief) — needed so cmd_done can
        # rebuild the Recurring entry with the right kind/streak.
        self.recurring_kind = recurring_kind
        self.recurring_streak = recurring_streak
        self.recurring_last_done = recurring_last_done

    def to_line(self):
        line = f"- [ ] {self.text} — due {self.due} — {self.category}"
        if self.deferred:
            line += f" — deferred {self.deferred}x"
        if self.recurring_cadence:
            ld = self.recurring_last_done or "never"
            kind = self.recurring_kind or "hard"
            line += f" — recurring:{self.recurring_cadence}|{kind}|{self.recurring_streak or 0}|{ld}"
        if self.effort:
            line += f" — effort:{self.effort}"
        if self.energy:
            line += f" — energy:{self.energy}"
        if self.notes:
            line += f" — notes:{self.notes}"
        return line


class Recurring:
    __slots__ = ("text", "cadence", "category", "last_done", "kind", "streak", "effort", "energy", "notes")

    def __init__(self, text, cadence, category, last_done=None, kind="hard", streak=0,
                 effort=None, energy=None, notes=None):
        self.text = text
        self.cadence = cadence
        self.category = category
        self.last_done = last_done
        self.kind = kind
        self.streak = streak
        self.effort = effort
        self.energy = energy
        self.notes = notes

    def to_line(self):
        ld = self.last_done if self.last_done else "never"
        line = f"- [ ] {self.text} — every {self.cadence} — {self.category} — last done {ld}"
        if self.kind == "soft":
            line += f" — kind:soft — streak:{self.streak}"
        if self.effort:
            line += f" — effort:{self.effort}"
        if self.energy:
            line += f" — energy:{self.energy}"
        if self.notes:
            line += f" — notes:{self.notes}"
        return line

    def is_due(self, on=None):
        on = on or today()
        if self.last_done is None:
            return True
        c = self.cadence.strip().lower()
        try:
            if c in WEEKDAYS:
                target_idx = WEEKDAYS.index(c)
                d = date.fromisoformat(on)
                offset = (d.weekday() - target_idx) % 7
                last_occurrence = (d - timedelta(days=offset)).isoformat()
                return self.last_done < last_occurrence
            days = parse_cadence_days(self.cadence)
        except ValueError:
            print(f"WARNING: recurring task '{self.text}' has an unparseable cadence "
                  f"'{self.cadence}' — it will never come due until fixed.", file=sys.stderr)
            return False
        next_due = add_days(self.last_done, days)
        return on >= next_due


class Done:
    __slots__ = ("text", "done_date", "category")

    def __init__(self, text, done_date, category):
        self.text = text
        self.done_date = done_date
        self.category = category

    def to_line(self):
        return f"- [x] {self.text} — done {self.done_date} — {self.category}"


def load():
    open_tasks, recurring_tasks, done_tasks = [], [], []
    if not TASKS_FILE.exists():
        return open_tasks, recurring_tasks, done_tasks

    section = None
    for raw in TASKS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## Open"):
            section = "open"
            continue
        if line.startswith("## Recurring"):
            section = "recurring"
            continue
        if line.startswith("## Done"):
            section = "done"
            continue
        if not line.strip().startswith("- ["):
            continue

        checked = line.strip().startswith("- [x]")
        content = line.strip()[6:].strip()
        parts = [p.strip() for p in content.split(" — ")]

        if section == "open":
            text = parts[0]
            due = parts[1].split(" ", 1)[1] if len(parts) > 1 else today()
            category = parts[2] if len(parts) > 2 else DEFAULT_CATEGORY
            deferred = 0
            cadence = None
            rkind = None
            rstreak = 0
            rlast = None
            effort = None
            energy = None
            notes = None
            for p in parts[3:]:
                if p.startswith("deferred"):
                    m = re.search(r"\d+", p)
                    deferred = int(m.group()) if m else 0
                elif p.startswith("recurring:"):
                    payload = p.split(":", 1)[1]
                    bits = payload.split("|")
                    cadence = bits[0]
                    rkind = bits[1] if len(bits) > 1 else "hard"
                    rstreak = int(bits[2]) if len(bits) > 2 and bits[2].isdigit() else 0
                    rlast = bits[3] if len(bits) > 3 and bits[3] != "never" else None
                elif p.startswith("effort:"):
                    effort = p.split(":", 1)[1]
                elif p.startswith("energy:"):
                    energy = p.split(":", 1)[1]
                elif p.startswith("notes:"):
                    notes = p.split(":", 1)[1]
            open_tasks.append(Task(text, due, category, deferred, cadence, effort, energy, notes,
                                    rkind, rstreak, rlast))
        elif section == "recurring":
            text = parts[0]
            cadence = parts[1].split(" ", 1)[1] if len(parts) > 1 else ""
            category = parts[2] if len(parts) > 2 else DEFAULT_CATEGORY
            last_done = None
            if len(parts) > 3 and parts[3].startswith("last done"):
                val = parts[3].split(" ", 2)[2]
                last_done = None if val == "never" else val
            kind = "hard"
            streak = 0
            r_effort = None
            r_energy = None
            r_notes = None
            for p in parts[4:]:
                if p.startswith("kind:"):
                    kind = p.split(":", 1)[1]
                elif p.startswith("streak:"):
                    m = re.search(r"\d+", p)
                    streak = int(m.group()) if m else 0
                elif p.startswith("effort:"):
                    r_effort = p.split(":", 1)[1]
                elif p.startswith("energy:"):
                    r_energy = p.split(":", 1)[1]
                elif p.startswith("notes:"):
                    r_notes = p.split(":", 1)[1]
            recurring_tasks.append(Recurring(text, cadence, category, last_done, kind, streak,
                                              r_effort, r_energy, r_notes))
        elif section == "done":
            text = parts[0]
            done_date = parts[1].split(" ", 1)[1] if len(parts) > 1 else today()
            category = parts[2] if len(parts) > 2 else DEFAULT_CATEGORY
            done_tasks.append(Done(text, done_date, category))

    return open_tasks, recurring_tasks, done_tasks


def save(open_tasks, recurring_tasks, done_tasks):
    open_tasks = sorted(open_tasks, key=lambda t: t.due)
    lines = ["# Tasks", "", "## Open"]
    for t in open_tasks:
        lines.append(t.to_line())
    lines += ["", "## Recurring"]
    for r in recurring_tasks:
        lines.append(r.to_line())
    lines += ["", "## Done"]
    for d in done_tasks:
        lines.append(d.to_line())
    lines.append("")
    TASKS_FILE.write_text("\n".join(lines), encoding="utf-8")


def find_matches(items, query):
    q = query.strip().lower()
    if not q:
        return []
    return [i for i in items if q in i.text.lower()]


def resolve_single(items, query, kind):
    matches = find_matches(items, query)
    if not matches:
        print(f"No {kind} task matches '{query}'.")
        sys.exit(1)
    if len(matches) > 1:
        print(f"Multiple {kind} tasks match '{query}':")
        for m in matches:
            print(f"  - {m.text}")
        print("Be more specific.")
        sys.exit(1)
    return matches[0]


def cmd_add(args):
    open_tasks, recurring_tasks, done_tasks = load()
    text = check_field(args.text, "Task text")
    category = check_field(args.category or DEFAULT_CATEGORY, "Category")
    due = parse_date(args.deadline, "Deadline") if args.deadline else add_days(today(), DEFAULT_DEADLINE_DAYS)
    effort = check_enum(args.effort, EFFORT_LEVELS, "Effort")
    energy = check_enum(args.energy, ENERGY_LEVELS, "Energy")
    notes = check_field(args.notes, "Notes") if args.notes else None
    open_tasks.append(Task(text, due, category, effort=effort, energy=energy, notes=notes))
    save(open_tasks, recurring_tasks, done_tasks)
    meta_note = ""
    if effort or energy:
        meta_note = f" ({', '.join(x for x in (effort, energy) if x)})"
    print(f"Added: {text} — due {due} — {category}{meta_note}")


def cmd_meta(args):
    open_tasks, recurring_tasks, done_tasks = load()

    if find_matches(open_tasks, args.match):
        t = resolve_single(open_tasks, args.match, "open")
    elif find_matches(recurring_tasks, args.match):
        t = resolve_single(recurring_tasks, args.match, "recurring")
    else:
        print(f"No open or recurring task matches '{args.match}'.")
        sys.exit(1)

    changed = []
    if args.effort:
        t.effort = check_enum(args.effort, EFFORT_LEVELS, "Effort")
        changed.append(f"effort={t.effort}")
    if args.energy:
        t.energy = check_enum(args.energy, ENERGY_LEVELS, "Energy")
        changed.append(f"energy={t.energy}")
    if args.set_notes is not None:
        t.notes = check_field(args.set_notes, "Notes") if args.set_notes else None
        changed.append("notes replaced")
    elif args.notes:
        addition = check_field(args.notes, "Notes")
        t.notes = f"{t.notes}; {addition}" if t.notes else addition
        changed.append("notes appended")
    if args.due:
        if not hasattr(t, "due"):
            print("--due only applies to open tasks (recurring tasks track 'last done', not a due date).")
            sys.exit(1)
        t.due = parse_date(args.due, "Due date")
        changed.append(f"due={t.due}")

    if not changed:
        print("Nothing to update — pass --effort, --energy, --notes, --set-notes, or --due.")
        sys.exit(1)

    save(open_tasks, recurring_tasks, done_tasks)
    print(f"Updated: {t.text} — {', '.join(changed)}")


def cmd_add_recurring(args):
    open_tasks, recurring_tasks, done_tasks = load()
    text = check_field(args.text, "Task text")
    category = check_field(args.category or DEFAULT_CATEGORY, "Category")
    try:
        parse_cadence_days(args.every)
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    kind = check_enum(args.kind, RECURRING_KINDS, "Kind") or "hard"
    effort = check_enum(args.effort, EFFORT_LEVELS, "Effort")
    energy = check_enum(args.energy, ENERGY_LEVELS, "Energy")
    notes = check_field(args.notes, "Notes") if args.notes else None
    recurring_tasks.append(Recurring(text, args.every, category, kind=kind,
                                      effort=effort, energy=energy, notes=notes))
    save(open_tasks, recurring_tasks, done_tasks)
    meta_note = f" ({', '.join(x for x in (effort, energy) if x)})" if (effort or energy) else ""
    print(f"Added recurring ({kind}): {text} — every {args.every} — {category}{meta_note}")


def _next_streak(prev_streak, prev_last_done, cadence, on):
    """Streak continues if completed within ~1.5 cadence periods of the
    last completion; a longer gap means a cycle was missed, so it resets."""
    if prev_last_done is None:
        return 1
    try:
        cadence_days = parse_cadence_days(cadence)
    except ValueError:
        cadence_days = 7
    gap = (date.fromisoformat(on) - date.fromisoformat(prev_last_done)).days
    return prev_streak + 1 if gap <= cadence_days * 1.5 else 1


def cmd_done(args):
    open_tasks, recurring_tasks, done_tasks = load()

    open_matches = find_matches(open_tasks, args.match)
    if open_matches:
        if len(open_matches) > 1:
            print(f"Multiple open tasks match '{args.match}':")
            for m in open_matches:
                print(f"  - {m.text}")
            print("Be more specific.")
            sys.exit(1)
        t = open_matches[0]
        open_tasks.remove(t)
        if t.recurring_cadence:
            kind = t.recurring_kind or "hard"
            t_today = today()
            streak = _next_streak(t.recurring_streak, t.recurring_last_done, t.recurring_cadence, t_today) \
                if kind == "soft" else 0
            recurring_tasks.append(Recurring(t.text, t.recurring_cadence, t.category, t_today, kind, streak,
                                              t.effort, t.energy, t.notes))
            save(open_tasks, recurring_tasks, done_tasks)
            streak_note = f", streak {streak}" if kind == "soft" else ""
            print(f"Done: {t.text} (recurring — every {t.recurring_cadence}, back on schedule{streak_note})")
        else:
            done_tasks.append(Done(t.text, today(), t.category))
            save(open_tasks, recurring_tasks, done_tasks)
            print(f"Done: {t.text}")
        return

    rec_matches = find_matches(recurring_tasks, args.match)
    if rec_matches:
        r = resolve_single(recurring_tasks, args.match, "recurring")
        t_today = today()
        if r.kind == "soft":
            r.streak = _next_streak(r.streak, r.last_done, r.cadence, t_today)
        r.last_done = t_today
        save(open_tasks, recurring_tasks, done_tasks)
        streak_note = f", streak {r.streak}" if r.kind == "soft" else ""
        print(f"Done: {r.text} (recurring — every {r.cadence}, last done today{streak_note})")
        return

    print(f"No open or recurring task matches '{args.match}'.")
    sys.exit(1)


def cmd_retire(args):
    """Permanently ends a recurring task (hard or soft) — moves it to Done
    for good, no more reopening. This is the 'you just say so' off-ramp for
    soft/habit tasks, but works on hard ones too if they're no longer needed."""
    open_tasks, recurring_tasks, done_tasks = load()

    rec_matches = find_matches(recurring_tasks, args.match)
    if rec_matches:
        r = resolve_single(recurring_tasks, args.match, "recurring")
        recurring_tasks.remove(r)
        done_tasks.append(Done(r.text, today(), r.category))
        save(open_tasks, recurring_tasks, done_tasks)
        streak_note = f" — {r.streak}-cycle streak when retired" if r.kind == "soft" and r.streak else ""
        print(f"Retired: {r.text}{streak_note}")
        return

    open_matches = [t for t in find_matches(open_tasks, args.match) if t.recurring_cadence]
    if open_matches:
        t = resolve_single(open_matches, args.match, "recurring")
        open_tasks.remove(t)
        done_tasks.append(Done(t.text, today(), t.category))
        save(open_tasks, recurring_tasks, done_tasks)
        streak_note = f" — {t.recurring_streak}-cycle streak when retired" \
            if t.recurring_kind == "soft" and t.recurring_streak else ""
        print(f"Retired: {t.text}{streak_note}")
        return

    print(f"No recurring task matches '{args.match}'.")
    sys.exit(1)


def cmd_defer(args):
    open_tasks, recurring_tasks, done_tasks = load()
    t = resolve_single(open_tasks, args.match, "open")
    days = DEFAULT_DEFER_DAYS if args.days is None else args.days
    if days <= 0:
        print("--days must be a positive number.")
        sys.exit(1)
    t.due = add_days(t.due, days)
    t.deferred += 1
    save(open_tasks, recurring_tasks, done_tasks)
    print(f"Deferred: {t.text} — new due {t.due} — deferred {t.deferred}x")


def cmd_prepone(args):
    open_tasks, recurring_tasks, done_tasks = load()
    t = resolve_single(open_tasks, args.match, "open")
    days = DEFAULT_DEFER_DAYS if args.days is None else args.days
    if days <= 0:
        print("--days must be a positive number.")
        sys.exit(1)
    t.due = add_days(t.due, -days)
    save(open_tasks, recurring_tasks, done_tasks)
    print(f"Preponed: {t.text} — new due {t.due}")


def cmd_delete(args):
    open_tasks, recurring_tasks, done_tasks = load()
    for items, label in ((open_tasks, "open"), (recurring_tasks, "recurring"), (done_tasks, "done")):
        matches = find_matches(items, args.match)
        if matches:
            t = resolve_single(items, args.match, label)
            items.remove(t)
            save(open_tasks, recurring_tasks, done_tasks)
            print(f"Deleted ({label}): {t.text}")
            return
    print(f"No task matches '{args.match}'.")
    sys.exit(1)


def _meta_suffix(t):
    tags = []
    if t.effort:
        tags.append(t.effort)
    if t.energy:
        tags.append(f"{t.energy} energy")
    meta = f" [{', '.join(tags)}]" if tags else ""
    notes = f" — notes: {t.notes}" if t.notes else ""
    return meta + notes


def cmd_list(args):
    open_tasks, recurring_tasks, done_tasks = load()
    if not open_tasks:
        print("Nothing open.")
        return
    t_today = today()
    for t in sorted(open_tasks, key=lambda t: t.due):
        tag = ""
        if t.due < t_today:
            tag = " [OVERDUE]"
        elif t.due == t_today:
            tag = " [DUE TODAY]"
        defer_note = f" (deferred {t.deferred}x)" if t.deferred else ""
        if t.recurring_cadence:
            rec_note = f" (recurring, streak {t.recurring_streak})" if t.recurring_kind == "soft" else " (recurring)"
        else:
            rec_note = ""
        print(f"- {t.text} — due {t.due} — {t.category}{tag}{defer_note}{rec_note}{_meta_suffix(t)}")


def cmd_brief(args):
    open_tasks, recurring_tasks, done_tasks = load()
    t_today = today()

    reopened = []
    still_recurring = []
    for r in recurring_tasks:
        if r.is_due(t_today):
            open_tasks.append(Task(r.text, t_today, r.category, deferred=0, recurring_cadence=r.cadence,
                                    effort=r.effort, energy=r.energy, notes=r.notes,
                                    recurring_kind=r.kind, recurring_streak=r.streak,
                                    recurring_last_done=r.last_done))
            reopened.append(r)
        else:
            still_recurring.append(r)
    recurring_tasks = still_recurring

    if reopened:
        save(open_tasks, recurring_tasks, done_tasks)

    reopened_texts = {r.text for r in reopened}
    overdue = [t for t in open_tasks if t.due < t_today]
    due_today = [t for t in open_tasks if t.due == t_today and t.text not in reopened_texts]

    if not overdue and not due_today and not reopened:
        print("Nothing overdue or due today.")
        return

    if overdue:
        print("OVERDUE:")
        for t in sorted(overdue, key=lambda t: t.due):
            defer_note = f" (deferred {t.deferred}x)" if t.deferred else ""
            days_late = (date.fromisoformat(t_today) - date.fromisoformat(t.due)).days
            print(f"  - {t.text} — {days_late}d overdue — {t.category}{defer_note}{_meta_suffix(t)}")
    if due_today:
        print("DUE TODAY:")
        for t in due_today:
            print(f"  - {t.text} — {t.category}{_meta_suffix(t)}")
    if reopened:
        print("RECURRING, BACK ON SCHEDULE:")
        for r in reopened:
            streak_note = f" — streak {r.streak}" if r.kind == "soft" else ""
            print(f"  - {r.text} — every {r.cadence} — {r.category}{streak_note}")


DASHBOARD_FILE = Path(__file__).parent / "dashboard.html"

# Fixed categorical order (light, dark). Kept as a prefix of the validated
# 8-slot categorical palette so adjacent-pair CVD separation still holds.
CATEGORY_COLORS = {
    "admin":   ("#2a78d6", "#3987e5"),  # slot 1, blue
    "home":    ("#1baf7a", "#199e70"),  # slot 2, aqua
    "project": ("#eda100", "#c98500"),  # slot 3, yellow
    "social":  ("#008300", "#008300"),  # slot 4, green
}
FALLBACK_CATEGORY_COLOR = ("#4a3aa7", "#9085e9")  # slot 5, violet — any other category

STATUS_COLOR = {
    "overdue": "#d03b3b",
    "due_today": "#fab219",
}


def _html_escape(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _category_colors(category):
    return CATEGORY_COLORS.get(category.lower(), FALLBACK_CATEGORY_COLOR)


def _category_css():
    """Returns (light_rules, dark_rules) as standalone top-level CSS rule
    strings — these must NOT be nested inside :root{}, since a class
    selector can't appear inside another rule's declaration block."""
    rules = [f'.cat-{cat} {{ --cat-color: {light}; }}' for cat, (light, dark) in CATEGORY_COLORS.items()]
    rules.append(f'.cat-other {{ --cat-color: {FALLBACK_CATEGORY_COLOR[0]}; }}')
    dark_rules = [f'.cat-{cat} {{ --cat-color: {dark}; }}' for cat, (light, dark) in CATEGORY_COLORS.items()]
    dark_rules.append(f'.cat-other {{ --cat-color: {FALLBACK_CATEGORY_COLOR[1]}; }}')
    return "\n  ".join(rules), "\n    ".join(dark_rules)


def _task_row_html(t, t_today, status):
    text = _html_escape(t.text)
    cat_slug = t.category.lower() if t.category.lower() in CATEGORY_COLORS else "other"
    cat_label = _html_escape(t.category)
    defer_badge = f'<span class="defer-badge">deferred {t.deferred}x</span>' if t.deferred else ""
    if t.recurring_cadence and t.recurring_kind == "soft":
        rec_badge = f'<span class="rec-badge">streak {t.recurring_streak}</span>'
    elif t.recurring_cadence:
        rec_badge = '<span class="rec-badge">recurring</span>'
    else:
        rec_badge = ""
    effort_badge = f'<span class="meta-badge">{_html_escape(t.effort)}</span>' if t.effort else ""
    energy_badge = f'<span class="meta-badge">{_html_escape(t.energy)} energy</span>' if t.energy else ""

    if status == "overdue":
        days_late = (date.fromisoformat(t_today) - date.fromisoformat(t.due)).days
        due_text = f"was due {t.due} · {days_late}d overdue"
    elif status == "due_today":
        due_text = "due today"
    else:
        days_left = (date.fromisoformat(t.due) - date.fromisoformat(t_today)).days
        due_text = f"due {t.due} · in {days_left}d"

    dot = f'<span class="status-dot status-{status}" aria-hidden="true"></span>' if status in ("overdue", "due_today") else '<span class="status-dot status-upcoming" aria-hidden="true"></span>'

    notes_html = f'\n        <div class="task-notes">{_html_escape(t.notes)}</div>' if t.notes else ""

    return f'''      <div class="task-row-wrap">
      <div class="task-row">
        {dot}
        <span class="task-text">{text}</span>
        <span class="cat-tag cat-{cat_slug}">{cat_label}</span>
        <span class="due-text">{due_text}</span>
        {effort_badge}{energy_badge}{defer_badge}{rec_badge}
      </div>{notes_html}
      </div>'''


def cmd_render(args):
    open_tasks, recurring_tasks, done_tasks = load()
    t_today = today()

    overdue = sorted([t for t in open_tasks if t.due < t_today], key=lambda t: t.due)
    due_today = sorted([t for t in open_tasks if t.due == t_today], key=lambda t: t.text)
    upcoming = sorted([t for t in open_tasks if t.due > t_today], key=lambda t: t.due)

    sections = []
    if overdue:
        sections.append(("OVERDUE", overdue, "overdue"))
    if due_today:
        sections.append(("DUE TODAY", due_today, "due_today"))
    if upcoming:
        sections.append(("UPCOMING", upcoming, "upcoming"))

    section_html = []
    for title, tasks, status in sections:
        rows = "\n".join(_task_row_html(t, t_today, status) for t in tasks)
        section_html.append(f'''    <section class="task-section">
      <h2 class="section-title section-{status}">{title} <span class="count">{len(tasks)}</span></h2>
{rows}
    </section>''')

    if not sections:
        section_html.append('    <p class="empty">Nothing open. Clean slate.</p>')

    recurring_html = ""
    if recurring_tasks:
        rows = []
        for r in sorted(recurring_tasks, key=lambda r: r.text.lower()):
            cat_slug = r.category.lower() if r.category.lower() in CATEGORY_COLORS else "other"
            last = f"last done {r.last_done}" if r.last_done else "never done yet"
            kind_badge = f'<span class="meta-badge">streak {r.streak}</span>' if r.kind == "soft" \
                else '<span class="meta-badge">hard</span>'
            effort_badge = f'<span class="meta-badge">{_html_escape(r.effort)}</span>' if r.effort else ""
            energy_badge = f'<span class="meta-badge">{_html_escape(r.energy)} energy</span>' if r.energy else ""
            notes_html = f'\n        <div class="task-notes">{_html_escape(r.notes)}</div>' if r.notes else ""
            rows.append(f'''      <div class="task-row-wrap">
      <div class="task-row">
        <span class="status-dot status-recurring" aria-hidden="true"></span>
        <span class="task-text">{_html_escape(r.text)}</span>
        <span class="cat-tag cat-{cat_slug}">{_html_escape(r.category)}</span>
        <span class="due-text">every {_html_escape(r.cadence)} · {last}</span>
        {effort_badge}{energy_badge}{kind_badge}
      </div>{notes_html}
      </div>''')
        recurring_html = f'''    <section class="task-section">
      <h2 class="section-title">RECURRING <span class="count">{len(recurring_tasks)}</span></h2>
{chr(10).join(rows)}
    </section>'''

    done_html = ""
    recent_done = list(reversed(done_tasks))[:8]
    if recent_done:
        rows = []
        for d in recent_done:
            cat_slug = d.category.lower() if d.category.lower() in CATEGORY_COLORS else "other"
            rows.append(f'''      <div class="task-row done-row">
        <span class="status-dot status-done" aria-hidden="true"></span>
        <span class="task-text">{_html_escape(d.text)}</span>
        <span class="cat-tag cat-{cat_slug}">{_html_escape(d.category)}</span>
        <span class="due-text">done {d.done_date}</span>
      </div>''')
        done_html = f'''    <section class="task-section muted-section">
      <h2 class="section-title">RECENTLY DONE</h2>
{chr(10).join(rows)}
    </section>'''

    cat_css_light, cat_css_dark = _category_css()

    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="60">
<title>Tasks</title>
<style>
  :root {{
    --surface-page: #f9f9f7;
    --surface-card: #fcfcfb;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --border: rgba(11,11,11,0.10);
    --gridline: #e1e0d9;
    --status-overdue: {STATUS_COLOR['overdue']};
    --status-due-today: {STATUS_COLOR['due_today']};
    --status-upcoming: #898781;
    --status-recurring: #4a3aa7;
    --status-done: #0ca30c;
  }}
  {cat_css_light}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface-page: #0d0d0d;
      --surface-card: #1a1a19;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted: #898781;
      --border: rgba(255,255,255,0.10);
      --gridline: #2c2c2a;
    }}
    {cat_css_dark}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--surface-page);
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 32px 16px 60px;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  h1 {{ font-size: 20px; margin: 0 0 4px 0; }}
  .subtitle {{ color: var(--text-secondary); font-size: 14px; margin: 0 0 28px 0; }}
  .task-section {{
    background: var(--surface-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 16px;
  }}
  .muted-section {{ opacity: 0.7; }}
  .section-title {{
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-secondary);
    margin: 0 0 12px 0;
    font-weight: 700;
  }}
  .section-overdue {{ color: var(--status-overdue); }}
  .section-due_today {{ color: #a06e00; }}
  .count {{
    color: var(--text-muted);
    font-weight: 400;
    text-transform: none;
    letter-spacing: normal;
  }}
  .task-row-wrap:last-child .task-row {{ border-bottom: none; }}
  .task-row {{
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid var(--gridline);
    flex-wrap: wrap;
  }}
  .task-row:last-child {{ border-bottom: none; }}
  .task-notes {{
    font-size: 12px;
    font-style: italic;
    color: var(--text-secondary);
    padding: 0 0 8px 18px;
  }}
  .meta-badge {{
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
    border: 1px solid var(--gridline);
    border-radius: 999px;
    padding: 1px 7px;
  }}
  .status-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    flex-shrink: 0;
    align-self: center;
  }}
  .status-overdue {{ background: var(--status-overdue); }}
  .status-due_today {{ background: var(--status-due-today); }}
  .status-upcoming {{ background: var(--status-upcoming); opacity: 0.5; }}
  .status-recurring {{ background: var(--status-recurring); }}
  .status-done {{ background: var(--status-done); }}
  .task-text {{
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    flex: 1 1 auto;
    min-width: 160px;
  }}
  .done-row .task-text {{ font-weight: 400; text-decoration: line-through; color: var(--text-secondary); }}
  .cat-tag {{
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 999px;
    color: var(--cat-color);
    border: 1px solid var(--cat-color);
    white-space: nowrap;
  }}
  .due-text {{ font-size: 13px; color: var(--text-muted); white-space: nowrap; }}
  .defer-badge {{
    font-size: 11px; font-weight: 700; color: var(--status-overdue);
    white-space: nowrap;
  }}
  .rec-badge {{ font-size: 11px; color: var(--status-recurring); white-space: nowrap; }}
  .empty {{ color: var(--text-secondary); font-size: 15px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Tasks</h1>
  <p class="subtitle">{t_today} · view-only, regenerated automatically · refreshes every 60s</p>
{chr(10).join(section_html)}
{recurring_html}
{done_html}
</div>
</body>
</html>
'''
    DASHBOARD_FILE.write_text(html, encoding="utf-8")
    print(f"Rendered {DASHBOARD_FILE}")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Personal task tracker backed by TASKS.md")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("text")
    p.add_argument("--category")
    p.add_argument("--deadline", help="YYYY-MM-DD, defaults to +3 days")
    p.add_argument("--effort", choices=EFFORT_LEVELS, help="quick / medium / large")
    p.add_argument("--energy", choices=ENERGY_LEVELS, help="low / high focus required")
    p.add_argument("--notes", help="free-text context")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("add-recurring")
    p.add_argument("text")
    p.add_argument("--every", required=True)
    p.add_argument("--category")
    p.add_argument("--kind", choices=RECURRING_KINDS, default="hard",
                    help="hard = permanent obligation, always reopens. soft = habit-building, "
                         "tracks a streak, ends only when explicitly retired.")
    p.add_argument("--effort", choices=EFFORT_LEVELS, help="quick / medium / large")
    p.add_argument("--energy", choices=ENERGY_LEVELS, help="low / high focus required")
    p.add_argument("--notes", help="free-text context")
    p.set_defaults(func=cmd_add_recurring)

    p = sub.add_parser("done")
    p.add_argument("match")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("defer")
    p.add_argument("match")
    p.add_argument("--days", type=int)
    p.set_defaults(func=cmd_defer)

    p = sub.add_parser("prepone", help="pull an open task's due date earlier")
    p.add_argument("match")
    p.add_argument("--days", type=int)
    p.set_defaults(func=cmd_prepone)

    p = sub.add_parser("meta", help="update effort/energy/notes on an existing open task")
    p.add_argument("match")
    p.add_argument("--effort", choices=EFFORT_LEVELS)
    p.add_argument("--energy", choices=ENERGY_LEVELS)
    p.add_argument("--notes", help="append to existing notes")
    p.add_argument("--set-notes", dest="set_notes", help="replace notes entirely (pass '' to clear)")
    p.set_defaults(func=cmd_meta)

    p = sub.add_parser("delete")
    p.add_argument("match")
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("retire", help="permanently end a recurring task (hard or soft) — moves it to Done for good")
    p.add_argument("match")
    p.set_defaults(func=cmd_retire)

    p = sub.add_parser("list")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("brief")
    p.set_defaults(func=cmd_brief)

    p = sub.add_parser("render")
    p.set_defaults(func=cmd_render)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
