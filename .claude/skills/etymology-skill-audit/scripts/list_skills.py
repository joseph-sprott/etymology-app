"""Deterministic discovery pass for the skill audit.

Walks .claude/skills/*/SKILL.md, parses the YAML-ish frontmatter (name,
description, disable-model-invocation) without requiring PyYAML, lists each
skill's scripts/ subdirectory, and flags skills whose description mentions a
high-risk verb (deploy/commit/push/send/delete/rm) but have no
disable-model-invocation setting. Flags are candidates for a human/AI
judgment call, not an automatic verdict -- this script only surfaces facts.
"""
import os
import re
import sys

RISKY_VERBS = re.compile(r"\b(deploy|commit|push|send|delete|remove|drop|rm)\b", re.IGNORECASE)


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            fm[key] = val.strip('"')
    return fm


def find_skills(skills_root):
    skills = []
    if not os.path.isdir(skills_root):
        return skills
    for name in sorted(os.listdir(skills_root)):
        skill_dir = os.path.join(skills_root, name)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        with open(skill_md, "r", encoding="utf-8") as f:
            text = f.read()
        fm = parse_frontmatter(text)
        scripts_dir = os.path.join(skill_dir, "scripts")
        scripts = sorted(os.listdir(scripts_dir)) if os.path.isdir(scripts_dir) else []
        # A skill can also USE shared scripts kept at the project root
        # (scripts/check_word.py etc.), which is this project's convention
        # when two or more skills need the same tool -- see the composability
        # dimension. Reporting only skill-local scripts made those skills look
        # tool-less (fixed 2026-07-25 after this script reported "(none)" for
        # etymology-fix-word, which has had check_word.py/check_raw_data.py
        # since the day it was written). A future reader trusting that would
        # rebuild tooling that already exists -- the exact duplication this
        # audit is supposed to catch.
        shared = sorted(set(re.findall(r"scripts[\\/]([A-Za-z0-9_.-]+\.(?:py|ps1))", text)))
        shared = [s for s in shared if s not in scripts]
        skills.append({
            "dir": name,
            "name": fm.get("name", name),
            "description": fm.get("description", ""),
            "disable_model_invocation": fm.get("disable-model-invocation", "false"),
            "scripts": scripts,
            "shared_scripts": shared,
        })
    return skills


def main():
    repo_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    skills_root = os.path.join(repo_root, ".claude", "skills")
    skills = find_skills(skills_root)

    if not skills:
        print(f"No skills found under {skills_root}")
        return 0

    print(f"Found {len(skills)} skill(s) under {skills_root}\n")
    flags = []
    for s in skills:
        auto = s["disable_model_invocation"].lower() != "true"
        print(f"- {s['name']} (dir: {s['dir']})")
        print(f"    auto-invocable: {auto}")
        print(f"    scripts: {', '.join(s['scripts']) if s['scripts'] else '(none of its own)'}")
        if s["shared_scripts"]:
            print(f"    shared:  {', '.join(s['shared_scripts'])}  (project-root scripts/)")
        if auto and RISKY_VERBS.search(s["description"]):
            verb = RISKY_VERBS.search(s["description"]).group(1)
            flags.append((s["name"], verb))
            print(f"    FLAG: auto-invocable but description mentions '{verb}' -- review for disable-model-invocation")
        print()

    if flags:
        print(f"{len(flags)} skill(s) flagged for visibility review:")
        for name, verb in flags:
            print(f"  - {name}: mentions '{verb}'")
    else:
        print("No visibility flags -- no auto-invocable skill mentions a high-risk verb.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
