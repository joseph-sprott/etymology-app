---
name: etymology-parallel-sync
description: This skill should be used when a parallel or background Claude Code session (working in a separate git worktree) has pushed commits to origin that need to be pulled into the current session's checkout of the Etymology Analyzer project -- e.g. "pull in the other agent's research", "sync with what the parallel session pushed", "another session finished, check for its changes", or a `git pull` fails because of an untracked-file conflict.
---

# Syncing in a parallel agent's work

Multiple Claude Code sessions can work on this project at once, each in its
own git worktree (see `.claude/worktrees/`). When one of them pushes to
`origin`, pulling that into a different session's checkout can fail if that
session independently created a file with the same name and path (untracked,
so git won't just merge it) -- this happened for real on 2026-07-24 when
`FUTURE_FEATURES_AND_RESOURCES.md` existed locally, untracked, at the same
path a parallel session had just pushed.

The standing safety rule applies here same as anywhere else: never discard
uncommitted or untracked work to make a conflict go away. Back it up first,
always.

## 1. Run the sync script

```powershell
powershell -File ".claude\skills\etymology-parallel-sync\scripts\sync_worktree_research.ps1"
```

This does the whole mechanical sequence:
- `git fetch origin`
- `git pull --ff-only` (never a merge commit, never `--force` -- if a
  fast-forward isn't possible, that's a signal to look at the divergence by
  hand, not to script through it)
- if the pull fails specifically because untracked files would be
  overwritten, it parses the filenames git names in its own error output,
  copies each one to a timestamped backup under `%TEMP%\etymology-sync-backups`,
  and retries the pull
- after a successful pull, diffs each backed-up file against the newly-pulled
  version and reports `IDENTICAL` or `DIFFERS` for each -- it never deletes
  the backup itself, that's a judgment call left to the next step

## 2. Handle the diff result

- **IDENTICAL** -- the local copy and the parallel session's pushed version
  are byte-for-byte the same (this was the actual outcome on 2026-07-24: a
  local read-only copy of research another session had also produced). Safe
  to proceed; the backup can be left alone or cleaned up, no merge needed.
- **DIFFERS** -- genuine divergent content exists in both versions. Do not
  pick one arbitrarily. Read both (the backup path is printed) and decide
  whether to fold changes from the backup into the newly-pulled file, keep
  the pulled version, or flag it to Joe if it's not obviously resolvable.

## 3. Confirm

The script's own final `git log -3` and `git status --short` output is the
confirmation -- check that the expected commits are now present and the
working tree is clean (other than any intentionally-kept backup residue,
which lives outside the repo in `%TEMP%`, not in the working tree).

## Additional resources

- `scripts/sync_worktree_research.ps1 -RepoPath <path> -BackupDir <path> -Branch <name>`
  -- all optional, default to this project's root, `%TEMP%\etymology-sync-backups`,
  and the current branch.
