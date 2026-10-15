"""Role-aware current source-package validation; no scientific execution."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile

MANIFEST = "artifact/current-project-manifest.json"
METADATA = "artifact/current-package-metadata.json"
SUPPLEMENT = "artifact/current-export-supplement.json"
EXPORT_ROOTS = ("paper", "artifact")
BIB_PATHS = ("paper/main.tex", "paper/references.bib", "paper/main.bbl")
VENDOR_PATHS = ("paper/acmart.cls", "paper/acmart.dtx", "paper/acmart.ins",
                "paper/acmart-source-v2.19.tar.gz", "paper/ACM-SOURCE-NOTICE.md")
FORBIDDEN = {".pyc", ".pyo", ".aux", ".blg", ".bbl", ".log", ".fls", ".fdb_latexmk", ".toc"}
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}
ARCHIVE_ENV = "TOPLAS19_EXPORT_ARCHIVE"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _collect_filesystem_records(root):
    """Collect every file in the two delivery roots, not project navigation."""
    root = Path(root)
    records = {}
    for name in EXPORT_ROOTS:
        directory = root / name
        require(directory.is_dir() and not directory.is_symlink(), 'export root missing or symlink: ' + name)
        for path in sorted(directory.rglob('*')):
            require(not path.is_symlink(), 'source export contains a symlink')
            if path.is_file():
                records[path.relative_to(root).as_posix()] = (path.read_bytes(), f'{path.stat().st_mode & 0o777:04o}')
    return records


def _requires_posix_modes():
    return os.name == "posix"


def collect_archive_records(archive):
    """Read regular ZIP members with explicit Unix type and permission bits."""
    records = {}
    seen = set()
    portable_names = set()
    with zipfile.ZipFile(archive) as supplied:
        for member in supplied.infolist():
            name = member.filename
            require(member.orig_filename == name and '\0' not in name,
                    'ZIP member name was truncated')
            require(name not in seen and name.casefold() not in portable_names,
                    'duplicate ZIP member: ' + name)
            seen.add(name)
            portable_names.add(name.casefold())
            require(not member.flag_bits & 1, 'encrypted ZIP member: ' + name)
            stored = member.external_attr >> 16
            if member.is_dir():
                # Existing delivery ZIPs can contain these two empty root
                # headers. They are not regular-file manifest entries.
                require(name in {root + '/' for root in EXPORT_ROOTS}
                        and member.file_size == 0 and supplied.read(member) == b''
                        and stored in (stat.S_IFDIR | 0o755, stat.S_IFDIR | 0o775),
                        'invalid ZIP root directory: ' + name)
                continue
            path = PurePosixPath(name)
            require(not path.is_absolute() and len(path.parts) >= 2
                    and path.parts[0] in EXPORT_ROOTS and '..' not in path.parts
                    and '\\' not in name and ':' not in name
                    and path.as_posix() == name and not FORBIDDEN_PARTS.intersection(path.parts),
                    'unsafe ZIP member: ' + name)
            expected = 0o755 if path.suffix == '.sh' else 0o644
            require(member.create_system == 3 and stored == (stat.S_IFREG | expected),
                    'ZIP Unix type/mode: ' + name)
            records[name] = (supplied.read(member), f'{expected:04o}')
    require(bool(records), 'empty ZIP export')
    return records


def collect_export_records(root, archive=None):
    """Check physical files, optionally bound to an actual distribution ZIP.

    On POSIX both the stored modes and physical modes are mandatory. On
    Windows ZIP mode checks attest transport metadata, not NTFS POSIX modes.
    """
    physical = _collect_filesystem_records(root)
    if archive is None:
        return physical
    stored = collect_archive_records(archive)
    require(set(stored) == set(physical), 'archive/extracted exact file inventory')
    for name, (data, mode) in stored.items():
        require(data == physical[name][0], 'archive/extracted bytes: ' + name)
        if _requires_posix_modes():
            require(mode == physical[name][1], 'physical POSIX mode: ' + name)
    return stored


def uncomment(text):
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def bibliography_keys(bbl):
    """Read actual compiled entries, including ACM's comment-newline layout."""
    return re.findall(r"\\bibitem(?:\[[\s\S]*?\])?\s*\{([^{}]+)\}", uncomment(bbl))


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
    keys = bibliography_keys(bbl.decode("utf-8"))
    source_keys = re.findall(r"(?m)^\s*@\w+\s*\{\s*([^,\s]+)\s*,", bib.decode("utf-8"))
    cited = set(re.findall(r"\\cite(?:\[[^\]]*\])?\{([^{}]+)\}", tex))
    expected = set(current["current_bib_entry_sha256"])
    require(len(keys) == len(set(keys)) > 0 and len(source_keys) == len(set(source_keys))
            and set(keys) == cited == expected and set(keys) <= set(source_keys),
            "bibliography exact compiled-key coverage")
    require(type(role["key_count"]) is int and role["key_count"] == len(keys)
            and role["keys"] == sorted(expected), "bibliography metadata keys")
    text = bbl.decode("utf-8")
    require(text.count(r"\begin{thebibliography}{" + str(len(keys)) + "}") == 1
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
    require(manifest['export_roots'] == list(EXPORT_ROOTS), 'export roots contract')
    rows = manifest["files"]
    names = [row["path"] for row in rows]
    actual = set(records) - {MANIFEST}
    require(len(names) == len(set(names)) == manifest["file_count"]
            and set(names) == actual, "exact current file inventory")
    require(manifest["root_entries"] == sorted(EXPORT_ROOTS)
            == sorted({PurePosixPath(path).parts[0] for path in records}),
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
    for path, expected in current.get("current_file_sha256", {}).items():
        require(digest(files[path]) == expected, "current byte binding: " + path)
    # Earlier mutable-ledger identities are checked against the unchanged
    # historical export manifest, never resealed to today's ledger bytes.
    archived = json.loads(files['artifact/project-manifest.json'])
    old_rows = {row['path']: row['sha256'] for row in archived['files']}
    for path, expected in current.get('prior_export_file_sha256', {}).items():
        require(old_rows.get(path) == expected, 'prior export identity: ' + path)
    validate_bibliography(files, current)
    validate_vendor(files, current)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--archive", type=Path,
                        help="Check actual ZIP Unix modes and exact agreement with the extracted --root")
    parser.add_argument("--run-checks", action="store_true",
                        help="Also run the eight full-package checks and seven export regressions")
    args = parser.parse_args()
    root = args.root.resolve()
    archive = args.archive.resolve() if args.archive is not None else None
    records = collect_export_records(root, archive)
    manifest = json.loads(records[MANIFEST][0])
    current = json.loads(records[METADATA][0])
    supplement = json.loads(records[SUPPLEMENT][0])
    require(supplement["schema"] == "CURRENT_EXPORT_SUPPLEMENT_V1"
            and supplement["current_metadata_sha256"] == digest(records[METADATA][0])
            and supplement["publisher_source_paths"] == list(BIB_PATHS + VENDOR_PATHS)
            and supplement["scheduled_checks"] == {"package": 8, "export_regressions": 7},
            "export supplement binding")
    # The exact manifest includes the supplement, metadata and validator.
    # Only the manifest itself is excluded, just as in the existing gate.
    validate_inventory(records, manifest, current)
    if args.run_checks:
        for command in ('pdfinfo', 'pdftotext'):
            require(shutil.which(command) is not None, 'PACKAGE_CHECK_DEPENDENCY_ERROR: ' + command)
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
        environment.pop(ARCHIVE_ENV, None)
        if archive is not None:
            environment[ARCHIVE_ENV] = str(archive)
        interpreter = [sys.executable, '-B']
        if sys.flags.optimize:
            interpreter.append('-' + 'O' * sys.flags.optimize)
        for arguments in (
            ['-m', 'unittest', 'tests.test_package_integrity', '-v'],
            ['-m', 'unittest', 'discover', '-s', 'regressions', '-p', 'test_current_export.py', '-v'],
        ):
            subprocess.run(interpreter + arguments, cwd=root/'artifact', env=environment, check=True)
    print(json.dumps({"scope": "current source inventory/roles only; no scientific or publication guarantee",
                      "current_files": manifest["file_count"],
                      "bibliography_keys": current["publisher_bibliography"]["key_count"],
                      "permission_basis": "ZIP Unix metadata and extracted bytes" if archive else "physical filesystem modes",
                      "physical_POSIX_modes_checked": _requires_posix_modes(),
                      "archive": str(archive) if archive else None,
                      "package_and_export_suites_executed": args.run_checks}))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
    except (ValueError, KeyError, OSError, UnicodeError, tarfile.TarError, zipfile.BadZipFile) as exc:
        raise SystemExit("CURRENT_EXPORT_CHECK_FAILED: " + str(exc))
