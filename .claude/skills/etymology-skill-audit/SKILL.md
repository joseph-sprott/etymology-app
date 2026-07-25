---
name: etymology-skill-audit
description: This skill should be used when a new skill is added to this project, or when the user asks to "audit the skills", "review the skills for visibility/composability", or "check if this skill should be auto-invocable" -- applies the three-dimension checklist Joe set on 2026-07-24 (visibility, deterministic-vs-non-deterministic, composability) so it doesn't need to be re-derived from memory each time.
---

# Auditing a skill (or the whole skill set)

Joe's own framing (2026-07-24), preserved verbatim in intent:

1. **Visibility** -- flag skills with high-risk side effects (deploy, commit,
   send messages, or anything else that touches shared/remote/external state)
   and set `disable-model-invocation: true` so they can't auto-fire. The
   default is a human has to explicitly ask for those.
2. **Deterministic vs non-deterministic** -- find steps where the AI is doing
   something that's actually a fixed, repeatable operation, and replace it
   with a script saved in the skill's folder. A script gives the same result
   every time at no token cost; keep the AI for the steps that genuinely need
   judgment (deciding *what* to fix, *whether* something is wrong, *how* to
   word a commit message).
3. **Composability** -- flag any skill duplicating logic another skill
   already has. Extract shared logic into a callable script or a smaller
   composable skill instead of copy-pasting it.

## 1. Run the discovery script

```powershell
python ".claude\skills\etymology-skill-audit\scripts\list_skills.py" "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
```

This is the deterministic part of the audit -- it enumerates every skill,
its frontmatter (`disable-model-invocation` in particular), and its
`scripts/` contents, and flags any auto-invocable skill whose description
mentions a risky verb (deploy/commit/push/send/delete/remove/drop/rm) without
`disable-model-invocation: true` set. Treat its flags as candidates to
examine, not a verdict -- a skill can legitimately mention "delete" in
passing without actually performing one.

## 2. Apply judgment per dimension

For the skill(s) in scope:

- **Visibility**: does it actually perform (not just discuss) a
  deploy/commit/push/send/delete against shared or remote state? If yes and
  `disable-model-invocation` isn't set, that's a real finding -- fix it.
  Also check for the same *shape* of risk even without the literal verb (e.g.
  `etymology-regen` isn't a commit/push, but a 15-70 minute unattended
  process that restarts a live server has the same "don't let this auto-fire"
  profile -- it was gated for that reason, not because it matched a keyword).
- **Deterministic vs non-deterministic**: read the skill body for any inline
  code block or narrated multi-step procedure that has no decision point in
  it (same command every time, same parsing logic every time). That belongs
  in a script under that skill's `scripts/` folder, not typed out fresh each
  invocation.
- **Composability**: compare the skill's scripts and instructions against
  every other skill's. If two skills solve the same sub-problem (e.g. "look
  up a word's current resolver answer"), the shared logic belongs in one
  place both point to -- this project's convention is a shared script at the
  project root's `scripts/` folder (see `check_word.py`, `check_raw_data.py`,
  used by both `etymology-fix-word` and `etymology-coverage-scan`) when two
  or more *skills* need it, versus a skill-local `scripts/` subfolder when
  only one skill does.

## 3. Ship the fix and log it

Same as any other skill change: edit the `SKILL.md`/scripts directly, then
add an entry to `.claude\skills\CHANGELOG.md` (newest entries first) stating
what changed and why -- this is a standing requirement (see the changelog's
own header), not specific to audits.

## 4. If a skill turns out not to be earning its place

Don't just leave it to rot or quietly delete it -- rescope its trigger
description, fold it into a skill that IS getting used, or narrow/widen what
it covers so it becomes useful. Only remove a skill outright if no
plausible fix exists and Joe agrees it should go.

## Additional resources

- `scripts/list_skills.py [repo_path]` -- the discovery script used in step 1.
