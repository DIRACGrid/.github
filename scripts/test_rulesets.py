"""Tests for the ruleset rendering and comparison (no network)."""

import unittest

from rulesets import compare, normalize, render


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
