#!/usr/bin/env python3
"""Compare or apply the DIRACGrid repository rulesets defined in ``rulesets/``.

    scripts/rulesets.py                      # diff every repository (read-only)
    scripts/rulesets.py diff --repo diracx
    scripts/rulesets.py apply --repo diracx --yes [--prune]

Needs the ``gh`` CLI, logged in as an admin of the repositories.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

RULESETS_DIR = Path(__file__).resolve().parent.parent / "rulesets"


def gh(*args: str, body: dict | None = None):
    """Call ``gh api`` and return the decoded JSON response."""
    cmd = ["gh", "api", *args]
    if body is not None:
        cmd += ["--input", "-"]
    out = subprocess.run(
        cmd,
        input=json.dumps(body) if body is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode:
        sys.exit(f"gh api {' '.join(args)} failed:\n{out.stderr or out.stdout}")
    return json.loads(out.stdout) if out.stdout.strip() else None


def template(name: str) -> dict:
    return json.loads((RULESETS_DIR / f"{name}.json").read_text())


def render(params: dict, default_branch: str, actors: dict) -> dict[str, dict]:
    """Return the rulesets one repository should have, keyed by ruleset name.

    ``actors`` is the ``[actors]`` table of repos.toml: the templates name their
    bypass actors, GitHub wants the numeric ids.
    """
    protected = [f"refs/heads/{b}" for b in params.get("protected", [default_branch])]
    extra = [f"refs/heads/{b}" for b in params.get("fork_only_exclude", [])]

    branches = template("branches")
    branches["conditions"]["ref_name"]["include"] = (
        ["~ALL"] if params.get("branches_all") else protected
    )
    pull_request = next(r for r in branches["rules"] if r["type"] == "pull_request")
    pull_request["parameters"]["require_code_owner_review"] = params.get(
        "code_owners", True
    )
    if methods := params.get("merge_methods"):
        pull_request["parameters"]["allowed_merge_methods"] = methods

    fork_only = template("fork-only")
    fork_only["conditions"]["ref_name"]["exclude"] = protected + extra

    tags = template("tags" if params.get("tags", True) else "no-tags")
    rulesets = [branches, fork_only, tags]

    # A ruleset of its own, always on the protected branches only: with
    # `branches_all` the checks would otherwise also gate pushes to renovate/*.
    if checks := params.get("required_checks"):
        required = template("required-checks")
        required["conditions"]["ref_name"]["include"] = protected
        required["rules"][0]["parameters"]["required_status_checks"] = [
            {"context": c, "integration_id": actors["github-actions"]["actor_id"]}
            for c in checks
        ]
        rulesets.append(required)

    for ruleset in rulesets:
        ruleset["bypass_actors"] = [
            {**actors[name], "bypass_mode": "always"}
            for name in ruleset["bypass_actors"]
        ]
    return {r["name"]: r for r in rulesets}


def normalize(ruleset: dict, default_branch: str) -> dict:
    """Reduce a ruleset to what matters, in a stable order."""
    ref_name = ruleset.get("conditions", {}).get("ref_name", {})

    def refs(key: str) -> list[str]:
        return sorted(
            f"refs/heads/{default_branch}" if r == "~DEFAULT_BRANCH" else r
            for r in ref_name.get(key, [])
        )

    rules = {}
    for rule in ruleset.get("rules", []):
        params = dict(rule.get("parameters") or {})
        if rule["type"] == "required_status_checks":
            checks = params.get("required_status_checks", [])
            # A rule that requires no check is the same as no rule.
            if not checks:
                continue
            params["required_status_checks"] = sorted(checks, key=json.dumps)
        rules[rule["type"]] = params
    return {
        "enforcement": ruleset.get("enforcement"),
        "target": ruleset.get("target"),
        "include": refs("include"),
        "exclude": refs("exclude"),
        "rules": rules,
        "bypass_actors": sorted(
            f"{b['actor_type']}:{b.get('actor_id')}:{b['bypass_mode']}"
            for b in ruleset.get("bypass_actors", [])
        ),
    }


def compare(live: dict, wanted: dict) -> list[str]:
    """List the differences between two normalized rulesets."""
    diffs = [
        f"{key}: live {live[key]} != template {wanted[key]}"
        for key in ("enforcement", "target", "include", "exclude", "bypass_actors")
        if live[key] != wanted[key]
    ]
    for rule in sorted(set(live["rules"]) | set(wanted["rules"])):
        if rule not in wanted["rules"]:
            diffs.append(f"rule {rule}: not in template")
        elif rule not in live["rules"]:
            diffs.append(f"rule {rule}: missing")
        else:
            # Only the template's keys: GitHub returns more, with defaults.
            for key, value in wanted["rules"][rule].items():
                got = live["rules"][rule].get(key)
                if got != value:
                    diffs.append(f"rule {rule}.{key}: live {got} != template {value}")
    return diffs


def live_rulesets(org: str, repo: str) -> dict[str, dict]:
    listed = gh(f"repos/{org}/{repo}/rulesets?includes_parents=false&per_page=100")
    return {r["name"]: gh(f"repos/{org}/{repo}/rulesets/{r['id']}") for r in listed}


def diff_repo(org: str, repo: str, params: dict, actors: dict) -> list[str]:
    default_branch = gh(f"repos/{org}/{repo}")["default_branch"]
    wanted = render(params, default_branch, actors)
    live = live_rulesets(org, repo)
    lines = []
    for name, ruleset in wanted.items():
        if name not in live:
            lines.append(f"{name}: missing")
            continue
        lines += [
            f"{name}: {d}"
            for d in compare(
                normalize(live[name], default_branch),
                normalize(ruleset, default_branch),
            )
        ]
    lines += [
        f"{name}: not in template ({live[name]['enforcement']})"
        for name in sorted(set(live) - set(wanted))
    ]
    return lines


def apply_repo(org: str, repo: str, params: dict, actors: dict, prune: bool) -> None:
    default_branch = gh(f"repos/{org}/{repo}")["default_branch"]
    live = live_rulesets(org, repo)
    wanted = render(params, default_branch, actors)
    for name, ruleset in wanted.items():
        if name in live:
            gh(
                "-X",
                "PUT",
                f"repos/{org}/{repo}/rulesets/{live[name]['id']}",
                body=ruleset,
            )
            print(f"{repo}: updated {name}")
        else:
            gh("-X", "POST", f"repos/{org}/{repo}/rulesets", body=ruleset)
            print(f"{repo}: created {name}")
    for name in sorted(set(live) - set(wanted)):
        if prune:
            gh("-X", "DELETE", f"repos/{org}/{repo}/rulesets/{live[name]['id']}")
            print(f"{repo}: deleted {name}")
        else:
            print(
                f"{repo}: kept {name}, which is not in the template (--prune deletes it)"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", choices=["diff", "apply"], default="diff")
    parser.add_argument("--repo", help="one repository (required for apply)")
    parser.add_argument("--yes", action="store_true", help="confirm apply")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="apply: delete rulesets not in the template",
    )
    args = parser.parse_args()

    config = tomllib.loads((RULESETS_DIR / "repos.toml").read_text())
    org, repos, actors = config["org"], config["repos"], config["actors"]
    if args.repo and args.repo not in repos:
        parser.error(f"{args.repo} is not in rulesets/repos.toml")

    if args.command == "apply":
        if not (args.repo and args.yes):
            parser.error("apply needs --repo and --yes")
        apply_repo(org, args.repo, repos[args.repo], actors, args.prune)
        return 0

    drift = False
    for repo in [args.repo] if args.repo else sorted(repos, key=str.lower):
        lines = diff_repo(org, repo, repos[repo], actors)
        drift |= bool(lines)
        print(f"{repo}: ok" if not lines else f"{repo}:")
        for line in lines:
            print(f"  {line}")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
