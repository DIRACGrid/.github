# DIRACGrid `.github`

Organization-level GitHub configuration for [DIRACGrid](https://github.com/DIRACGrid).

## What lives here

| Path | Purpose |
|---|---|
| `renovate-config.json` | The shared [Renovate](https://docs.renovatebot.com/) preset extended by the DIRACGrid repositories: digest-pinned GitHub Actions, grouped updates, a 7-day release-age cooldown, lock file maintenance, and no CI interpreter bumps |
| `rulesets/`, `scripts/rulesets.py` | The branch and tag rulesets every repository should have, and the script that compares them with GitHub or applies them |
| `profile/` | The organization profile shown on https://github.com/DIRACGrid |
| `.github/workflows/` | Workflows of this repository: pre-commit, Renovate config validation, and PR review reminders for the diracx repositories |
| `CONTRIBUTING.md`, `SECURITY.md` | Default community health files inherited by repositories without their own |

## Adopting the Renovate preset

Add a `renovate.json` to your repository:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>DIRACGrid/.github//renovate-config"]
}
```

Repositories with maintained release branches also set `baseBranchPatterns`, e.g. `["$default", "/^rel-/"]`.

CI validates the preset on every change: a broken preset would break Renovate for the whole organization at once.

## Repository rulesets

Every repository gets the same three rulesets, defined in `rulesets/`:

- `branches`: the protected branches only change through a reviewed pull request with signed commits.
- `fork-only`: nobody creates or pushes other branches in the repository, so pull requests come from forks. Renovate is the exception.
- `tags` or `no tags`: only release managers create tags, or nobody does.

What differs per repository (protected branches, whether it has releases, required checks) is in `rulesets/repos.toml`.

```bash
scripts/rulesets.py                              # show what differs on GitHub, for every repository
scripts/rulesets.py diff --repo diracx
scripts/rulesets.py apply --repo diracx --yes    # create or update the three rulesets
```

`diff` only reads and exits with 1 when something differs. `apply` needs admin rights on the repository; add `--prune` to also delete rulesets that are not in the template. Both need the `gh` CLI. The `fork-only` ruleset can only be applied where the Renovate app is installed.

To change the rules, edit the template or `repos.toml` in a pull request, then run `apply` once it is merged. Organization-level rulesets would replace this script, but they need a paid GitHub plan.

## More information

- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute to DIRACGrid projects
- [Security policy](SECURITY.md)
- Ongoing organization-wide hardening work is tracked in [issue #5](https://github.com/DIRACGrid/.github/issues/5)
