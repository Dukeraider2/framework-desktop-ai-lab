Failed to create stream fd: Operation not permitted
Failed to create stream fd: Operation not permitted
Failed to create stream fd: Operation not permitted
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentIdentityTests(unittest.TestCase):
    def test_registry_has_seven_distinct_model_independent_profiles(self):
        registry = json.loads((ROOT / "agents/registry.json").read_text(encoding="utf-8"))
        agents = registry["agents"]
        self.assertEqual(len(agents), 7)
        self.assertEqual(len({agent["id"] for agent in agents}), 7)
        self.assertEqual(len({agent["name"] for agent in agents}), 7)
        self.assertNotIn("model", registry)
        self.assertEqual(registry["schema_version"], 2)
        for agent in agents:
            self.assertNotIn("model", agent)
            self.assertTrue(agent["expertise_areas"])
            self.assertEqual(agent["tool_permissions"], [])
            self.assertEqual(len(agent["aliases"]), len(set(alias.casefold() for alias in agent["aliases"])))
            profile = ROOT / agent["profile_distribution"]
            soul = ROOT / agent["soul"]
            self.assertTrue((profile / "distribution.yaml").is_file())
            self.assertTrue(soul.is_file())
            manifest = (profile / "distribution.yaml").read_text(encoding="utf-8")
            self.assertIn(f"name: {agent['id']}", manifest)
            self.assertNotIn("model:", manifest)
            config = (profile / "config.yaml").read_text(encoding="utf-8")
            self.assertIn("mcp_servers: {}", config)
            self.assertIn("enabled: []", config)
            self.assertNotIn("terminal", config)
            self.assertNotIn("delegation", config)
            self.assertNotIn("browser", config)

    def test_every_soul_contains_shared_independence_and_scope_rules(self):
        registry = json.loads((ROOT / "agents/registry.json").read_text(encoding="utf-8"))
        for agent in registry["agents"]:
            soul = (ROOT / agent["soul"]).read_text(encoding="utf-8")
            self.assertIn("## Personality", soul)
            self.assertIn("## Responsibilities", soul)
            self.assertIn("## Expertise", soul)
            self.assertIn("## Communication style", soul)
            self.assertIn("## Intellectual interests", soul)
            self.assertIn("## Collaboration expectations", soul)
            self.assertIn("intellectual independence over artificial consensus", soul.lower())
            self.assertIn("A mention or assignment is not permission", soul)
            self.assertIn("not the real person", soul.lower())


if __name__ == "__main__":
    unittest.main()
