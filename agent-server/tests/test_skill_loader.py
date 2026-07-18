import unittest
from pathlib import Path

from app.skills.loader import FigureSkillLoader, SkillSelectionRequired


class SkillLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project_root = Path(__file__).resolve().parents[2]
        cls.loader = FigureSkillLoader(project_root / ".agents" / "skills" / "figure")

    def test_requires_default_confirmation_without_user_reference(self) -> None:
        with self.assertRaises(SkillSelectionRequired):
            self.loader.load(use_default_style=False)

    def test_loads_complete_confirmed_default_bundle(self) -> None:
        bundle = self.loader.load(use_default_style=True)
        self.assertEqual(bundle.source, "confirmed-default")
        self.assertIn("#6C63FF", bundle.style_profile_text)
        self.assertTrue(bundle.template_path.is_file())
        self.assertIn("可编辑 draw.io", bundle.output_modes)


if __name__ == "__main__":
    unittest.main()

