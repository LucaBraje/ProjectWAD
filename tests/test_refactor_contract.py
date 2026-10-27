"""Static checks; run with: python -m unittest discover -s tests -v"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RefactorContract(unittest.TestCase):
    def test_all_python_files_compile(self):
        for file in ROOT.rglob("*.py"):
            with self.subTest(file=str(file.relative_to(ROOT))):
                compile(file.read_bytes(), str(file), "exec")

    def test_no_routes_declared_in_app(self):
        tree = ast.parse((ROOT / "app.py").read_text())
        self.assertFalse(any(isinstance(n, ast.FunctionDef) and any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and d.func.attr == "route" for d in n.decorator_list
        ) for n in tree.body))

    def test_expected_legacy_endpoint_registration(self):
        source = (ROOT / "routes/__init__.py").read_text()
        for endpoint in ("get_legends", "get_players", "fantasy_dashboard",
                         "admin_schedule_finalize", "simulate_draft_api",
                         "hl_guess", "api_schedule", "profile_titles"):
            with self.subTest(endpoint=endpoint):
                self.assertIn("endpoint='" + endpoint + "'", source)

    def test_external_games_register_before_database_init(self):
        src = (ROOT / "app.py").read_text()
        self.assertLess(src.index("BasketballGridGame = register_basketball_grid"),
                        src.index("if __name__ =="))
        self.assertLess(src.index("GuessPlayerStats = register_guess_the_player"),
                        src.index("if __name__ =="))

if __name__ == "__main__":
    unittest.main()
