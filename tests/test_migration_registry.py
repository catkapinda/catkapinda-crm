from __future__ import annotations

import unittest

from infrastructure.migrations import MigrationStep, get_latest_migration_version, get_pending_migrations


class MigrationRegistryTests(unittest.TestCase):
    def test_get_latest_migration_version_returns_last_sorted_version(self):
        steps = [
            MigrationStep(version="2026-03-21-a", apply_fn=lambda conn: None),
            MigrationStep(version="2026-03-22-b", apply_fn=lambda conn: None),
            MigrationStep(version="2026-03-20-c", apply_fn=lambda conn: None),
        ]

        self.assertEqual(get_latest_migration_version(steps), "2026-03-22-b")

    def test_get_pending_migrations_returns_only_versions_after_current(self):
        steps = [
            MigrationStep(version="2026-03-20-a", apply_fn=lambda conn: None),
            MigrationStep(version="2026-03-21-b", apply_fn=lambda conn: None),
            MigrationStep(version="2026-03-22-c", apply_fn=lambda conn: None),
        ]

        pending = get_pending_migrations("2026-03-21-b", steps)
        self.assertEqual([step.version for step in pending], ["2026-03-22-c"])

    def test_get_pending_migrations_returns_all_when_no_current_version(self):
        steps = [
            MigrationStep(version="2026-03-20-a", apply_fn=lambda conn: None),
            MigrationStep(version="2026-03-21-b", apply_fn=lambda conn: None),
        ]

        pending = get_pending_migrations("", steps)
        self.assertEqual([step.version for step in pending], ["2026-03-20-a", "2026-03-21-b"])


if __name__ == "__main__":
    unittest.main()
