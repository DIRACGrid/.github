#!/usr/bin/env python3
"""Give a repository's release workflow a deploy key that may pass the rulesets.

Creates the `release` environment (limited to the given branches), a write
deploy key whose private half only ever exists in that environment's secret
RELEASE_DEPLOY_KEY, and adds deploy keys as bypass actor of the `branches` and
`tags` rulesets. Needs admin on the repository, plus `gh` and `ssh-keygen`.

    setup_release_key.py DIRACGrid/DIRAC integration 'rel-v*r*'
    setup_release_key.py --rotate DIRACGrid/DIRAC integration 'rel-v*r*'
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

KEY_TITLE = "release-ci"
ENVIRONMENT = "release"
SECRET = "RELEASE_DEPLOY_KEY"
BYPASS = {"actor_id": None, "actor_type": "DeployKey", "bypass_mode": "always"}


def gh(*args, data=None):
    cmd = ["gh", "api", *args]
    if data is not None:
        cmd += ["--input", "-"]
    out = subprocess.run(
        cmd, input=json.dumps(data) if data is not None else None, text=True, capture_output=True, check=True
    ).stdout
    return json.loads(out) if out.strip() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", help="owner/name")
    parser.add_argument("branches", nargs="+", help="branch patterns allowed to use the key")
    parser.add_argument("--rulesets", nargs="*", default=["branches", "tags"], help="rulesets that get the bypass")
    parser.add_argument("--rotate", action="store_true", help="replace an existing key")
    args = parser.parse_args()
    repo = args.repo

    existing = [k for k in gh(f"repos/{repo}/keys") if k["title"] == KEY_TITLE]
    if existing and not args.rotate:
        raise SystemExit(f"{repo} already has a '{KEY_TITLE}' deploy key; use --rotate to replace it")

    # Environment: only the release branches can read its secrets.
    gh(
        "-X", "PUT", f"repos/{repo}/environments/{ENVIRONMENT}",
        data={"deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}},
    )
    policies = gh(f"repos/{repo}/environments/{ENVIRONMENT}/deployment-branch-policies")["branch_policies"]
    for pattern in args.branches:
        if not any(p["name"] == pattern and p.get("type", "branch") == "branch" for p in policies):
            gh(
                "-X", "POST", f"repos/{repo}/environments/{ENVIRONMENT}/deployment-branch-policies",
                data={"name": pattern, "type": "branch"},
            )

    with tempfile.TemporaryDirectory() as tmp:
        key = Path(tmp) / "key"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"{KEY_TITLE}@{repo}", "-f", str(key)], check=True
        )
        with key.open() as private:
            subprocess.run(
                ["gh", "secret", "set", SECRET, "--env", ENVIRONMENT, "--repo", repo], stdin=private, check=True
            )
        gh(
            "-X", "POST", f"repos/{repo}/keys",
            data={"title": KEY_TITLE, "key": key.with_suffix(".pub").read_text().strip(), "read_only": False},
        )
    for old in existing:
        gh("-X", "DELETE", f"repos/{repo}/keys/{old['id']}")

    for summary in gh(f"repos/{repo}/rulesets"):
        if summary["name"] not in args.rulesets:
            continue
        ruleset = gh(f"repos/{repo}/rulesets/{summary['id']}")
        actors = ruleset.get("bypass_actors") or []
        if any(a["actor_type"] == "DeployKey" for a in actors):
            continue
        body = {k: ruleset[k] for k in ("name", "target", "enforcement", "conditions", "rules")}
        body["bypass_actors"] = [
            {k: a[k] for k in ("actor_id", "actor_type", "bypass_mode")} for a in actors
        ] + [BYPASS]
        gh("-X", "PUT", f"repos/{repo}/rulesets/{summary['id']}", data=body)
        print(f"{repo}: deploy keys may now bypass ruleset '{summary['name']}'")

    print(f"{repo}: deploy key '{KEY_TITLE}' installed, secret {SECRET} set in environment '{ENVIRONMENT}'")


if __name__ == "__main__":
    main()
