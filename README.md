# DIRACGrid `.github`

Organization-level GitHub configuration for [DIRACGrid](https://github.com/DIRACGrid).

## What lives here

| Path | Purpose |
|---|---|
| `renovate-config.json` | The shared [Renovate](https://docs.renovatebot.com/) preset extended by the DIRACGrid repositories: digest-pinned GitHub Actions, grouped updates, a 7-day release-age cooldown, lock file maintenance, and no CI interpreter bumps |
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

## More information

- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute to DIRACGrid projects
- [Security policy](SECURITY.md)
- Ongoing organization-wide hardening work is tracked in [issue #5](https://github.com/DIRACGrid/.github/issues/5)
