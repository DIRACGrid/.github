# DIRACGrid `.github`

Organization-level GitHub configuration for [DIRACGrid](https://github.com/DIRACGrid).

## What lives here

| Path | Purpose |
|---|---|
| `renovate-config.json` | The shared [Renovate](https://docs.renovatebot.com/) preset consumed by **every** repository in the organization: digest-pinned GitHub Actions, grouped Actions updates, a 7-day release-age cooldown, lock file maintenance, and guardrails (no CI interpreter bumps, no tornado bumps, dashboard approval for pre-commit hook majors) |
| `profile/` | The organization profile shown on https://github.com/DIRACGrid |
| `.github/workflows/` | Organization-level workflows: PR review reminders, draft-PR conversion, Renovate preset validation |
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

The preset is validated in CI on every change to `renovate-config.json`: a broken preset would break Renovate for the whole organization at once.

## More information

- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute to DIRACGrid projects
- [Security policy](SECURITY.md)
- Ongoing organization-wide hardening work is tracked in [issue #5](https://github.com/DIRACGrid/.github/issues/5)
