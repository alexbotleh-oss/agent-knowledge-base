import ast
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "audit_write_contracts.py"
SPEC = importlib.util.spec_from_file_location("audit_write_contracts", SCRIPT)
audit_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_module)


def operations(source: str) -> list[tuple[int, str, str]]:
    tree = ast.parse(source)
    visitor = audit_module.MutationVisitor("fixture.py", tree)
    visitor.visit(tree)
    return visitor.hits


def test_string_replace_is_not_classified_as_filesystem_mutation():
    hits = operations(
        'def normalize(value: str):\n'
        '    return value.strip().replace("Z", "+00:00")\n'
    )
    assert hits == []


def test_path_replace_is_classified_from_path_assignment_and_derivation():
    hits = operations(
        'from pathlib import Path\n'
        'def publish(root: Path):\n'
        '    staged = root / "stage.json"\n'
        '    target = staged.with_name("final.json")\n'
        '    staged.replace(target)\n'
    )
    assert [(name, op) for _, name, op in hits] == [("publish", "replace")]


def test_os_replace_is_classified_as_filesystem_mutation():
    hits = operations(
        'import os\n'
        'def publish(source, target):\n'
        '    os.replace(source, target)\n'
    )
    assert [(name, op) for _, name, op in hits] == [("publish", "replace")]


def test_untyped_path_parameter_is_not_guessed_as_path():
    # Conservative boundary: no false claim of a filesystem write without path evidence.
    hits = operations(
        'def normalize(value):\n'
        '    return value.replace("-", "_")\n'
    )
    assert hits == []
