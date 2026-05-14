from pathlib import Path


def test_eitraining_does_not_import_sibling_internals() -> None:
    forbidden = (
        "from eiskills",
        "import eiskills",
        "from eidocs",
        "import eidocs",
    )
    offenders: list[str] = []
    for path in Path("eitraining").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in forbidden):
            offenders.append(str(path))
    assert offenders == []
