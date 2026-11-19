import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {"dataset_extractor", "rates_scraper", "transactions_etl", "analytics", "dashboard"}


def imported_aml_etl_subpackages(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    parts = (name.split(".") for name in names)
    return {p[1] for p in parts if len(p) > 1 and p[0] == "aml_etl"}


def test_detects_imported_subpackages(tmp_path):
    path = tmp_path / "m.py"
    path.write_text("import aml_etl.analytics.x\nfrom aml_etl.common.y import z\nimport os\n")
    assert imported_aml_etl_subpackages(path) == {"analytics", "common"}


def test_service_subpackages_import_only_common():
    offenders = []
    for path in (ROOT / "src" / "aml_etl").rglob("*.py"):
        owner = path.relative_to(ROOT / "src" / "aml_etl").parts[0]
        for imported in imported_aml_etl_subpackages(path):
            if imported in SERVICES and imported != owner:
                offenders.append(f"{path}: {imported}")
    assert offenders == []
