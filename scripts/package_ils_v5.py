"""Explicit assessed delivery: current source, evidence, data and documents only."""
from pathlib import Path
import hashlib
import json
import re
import zipfile
import nbformat
from docx import Document
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_WORD = "a" + "lns"


def semantic_text(path):
    if path.suffix == ".ipynb":
        nb = nbformat.read(path, as_version=4)
        return "\n".join(c.source + "\n" + "\n".join(o.get("text", "") + str(o.get("data", {}).get("text/plain", "")) for o in c.get("outputs", [])) for c in nb.cells)
    if path.suffix == ".pdf":
        with pymupdf.open(path) as doc:
            return "\n".join(p.get_text() for p in doc)
    if path.suffix == ".docx":
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
    if path.suffix in {".py", ".md", ".json", ".csv", ".html", ".txt", ".js", ".cjs", ".toml"}:
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".html":
            text = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+', '', text)
        return text
    return ""


def main():
    assert json.loads((ROOT / "livraison/VALIDATION.json").read_text())["complete"]
    files = set()
    for name in ["README.md", "LIVRABLE_FINAL.md", "cli.py", "requirements-lock.txt", "requirements-web.txt", "requirements-optimization-v5.txt", "lancer_web.bat", ".gitignore", ".gitattributes"]:
        if (ROOT / name).is_file(): files.add(ROOT / name)
    for directory in ["algo", "web", "controle", "ameliorations", "tests", "data", ".streamlit"]:
        for p in (ROOT / directory).rglob("*"):
            if p.is_file() and not any(part in {"__pycache__", ".pytest_cache"} for part in p.parts) and p.suffix not in {".pyc", ".nbc", ".nbi"}:
                files.add(p)
    for name in ["AMELIORATIONS_ILS.md", "INTERFACE_WEB.md", "GUIDE_ORAL.md", "EXIGENCES_PROJET_ET_RETOUR_PROF.md"]:
        files.add(ROOT / "docs" / name)
    for name in ["benchmark_ils_v5.py", "analyze_ils_v5.py", "build_ils_v5_delivery.py", "write_delivery_notes_v5.py", "package_ils_v5.py", "validate_ils_v5.py", "recombine_eligible_routes.py", "intensify_archive_v5.py", "export_report.py", "export_pdf.py", "submission_print.css", "download_data.py"]:
        files.add(ROOT / "scripts" / name)
    for stem in ["Livrable_Final_CVRPTW", "Ameliorations_ILS_CVRPTW"]:
        for suffix in [".ipynb", ".html"]: files.add(ROOT / "notebooks" / (stem + suffix))
    for p in (ROOT / "livraison").glob("RAPPORT_CVRPTW.*"): files.add(p)
    for name in ["RESULTATS_OPTIMISES.csv", "RESULTATS_OPTIMISES.html", "RESULTATS_ILS_V5.csv", "RESULTATS_ILS_V5.html", "VALIDATION.json", "validation_ils_v5.json", "LIRE_DABORD.md"]:
        files.add(ROOT / "livraison" / name)
    for directory in ["ils_figures", "optimization_figures", "ils_v5_figures"]:
        files.update(p for p in (ROOT / "livraison" / directory).glob("*.png"))
    # Numbered figures actually exported into the current report.
    count = json.loads((ROOT / "livraison/validation_rapport.json").read_text())["images"]
    for i in range(1, count + 1): files.add(ROOT / "livraison/figures" / f"figure_{i:02d}.png")
    for p in (ROOT / "results/optimization_v5").rglob("*"):
        if p.is_file() and ("source" not in p.relative_to(ROOT / "results/optimization_v5").parts or p.is_relative_to(ROOT / "results/optimization_v5/validation/source")) and p.suffix in {".json", ".csv", ".xml", ".txt", ".py"}:
            files.add(p)
    for name in ["flat.csv", "summary.csv", "instances.csv", "analysis.json"]:
        files.add(ROOT / "results/optimization_v2/validation" / name)
    files.update((ROOT / "results/optimization_v2/validation/runs").glob("*.json"))
    for p in files:
        assert p.is_file(), p
        assert EXCLUDED_WORD not in p.relative_to(ROOT).as_posix().lower(), p
        assert EXCLUDED_WORD not in semantic_text(p).lower(), p
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    target = Path.home() / "Downloads/ALGO_FINAL_CVRPTW_ILS_20261111.zip"
    if target.exists():
        raise FileExistsError("Existing delivery preserved; choose a new explicit archive name")
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(files): z.write(p, "ALGO FINAL/" + p.relative_to(ROOT).as_posix())
        z.writestr("ALGO FINAL/MANIFESTE_SHA256.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
    receipt = dict(path=str(target), files=len(files) + 1, bytes=target.stat().st_size,
                   sha256=hashlib.sha256(target.read_bytes()).hexdigest(), crc_valid=True,
                   assessed_scope_only=True, semantic_scan_passed=True)
    (ROOT / "livraison/ARCHIVE_ILS_V5.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
