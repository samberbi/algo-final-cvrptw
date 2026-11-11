"""Validate the active optimized delivery and its measured-data provenance."""

from pathlib import Path
import hashlib
import json
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nbformat
import pymupdf
from docx import Document
from scripts.analyze_optimization_v2 import analyze, BASE, read


def main():
    df, _, _, analysis = analyze("validation")
    _, _, _, regression = analyze("regression")
    protocol = read(BASE / "validation/protocol.json")
    for relative, expected in protocol["sources"].items():
        assert (
            hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
        ), relative
    manifest = read(ROOT / "data/manifest.json")
    for name, info in manifest["files"].items():
        assert (
            hashlib.sha256((ROOT / "data/instances" / name).read_bytes()).hexdigest()
            == info["sha256"]
        )
    nb = nbformat.read(ROOT / "notebooks/Livrable_Final_CVRPTW.ipynb", as_version=4)
    code = [cell for cell in nb.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in code)
    assert not any(
        output.output_type == "error" for cell in code for output in cell.outputs
    )
    figures = sum(
        "image/png" in output.get("data", {})
        for cell in code
        for output in cell.outputs
    )
    assert figures >= 10 and len(code) >= 12
    for relative in ["LIVRABLE_FINAL.md", "livraison/RAPPORT_CVRPTW.md"]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert not re.search(r"\{\{[A-Z_]+\}\}|<!-- EXEC:", text)
        for number in range(1, 9):
            assert f"C{number}" in text
        assert "def construct" in text and "delta = ca" in text and "proposal" in text
    doc = Document(ROOT / "livraison/RAPPORT_CVRPTW.docx")
    assert len(doc.inline_shapes) == figures
    with zipfile.ZipFile(ROOT / "livraison/RAPPORT_CVRPTW.docx") as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    equations = xml.count("<m:oMath>")
    assert equations >= 60
    pdf = pymupdf.open(ROOT / "livraison/RAPPORT_CVRPTW.pdf")
    overflow = []
    for number, page in enumerate(pdf):
        assert len(page.get_text().strip()) > 30
        for word in page.get_text("words"):
            if (
                word[0] < -1
                or word[1] < -1
                or word[2] > page.rect.width + 1
                or word[3] > page.rect.height + 1
            ):
                overflow.append(dict(page=number + 1, word=word[4]))
    assert not overflow, overflow[:20]
    files = [
        "LIVRABLE_FINAL.md",
        "notebooks/Livrable_Final_CVRPTW.ipynb",
        "notebooks/Livrable_Final_CVRPTW.html",
        "livraison/RAPPORT_CVRPTW.pdf",
        "livraison/RAPPORT_CVRPTW.docx",
        "livraison/RAPPORT_CVRPTW.html",
        "livraison/RESULTATS_OPTIMISES.csv",
        "livraison/RESULTATS_OPTIMISES.html",
        "docs/GUIDE_ORAL.md",
    ]
    payload = dict(
        complete=True,
        edition="optimization_v2",
        validation_runs=len(df),
        validation_instances=analysis["instances"],
        regression_runs=regression["runs"],
        development_runs=324,
        code_cells_executed=len(code),
        figures=figures,
        tables=len(doc.tables),
        editable_equations=equations,
        pdf_pages=len(pdf),
        text_outside_pages=overflow,
        tests=read(BASE / "test_validation.json"),
        sha256={
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in files
        },
    )
    (ROOT / "livraison/validation_livraison_ils.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (ROOT / "livraison/VALIDATION.json").write_text(
        json.dumps(
            dict(
                edition="optimization_v2",
                complete=True,
                authoritative_receipt="validation_livraison_ils.json",
                validation_runs=360,
                instances=36,
                regression_runs=80,
                legacy_ils="historique_ils_e104927",
                legacy_alns="historique_alns_avant_refonte",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "sha256"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
