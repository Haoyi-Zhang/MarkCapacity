"""Role-aware current source-package validation; no scientific execution."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

MANIFEST = "artifact/current-project-manifest.json"
METADATA = "artifact/current-package-metadata.json"
SUPPLEMENT = "artifact/current-export-supplement.json"
BIB_PATHS = ("paper/main.tex", "paper/references.bib", "paper/main.bbl")
VENDOR_PATHS = ("paper/acmart.cls", "paper/acmart.dtx", "paper/acmart.ins",
                "paper/acmart-source-v2.19.tar.gz", "paper/ACM-SOURCE-NOTICE.md")
FORBIDDEN = {".pyc", ".pyo", ".aux", ".blg", ".bbl", ".log", ".fls", ".fdb_latexmk", ".toc"}
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def uncomment(text):
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def validate_bibliography(files, current):
    """Only the named, byte-bound bibliography source earns a suffix exception."""
    role = current["publisher_bibliography"]
    require(role["path"] == "paper/main.bbl", "bibliography role path")
    bbl = files["paper/main.bbl"]
    require(type(role["bytes"]) is int and role["bytes"] == len(bbl)
            and role["sha256"] == digest(bbl), "bibliography byte binding")
    main = files["paper/main.tex"]
    bib = files["paper/references.bib"]
    require(digest(main) == current["manuscript_sha256"]
            and digest(bib) == role["references_sha256"], "bibliography source binding")
    tex = uncomment(main.decode("utf-8"))
    require(re.findall(r"\\bibliography\{([^{}]+)\}", tex) == ["references"]
            and re.findall(r"\\bibliographystyle\{([^{}]+)\}", tex) == ["ACM-Reference-Format"],
            "bibliography inclusion/style")
    keys = re.findall(r"\\bibitem(?:\[[\s\S]*?\])?\s*\{([^{}]+)\}", uncomment(bbl.decode("utf-8")))
    source_keys = re.findall(r"(?m)^\s*@\w+\s*\{\s*([^,\s]+)\s*,", bib.decode("utf-8"))
    cited = set(re.findall(r"\\cite(?:\[[^\]]*\])?\{([^{}]+)\}", tex))
    expected = set(current["current_bib_entry_sha256"])
    require(len(keys) == len(set(keys)) == len(source_keys) == len(set(source_keys)) == 68
            and set(keys) == set(source_keys) == cited == expected,
            "bibliography exact 68-key coverage")
    require(type(role["key_count"]) is int and role["key_count"] == 68
            and role["keys"] == sorted(expected), "bibliography metadata keys")
    text = bbl.decode("utf-8")
    require(text.count(r"\begin{thebibliography}{68}") == 1
            and text.count(r"\end{thebibliography}") == 1
            and "ACM-Reference-Format-Journals [18-Jan-2012]" in text,
            "bibliography generated-source structure")


def validate_vendor(files, current):
    source = current["template_source"]
    require(source["release"] == "2.19" and source["date"] == "2026-06-27",
            "template source release")
    commit = "062edc8119be9067a346ce874281eab48b2c29a4"
    require(source["upstream_commit"] == commit and source["source_url"] ==
            "https://raw.githubusercontent.com/borisveytsman/acmart/" + commit + "/acmart.dtx",
            "template source authority")
    for path in VENDOR_PATHS:
        require(digest(files[path]) == source["file_sha256"][path], "template source binding: " + path)
    require(digest(files["paper/acmart.cls"]) == source["derived_class_sha256"],
            "derived class binding")
    text = files["paper/acmart.dtx"].decode("utf-8")
    require("Copyright 2016-2026, Association for Computing Machinery" in text
            and "LaTeX Project Public License" in text and "maintained" in text,
            "template original notices")
    with tarfile.open(fileobj=io.BytesIO(files["paper/acmart-source-v2.19.tar.gz"]), mode="r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == len({member.name for member in members}), "upstream duplicate entry")
        selected = {}
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts
                    and (member.isfile() or member.isdir()), "upstream unsafe entry")
            if member.isfile() and path.name in ("acmart.dtx", "acmart.ins"):
                require(path.name not in selected and member.size < 2_000_000,
                        "upstream source ambiguity")
                selected[path.name] = archive.extractfile(member).read()
        require(selected == {name: files["paper/" + name] for name in ("acmart.dtx", "acmart.ins")},
                "upstream exact source inclusion")


def validate_inventory(records, manifest, current):
    """Exact current inventory and actual permissions remain unconditional."""
    require(manifest["schema"] == "CURRENT_PROJECT_MANIFEST_V1", "current manifest schema")
    rows = manifest["files"]
    names = [row["path"] for row in rows]
    actual = set(records) - {MANIFEST}
    require(len(names) == len(set(names)) == manifest["file_count"]
            and set(names) == actual, "exact current file inventory")
    require(manifest["root_entries"] == sorted({PurePosixPath(path).parts[0] for path in records}),
            "exact root inventory")
    # Self-exclusion avoids a circular hash, not the actual permission rule.
    require(MANIFEST in records, "current manifest file missing")
    require(records[MANIFEST][1] == "0644", "actual distribution mode: " + MANIFEST)
    for row in rows:
        rel = row["path"]
        path = PurePosixPath(rel)
        require(not path.is_absolute() and ".." not in path.parts and "\\" not in rel
                and str(path) == rel and not FORBIDDEN_PARTS.intersection(path.parts), "unsafe path: " + rel)
        data, actual_mode = records[rel]
        mode = "0755" if path.suffix == ".sh" else "0644"
        require(type(row["bytes"]) is int and row["bytes"] == len(data)
                and row["sha256"] == digest(data), "file byte binding: " + rel)
        require(row["mode"] == actual_mode == mode, "actual distribution mode: " + rel)
        if rel == "artifact/results/current/scientific.log":
            require(digest(data) == current["historical_file_sha256"][rel], "retained log binding")
        elif rel != "paper/main.bbl":
            require(path.suffix not in FORBIDDEN, "forbidden debris: " + rel)
    files = {path: value[0] for path, value in records.items()}
    for path, expected in current["historical_file_sha256"].items():
        require(digest(files[path]) == expected, "historical byte binding: " + path)
    validate_bibliography(files, current)
    validate_vendor(files, current)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    root = parser.parse_args().root.resolve()
    records = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "source export contains a symlink")
        if path.is_file():
            records[path.relative_to(root).as_posix()] = (path.read_bytes(), f"{path.stat().st_mode & 0o777:04o}")
    manifest = json.loads(records[MANIFEST][0])
    current = json.loads(records[METADATA][0])
    supplement = json.loads(records[SUPPLEMENT][0])
    require(supplement["schema"] == "CURRENT_EXPORT_SUPPLEMENT_V1"
            and supplement["current_metadata_sha256"] == digest(records[METADATA][0])
            and supplement["publisher_source_paths"] == list(BIB_PATHS + VENDOR_PATHS)
            and supplement["scheduled_checks"] == {"package": 8, "export_regressions": 6},
            "export supplement binding")
    # The exact manifest includes the supplement, metadata and validator.
    # Only the manifest itself is excluded, just as in the existing gate.
    validate_inventory(records, manifest, current)
    print(json.dumps({"scope": "current source inventory/roles only; no scientific or publication guarantee",
                      "current_files": manifest["file_count"], "bibliography_keys": 68}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, UnicodeError, tarfile.TarError) as exc:
        raise SystemExit("CURRENT_EXPORT_CHECK_FAILED: " + str(exc))
