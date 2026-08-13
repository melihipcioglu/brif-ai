"""Architecture regression tests for conversation.elicitation dependency boundaries."""

import ast
from pathlib import Path


def test_elicitation_has_zero_llm_imports() -> None:
    elicitation_dir = Path(__file__).parents[3] / "src" / "brif_ai" / "conversation" / "elicitation"
    py_files = list(elicitation_dir.glob("**/*.py"))
    assert py_files, "Found no python files in conversation.elicitation package"

    forbidden = {"brif_ai.llm", "PendingProposalContext"}

    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for bad in forbidden:
                        assert bad not in alias.name, (
                            f"Forbidden import '{alias.name}' found in {py_file.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                for bad in forbidden:
                    assert bad not in module_name, (
                        f"Forbidden import from '{module_name}' found in {py_file.name}"
                    )
                for alias in node.names:
                    for bad in forbidden:
                        assert bad not in alias.name, (
                            f"Forbidden imported symbol '{alias.name}' found in {py_file.name}"
                        )
