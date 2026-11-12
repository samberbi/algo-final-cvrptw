"""Validate current documents, source fingerprints, routes and actual test receipt."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import nbformat
import pymupdf
from docx import Document
from algo.data import load
from algo.verify import verify
from scripts.analyze_ils_v5 import analyze
from scripts.package_ils_v5 import semantic_text, EXCLUDED_WORD


def main():
    frame, summary, _ = analyze("validation")
    assert len(frame) == 72 and frame.valid.all()
    for label in ["development", "development_relay", "development_parameters", "development_partition"]:
        assert analyze(label)[0].valid.all()
    old_cases = {}
    old_runs = list((ROOT / "results/optimization_v2/validation/runs").glob("*.json"))
    assert len(old_runs) == 360
    for path in old_runs:
        record = json.loads(path.read_text(encoding="utf-8"))
        name = record["job"]["instance"]
        if name not in old_cases: old_cases[name] = load(ROOT / "data/instances" / (name + ".vrp"))
        checked = verify(record["result"]["routes"], old_cases[name])
        assert checked["valid"] and abs(checked["distance"] / 10 - record["result"]["cost"]) < 1e-7
    archive_rows = []
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    references = {r["instance"]:r["reference_distance"] for r in manifest["reference_instances"]}
    for path in sorted((ROOT / "results/optimization_v5/portfolio_intensified").glob("*_*.json")):
        record = json.loads(path.read_text())
        name = record["instance"]
        source = ROOT / "results/optimization_v5/portfolio" / path.name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == record["source_sha256"]
        pool = json.loads(source.read_text())
        assert pool["input_runs"] == len(pool["sources_sha256"]) == 16
        for relative, expected in pool["sources_sha256"].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
        checked = verify(record["result"]["routes"], old_cases[name])
        assert checked["valid"]
        distance = checked["distance"] / 10
        assert abs(distance - record["result"]["cost"]) < 1e-7
        assert distance <= pool["result"]["cost"] + 1e-7
        assert abs(record["gap_pct"] - 100 * (distance/references[name] - 1)) < 1e-7
        assert abs(pool["total_effort_s"] - pool["generation_search_s"] - pool["generation_construction_s"] - pool["result"]["runtime_s"]) < 1e-6
        assert abs(record["total_effort_s"] - pool["total_effort_s"] - record["result"]["runtime_s"]) < 1e-6
        archive_rows.append(record)
    assert len(archive_rows) == 12
    files = ["LIVRABLE_FINAL.md", "README.md", "docs/AMELIORATIONS_ILS.md",
             "notebooks/Livrable_Final_CVRPTW.ipynb", "notebooks/Livrable_Final_CVRPTW.html",
             "notebooks/Ameliorations_ILS_CVRPTW.ipynb", "notebooks/Ameliorations_ILS_CVRPTW.html",
             "livraison/RAPPORT_CVRPTW.md", "livraison/RAPPORT_CVRPTW.pdf", "livraison/RAPPORT_CVRPTW.docx",
             "livraison/RESULTATS_ILS_V5.csv", "livraison/RESULTATS_ILS_V5.html"]
    for relative in files:
        assert EXCLUDED_WORD not in semantic_text(ROOT / relative).lower(), relative
    for name in ["Livrable_Final_CVRPTW", "Ameliorations_ILS_CVRPTW"]:
        nb = nbformat.read(ROOT / "notebooks" / (name + ".ipynb"), as_version=4)
        code = [c for c in nb.cells if c.cell_type == "code"]
        assert code and all(c.execution_count is not None for c in code)
        assert not any(o.output_type == "error" for c in code for o in c.outputs)
    with pymupdf.open(ROOT / "livraison/RAPPORT_CVRPTW.pdf") as doc:
        assert all(page.get_text().strip() for page in doc)
        assert not any(w[0] < -1 or w[2] > p.rect.width + 1 for p in doc for w in p.get_text("words"))
        pages = len(doc)
    word = Document(ROOT / "livraison/RAPPORT_CVRPTW.docx")
    assert len(word.inline_shapes) >= 13
    suites = ET.parse(ROOT / "results/optimization_v5/tests.xml").getroot()
    suite = suites.find("testsuite") if suites.tag != "testsuite" else suites
    assert int(suite.attrib["failures"]) == int(suite.attrib["errors"]) == 0
    receipt = dict(complete=True, edition="ils_v5", validation_runs=len(frame), development_runs=144,
                   validation_instances=12, seeds_per_instance=2, baseline_v2_runs=360,
                   feasible=int(frame.valid.sum()), summary=summary.to_dict("records"),
                   tests=dict(suite.attrib), pdf_pages=pages,
                   archive_intensifications=12,
                   archive_mean_gap=sum(r["gap_pct"] for r in archive_rows)/12,
                   archive_mean_effort_s=sum(r["total_effort_s"] for r in archive_rows)/12,
                   semantic_scope_checked=True,
                   sha256={p:hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files})
    (ROOT / "livraison/validation_ils_v5.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    (ROOT / "livraison/VALIDATION.json").write_text(json.dumps(dict(
        edition="ils_v5", complete=True, authoritative_receipt="validation_ils_v5.json",
        validation_runs=72, development_runs=144, baseline_v2_runs=360,
        decision="../results/optimization_v5/decision.json"), indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in receipt.items() if k not in {"sha256", "summary"}}, indent=2))


if __name__ == "__main__":
    main()
