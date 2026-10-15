import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ("AGENT_MEMORY_SYSTEM", "B77_HTML_PWA", "CARD111", "ORGANISM", "RECIPE_MANAGER")


def _synthetic_project_events():
    """Minimal regression fixture for ownership and intentional cross-project links.

    Full project histories are deliberately integrated in separate scope-controlled
    changes. When all five canonical project logs are present, tests use those real
    files instead of this fixture.
    """
    return {
        "AGENT_MEMORY_SYSTEM": [
            {"event_id": "EVT-AGMS-XBR-TEST-001", "project_id": "AGENT_MEMORY_SYSTEM", "type": "checkpoint", "summary": "synthetic AGMS checkpoint", "related_event_ids": []}
        ],
        "B77_HTML_PWA": [
            {"event_id": "EVT-B77-20260922-001", "project_id": "B77_HTML_PWA", "type": "observation", "summary": "HTML ingredient/database report", "related_event_ids": []},
            {"event_id": "EVT-20261012-014", "project_id": "B77_HTML_PWA", "type": "reconciliation", "summary": "B77 HTML reconciliation", "related_event_ids": ["EVT-20261012-013"]},
            {"event_id": "EVT-20261012-016", "project_id": "B77_HTML_PWA", "type": "reconciliation", "summary": "B77 UI reconciliation", "related_event_ids": ["EVT-20261012-011", "EVT-20261012-015"]}
        ],
        "CARD111": [
            {"event_id": "EVT-CARD111-20261005-001", "project_id": "CARD111", "type": "observation", "summary": "synthetic CARD111 event", "related_event_ids": []}
        ],
        "ORGANISM": [
            {"event_id": "EVT-ORGANISM-20261008-002", "project_id": "ORGANISM", "type": "observation", "summary": "synthetic ORGANISM event", "related_event_ids": []}
        ],
        "RECIPE_MANAGER": [
            {"event_id": "EVT-20261012-011", "project_id": "RECIPE_MANAGER", "type": "observation", "summary": "recipe-manager event", "related_event_ids": []},
            {"event_id": "EVT-20261012-013", "project_id": "RECIPE_MANAGER", "type": "observation", "summary": "recipe-manager event", "related_event_ids": []},
            {"event_id": "EVT-20261012-015", "project_id": "RECIPE_MANAGER", "type": "observation", "summary": "recipe-manager event", "related_event_ids": []},
            {"event_id": "EVT-20260927-001", "project_id": "RECIPE_MANAGER", "type": "incident", "summary": "Flet API incident", "related_event_ids": []}
        ]
    }


def load_project_events():
    paths = {project_id: ROOT / "projects" / project_id / "events.jsonl" for project_id in PROJECTS}
    if all(path.is_file() for path in paths.values()):
        by_project = {
            project_id: [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            for project_id, path in paths.items()
        }
    else:
        by_project = _synthetic_project_events()

    records = {}
    for project_id, rows in by_project.items():
        for row in rows:
            event_id = row["event_id"]
            if event_id in records:
                raise AssertionError(f"duplicate event_id across project logs: {event_id}")
            records[event_id] = (project_id, row)
    return records, by_project


class ProjectMemoryBoundaryTests(unittest.TestCase):
    def test_project_event_ownership_and_links_are_consistent(self):
        records, by_project = load_project_events()
        dangling = []
        for folder_project, rows in by_project.items():
            for row in rows:
                self.assertEqual(
                    row.get("project_id"),
                    folder_project,
                    f"{row['event_id']} is stored under {folder_project} but claims another project",
                )
                refs = list(row.get("related_event_ids", []))
                relations = row.get("relations", [])
                if isinstance(relations, list):
                    refs.extend(
                        relation["event_id"]
                        for relation in relations
                        if isinstance(relation, dict) and isinstance(relation.get("event_id"), str)
                    )
                for event_id in refs:
                    if event_id not in records:
                        dangling.append((row["event_id"], event_id))
        self.assertEqual(dangling, [])

    def test_html_regression_event_is_owned_by_b77_not_recipe_manager(self):
        records, by_project = load_project_events()
        b77_ids = {row["event_id"] for row in by_project["B77_HTML_PWA"]}
        recipe_ids = {row["event_id"] for row in by_project["RECIPE_MANAGER"]}

        self.assertIn("EVT-B77-20260922-001", b77_ids)
        self.assertNotIn("EVT-B77-20260922-001", recipe_ids)
        # This was the old misclassified N99/RECIPE_MANAGER event ID.
        self.assertNotIn("EVT-20260922-001", recipe_ids)

    def test_explicit_b77_recipe_manager_links_are_preserved(self):
        records, by_project = load_project_events()
        b77 = {row["event_id"]: row for row in by_project["B77_HTML_PWA"]}
        recipe_ids = {row["event_id"] for row in by_project["RECIPE_MANAGER"]}

        self.assertIn("EVT-20261012-013", recipe_ids)
        self.assertIn("EVT-20261012-011", recipe_ids)
        self.assertIn("EVT-20261012-015", recipe_ids)
        self.assertIn("EVT-20261012-013", b77["EVT-20261012-014"].get("related_event_ids", []))
        self.assertIn("EVT-20261012-011", b77["EVT-20261012-016"].get("related_event_ids", []))
        self.assertIn("EVT-20261012-015", b77["EVT-20261012-016"].get("related_event_ids", []))


if __name__ == "__main__":
    unittest.main()
