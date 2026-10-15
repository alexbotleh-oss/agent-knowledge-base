import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ("AGENT_MEMORY_SYSTEM", "B77_HTML_PWA", "CARD111", "ORGANISM", "RECIPE_MANAGER")


def load_project_events():
    records = {}
    by_project = {}
    for project_id in PROJECTS:
        path = ROOT / "projects" / project_id / "events.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        by_project[project_id] = rows
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
