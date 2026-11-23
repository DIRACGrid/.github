"""Tests for the ruleset rendering and comparison (no network)."""

import unittest

from rulesets import compare, normalize
from rulesets import render as _render

ACTORS = {
    "renovate": {"actor_type": "Integration", "actor_id": 2740},
    "dirac-release-manager": {"actor_type": "Team", "actor_id": 52350},
    "github-actions": {"actor_type": "Integration", "actor_id": 15368},
}


def render(params, default_branch):
    return _render(params, default_branch, ACTORS)


def norm(ruleset):
    return normalize(ruleset, "main")


class RulesetsTest(unittest.TestCase):
    def test_render_defaults(self):
        wanted = render({}, "main")
        self.assertEqual(set(wanted), {"branches", "fork-only", "tags"})
        self.assertEqual(
            wanted["branches"]["conditions"]["ref_name"]["include"], ["refs/heads/main"]
        )
        self.assertEqual(
            wanted["fork-only"]["conditions"]["ref_name"]["exclude"],
            ["refs/heads/main"],
        )

    def test_render_parameters(self):
        wanted = render(
            {
                "protected": ["integration", "rel-v*r*"],
                "fork_only_exclude": ["renovate/*"],
                "tags": False,
            },
            "integration",
        )
        self.assertIn("no tags", wanted)
        self.assertEqual(
            wanted["fork-only"]["conditions"]["ref_name"]["exclude"],
            ["refs/heads/integration", "refs/heads/rel-v*r*", "refs/heads/renovate/*"],
        )

    def test_actors_are_resolved(self):
        wanted = render({}, "main")
        self.assertEqual(
            wanted["fork-only"]["bypass_actors"],
            [{"actor_type": "Integration", "actor_id": 2740, "bypass_mode": "always"}],
        )
        self.assertEqual(wanted["tags"]["bypass_actors"][0]["actor_id"], 52350)

    def test_required_checks_are_pinned_to_github_actions(self):
        wanted = render(
            {
                "protected": ["integration", "rel-v*r*"],
                "branches_all": True,
                "required_checks": ["pre-commit"],
                "code_owners": False,
            },
            "integration",
        )
        required = wanted["required-checks"]
        # Never on every branch, whatever `branches_all` says.
        self.assertEqual(
            required["conditions"]["ref_name"]["include"],
            ["refs/heads/integration", "refs/heads/rel-v*r*"],
        )
        self.assertEqual(
            required["rules"][0]["parameters"]["required_status_checks"],
            [{"context": "pre-commit", "integration_id": 15368}],
        )
        pull_request = next(
            r for r in wanted["branches"]["rules"] if r["type"] == "pull_request"
        )
        self.assertFalse(pull_request["parameters"]["require_code_owner_review"])
        self.assertNotIn("required-checks", render({}, "main"))

    def test_equivalent_live_ruleset_is_not_drift(self):
        wanted = render({}, "main")["branches"]
        live = {
            **wanted,
            "id": 1,
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "rules": [
                *reversed(wanted["rules"]),
                {
                    "type": "required_status_checks",
                    "parameters": {"required_status_checks": []},
                },
            ],
        }
        self.assertEqual(compare(norm(live), norm(wanted)), [])

    def test_drift_is_reported(self):
        wanted = render({}, "main")["fork-only"]
        live = {**wanted, "bypass_actors": [], "rules": wanted["rules"][:-1]}
        diffs = compare(norm(live), norm(wanted))
        self.assertEqual(len(diffs), 2)
        self.assertTrue(any(d.startswith("bypass_actors") for d in diffs))
        self.assertTrue(any("missing" in d for d in diffs))


if __name__ == "__main__":
    unittest.main()
