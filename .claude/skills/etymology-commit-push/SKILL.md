---
name: etymology-commit-push
description: This skill should be used when the user explicitly asks to "commit this", "commit and push", "push to GitHub", or "ship this change" for the Etymology Analyzer project. Not for silently deciding on its own that uncommitted work should be committed -- see disable-model-invocation below.
disable-model-invocation: true
---

<!--
disable-model-invocation is set deliberately (2026-07-24 skill audit --
commit/push is one of the three named high-risk-side-effect categories,
along with deploy and send-message, that should never auto-fire). The user
must explicitly ask for a commit; Claude should not decide on its own that
now is a good time to commit and push, even after finishing a fix.
-->

# Committing and pushing changes

The git plumbing here is entirely mechanical -- staging, committing, pushing,
confirming. Only the commit MESSAGE content requires judgment (summarizing
what actually changed and why), so that's the one thing this skill doesn't
script.

## 1. Review what's about to be staged

This skill's script does NOT pause for review -- it stages, commits, and
pushes in one shot. Look at the current state first, before invoking it:

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cd "C:\Users\Josep\Desktop\Etymology Project\etymology-app"
git status
```

If anything unexpected shows up (a file that shouldn't be there, something
that looks like it could contain a secret even if the filename looks
innocuous), stop and investigate before continuing -- do not rely on the
script to catch this.

## 2. Write the commit message to a file

Do not pass a multi-line message via `-m "..."` through PowerShell -- a
here-string with quotes inside it broke mid-session (git received the
message split into multiple mis-parsed pathspec arguments, e.g. `error:
pathspec 'entry' did not match any file(s)`). Write the message to a plain
file instead:

```
Write tool -> some temp path (e.g. C:\Users\Josep\.claude\jobs\<job-id>\tmp\commit_msg.txt if running as a background job, otherwise any scratch location)
```

Compose the message the way every commit this session was written: a one-line
summary, then a blank line, then paragraphs explaining what changed and why
(not just what) -- match the style already in this repo's `git log`.

## 3. Commit and push

```powershell
powershell -File .claude\skills\etymology-commit-push\scripts\commit_and_push.ps1 -MessageFile "PATH_TO_MESSAGE_FILE"
```

Stages everything (`git add -A`), prints `git status` for the record, commits
with `-F` (the message file), pushes, and prints the last 3 log entries to
confirm. Fails loudly (non-zero exit, `FAIL:` prefix) at whichever step
didn't work rather than silently continuing -- if it fails, report the exact
failure rather than retrying blindly.

## Additional resources

- `scripts/commit_and_push.ps1 -MessageFile <path> [-RepoPath <path>]` -- the
  script used in step 3. Defaults `RepoPath` to this project's root.
