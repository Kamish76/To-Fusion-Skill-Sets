#!/usr/bin/env python3
"""
tests/test_sync_manager.py — Unit Tests for To-Fusion Universal Sync Manager
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.sync_manager import (
    discover_skills,
    parse_skill_metadata,
    create_dir_link,
    check_target_link,
    get_git_status,
    load_manifest,
)


class TestSyncManager(unittest.TestCase):

    def test_parse_skill_metadata_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            skill_md = tmp_path / "SKILL.md"
            skill_md.write_text(
                "---\nname: test-skill\ndescription: A test CAD skill\nversion: 2.1.0\n---\n# Content\n",
                encoding="utf-8"
            )
            scripts_dir = tmp_path / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "run_test.py").write_text("# script\n", encoding="utf-8")

            meta = parse_skill_metadata(tmp_path)
            self.assertEqual(meta["name"], "test-skill")
            self.assertEqual(meta["description"], "A test CAD skill")
            self.assertEqual(meta["version"], "2.1.0")
            self.assertTrue(meta["has_skill_md"])
            self.assertIn("run_test.py", meta["scripts"])

    def test_parse_skill_metadata_missing_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            skill_md = tmp_path / "SKILL.md"
            skill_md.write_text("# Simple markdown without frontmatter\n", encoding="utf-8")

            meta = parse_skill_metadata(tmp_path)
            self.assertEqual(meta["name"], tmp_path.name)
            self.assertEqual(meta["description"], "")
            self.assertEqual(meta["version"], "beta")

    def test_discover_skills_detects_existing_skills(self):
        skills = discover_skills()
        self.assertGreaterEqual(len(skills), 3)
        names = [s["name"] for s in skills]
        self.assertIn("3mf-to-fusion", names)
        self.assertIn("media-to-fusion", names)
        self.assertIn("text-to-fusion", names)
        self.assertIn("to-fusion-sync", names)
        self.assertIn("to-fusion-dev-sync", names)

    def test_create_and_check_dir_link(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_dir = tmp_path / "source_skill"
            source_dir.mkdir()
            (source_dir / "SKILL.md").write_text("---\nname: temp\n---\n", encoding="utf-8")

            link_target = tmp_path / "linked_target"

            # Create link / junction
            ok, method = create_dir_link(source_dir, link_target)
            self.assertTrue(ok, f"Link creation failed: {method}")

            # Check target link
            is_present, link_type = check_target_link(link_target)
            self.assertTrue(is_present)
            self.assertIn(link_type, ("symlink", "junction", "folder", "present"))

            # Verify contents accessible through link
            self.assertTrue((link_target / "SKILL.md").exists())

    def test_get_git_status_structure(self):
        st = get_git_status()
        self.assertIn("branch", st)
        self.assertIn("ahead", st)
        self.assertIn("behind", st)
        self.assertIn("is_dirty", st)
        self.assertIn("staged", st)
        self.assertIn("unstaged", st)
        self.assertIn("untracked", st)
        self.assertIsInstance(st["branch"], str)
        self.assertIsInstance(st["is_dirty"], bool)

    def test_load_manifest_structure(self):
        manifest = load_manifest()
        self.assertIsInstance(manifest, dict)
        self.assertIn("name", manifest)
        self.assertIn("skills", manifest)


if __name__ == "__main__":
    unittest.main()
