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
SUBMISSION_PATHS = ("paper/titlepage.tex", "paper/project-repository.tex", "paper/main.pdf", "paper/titlepage.pdf")
VENDOR_PATHS = ("paper/acmart.cls", "paper/acmart.dtx", "paper/acmart.ins",
                "artifact/vendor/acmart-source.tar.gz", "paper/ACM-SOURCE-NOTICE.md")
FORBIDDEN = {".pyc", ".pyo", ".aux", ".blg", ".bbl", ".log", ".fls", ".fdb_latexmk", ".toc"}
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}
ARCHIVE_ENV = "TOPLAS19_EXPORT_ARCHIVE"
MAIN_OPTIONS = "acmsmall,screen,anonymous,nonacm"
TITLE_OPTIONS = "acmsmall,screen,nonacm"
# Existing approved identities belong to the separate title page, never main.
APPROVED_AUTHORS = ('Haoyi Zhang', 'Huaijin Ran', 'Jiongchi Yu', 'Yuqiang Sun')
APPROVED_EMAILS = ('hyeliozhang@gmail.com',
 'huaijin003@e.ntu.edu.sg',
 'jiongchiyu@acm.org',
 'yuqiang.sun@ntu.edu.sg')
APPROVED_ORCIDS = ('0009-0009-3693-786X',
 '0009-0009-2482-2344',
 '0000-0002-2888-4499',
 '0000-0003-4340-3371')
NON_DOI_CHAPTER = {"author": "Samson Abramsky", "title": "The Lazy Lambda Calculus", "booktitle": "Research Topics in Functional Programming",
                   "editor": "D. Turner", "publisher": "Addison Wesley", "year": "1990", "pages": "65--117",
                   "url": "https://www.cs.ox.ac.uk/people/samson.abramsky/lazy.pdf", "note": "Author-hosted manuscript"}


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


def literal_arguments(text, command):
    """Balanced literal TeX arguments; preserve accents and reject truncation."""
    source, values = uncomment(text), []
    for match in re.finditer(r"\\" + command + r"\{", source):
        start, depth, end = match.end(), 1, match.end()
        while end < len(source) and depth:
            if source[end] == "{" and source[end-1] != "\\": depth += 1
            elif source[end] == "}" and source[end-1] != "\\": depth -= 1
            end += 1
        require(depth == 0, "unclosed literal argument: " + command)
        values.append(source[start:end-1])
    return values


def reference_entries(text):
    """Exact brace-delimited source entries; not a DOI-resolution check."""
    result, cursor = {}, 0
    while True:
        match = re.search(r"@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,", text[cursor:])
        if match is None: return result
        start = cursor + match.start(); opening = text.index("{", start)
        depth, end = 1, opening + 1
        while end < len(text) and depth:
            if text[end] == "{" and text[end-1] != "\\": depth += 1
            elif text[end] == "}" and text[end-1] != "\\": depth -= 1
            end += 1
        require(depth == 0 and match[2] not in result, "duplicate/unclosed bibliography entry")
        result[match[2]] = text[start:end].strip(); cursor = end


def validate_reference_identities(entries):
    """One exact non-DOI chapter exception; no general missing-DOI waiver."""
    identities = []
    for key, entry in entries.items():
        kind = re.match(r"@([A-Za-z]+)", entry).group(1).lower()
        doi = re.search(r'(?im)^\s*doi\s*=\s*[{"]([^}"]+)', entry)
        if key == "abramsky1990lazy":
            require(kind == "incollection" and doi is None, "exact non-DOI chapter role")
            for field, expected in NON_DOI_CHAPTER.items():
                match = re.search(r'(?im)^\s*' + field + r'\s*=\s*\{([^}]+)\}', entry)
                require(match is not None and match[1] == expected, "exact non-DOI chapter identity: " + field)
            identities.append("bookchapter:Samson-Abramsky:1990:Research-Topics-in-Functional-Programming:65-117")
        else:
            require(kind in {"article", "inproceedings"} and doi is not None and doi[1].strip(), "DOI/type required: " + key)
            identities.append("doi:" + doi[1].strip().lower())
    require(len(identities) == len(set(identities)), "duplicate scholarly identity")


APPROVED_AUTHOR_RECORDS = [{'name': 'Haoyi Zhang',
  'email': 'hyeliozhang@gmail.com',
  'affiliation_tex': "\\institution{Xi'an Jiaotong-Liverpool "
                     'University}\\city{Suzhou}\\country{China}',
  'orcid': '0009-0009-3693-786X',
  'authornote': None},
 {'name': 'Huaijin Ran',
  'email': 'huaijin003@e.ntu.edu.sg',
  'affiliation_tex': '\\institution{Nanyang Technological '
                     'University}\\city{Singapore}\\country{Singapore}',
  'orcid': '0009-0009-2482-2344',
  'authornote': None},
 {'name': 'Jiongchi Yu',
  'email': 'jiongchiyu@acm.org',
  'affiliation_tex': '\\institution{Nanyang Technological '
                     'University}\\city{Singapore}\\country{Singapore}',
  'orcid': '0000-0002-2888-4499',
  'authornote': None},
 {'name': 'Yuqiang Sun',
  'email': 'yuqiang.sun@ntu.edu.sg',
  'affiliation_tex': '\\institution{Nanyang Technological '
                     'University}\\city{Singapore}\\country{Singapore}',
  'orcid': '0000-0003-4340-3371',
  'authornote': None}]
APPROVED_VARIANT = 'c'
AUTHORSHIP_APPROVAL_SHA256 = '0558ac8d74f7e8236e67045a6e860dbfc908eacc89d5b0b4012153ae8fc348d6'

"""Pure authorship checks injected into each clone's existing export validator.

APPROVED_AUTHOR_RECORDS, APPROVED_VARIANT and AUTHORSHIP_APPROVAL_SHA256 are
literal, per-clone constants generated from the exact main-approved source/gate.
The surrounding validator's bibliography, vendor, inventory and anonymous rules
remain in force. No external file or mutable metadata supplies the approved list.
"""


APPROVED_CORRESPONDING_AUTHOR = None
APPROVED_CORRESPONDING_NOTE = ''

def title_author_records(title):
    source = uncomment(title)
    starts = list(re.finditer(r"\\author\{", source))
    require(len(starts) == len(re.findall(r"\\author\b", source)), "approved titlepage identities: literal author blocks")
    require(not re.search(r"\\(?:authornotemark|thanks)\b", source), "approved titlepage identities: no shared/cofirst/thanks notes")
    records = []
    for i, match in enumerate(starts):
        block = source[match.start():starts[i+1].start() if i+1 < len(starts) else len(source)]
        fields = {key:literal_arguments(block, key) for key in ('author','email','affiliation','orcid','authornote')}
        for key, values in fields.items():
            require(len(values) == len(re.findall(r"\\"+key+r"\b",block)), "approved titlepage identities: literal field "+key)
        require(len(fields['author']) == len(fields['email']) == len(fields['affiliation']) == 1
                and len(fields['orcid']) <= 1 and len(fields['authornote']) <= 1,
                "approved titlepage identities: per-author field cardinality")
        note = fields['authornote'][0] if fields['authornote'] else None
        if note is not None:
            require(note == 'Corresponding author.' and re.match(
                r"\\author\{"+re.escape(fields['author'][0])+r"\}\s*\\authornote\{Corresponding author\.\}", block),
                "approved titlepage identities: single exact immediately attached note")
        records.append(dict(name=fields['author'][0], email=fields['email'][0], affiliation_tex=fields['affiliation'][0],
                            orcid=fields['orcid'][0] if fields['orcid'] else None, authornote=note))
    for command,key in (('email','email'),('affiliation','affiliation_tex'),('orcid','orcid'),('authornote','authornote')):
        require(literal_arguments(source,command) == [r[key] for r in records if r[key] is not None]
                and len(re.findall(r"\\"+command+r"\b",source)) == len(literal_arguments(source,command)),
                "approved titlepage identities: fields outside author blocks")
    require(len(re.findall(r"corresponding[ -]author",source,re.I)) == sum(r['authornote'] is not None for r in records),
            "approved titlepage identities: stray corresponding-author text")
    return records


def validate_current_authorship(title, current):
    records = title_author_records(title)
    require(records == APPROVED_AUTHOR_RECORDS, "approved titlepage identities: exact ordered records and note owner")
    require(current['current_author_records'] == APPROVED_AUTHOR_RECORDS
            and current['current_authorship_variant'] == APPROVED_VARIANT
            and current['authorship_approval_sha256'] == AUTHORSHIP_APPROVAL_SHA256,
            "approved titlepage identities: exact roster approval binding")
    for field, expected in (('authors_tex',[r['name'] for r in records]),
                            ('author_emails',[r['email'] for r in records]),
                            ('author_affiliations',[r['affiliation_tex'] for r in records]),
                            ('author_orcids',[r['orcid'] for r in records if r['orcid'] is not None])):
        require(current[field] == expected, "approved titlepage identities: "+field)
    names = [APPROVED_CORRESPONDING_AUTHOR] if APPROVED_CORRESPONDING_AUTHOR else []
    require(current['corresponding_authors'] == names
            and current['corresponding_author'] == APPROVED_CORRESPONDING_AUTHOR
            and current['corresponding_author_note_tex'] == APPROVED_CORRESPONDING_NOTE,
            "approved titlepage identities: exact current correspondence")
    document = current['current_documents']['paper/titlepage.pdf']
    for field in ('authors_tex','author_emails','author_affiliations','author_orcids',
                  'current_author_records','current_authorship_variant','authorship_approval_sha256',
                  'corresponding_authors','corresponding_author','corresponding_author_note_tex'):
        require(document[field] == current[field], "approved titlepage identities: title document "+field)


def validate_submission(files, current):
    """Check source roles and bound separate documents; not PDF visual QA."""
    main = uncomment(files["paper/main.tex"].decode("utf-8"))
    title = uncomment(files["paper/titlepage.tex"].decode("utf-8"))
    for source, expected in ((main, MAIN_OPTIONS), (title, TITLE_OPTIONS)):
        require(re.findall(r"\\documentclass\[([^\]]+)\]\{acmart\}", source) == [expected], "submission class role")
        require(not re.search(r"\\(?:linenumbers|runninglinenumbers)\b|\\usepackage(?:\[[^]]*\])?\{lineno\}", source), "submission line numbering")
        require(r"\usepackage{geometry}" not in source and r"\fancypagestyle" not in source
                and not re.search(r"\\setlength\{\\(?:textwidth|textheight|oddsidemargin|evensidemargin|topmargin)\}", source), "submission manual geometry")
        require(not re.search(r"\\acm(?:DOI|Volume|Number|Article|Year|Month)\{[^}]+\}", source), "unassigned publication metadata")
    require(current["class_options"] == MAIN_OPTIONS, "current anonymous main class")
    require(literal_arguments(main,"author") == ["Anonymous Author(s)"], "anonymous main author marker")
    for command in ("email", "orcid", "affiliation", "authornote"):
        require(not literal_arguments(main,command), "identifying main topmatter: " + command)
    require(r"\hypersetup{pdfauthor={}}" in main, "anonymous PDF author metadata clearing")
    require(not any("titlepage" in name for name in literal_arguments(main,"input")), "main inputs identifying titlepage")
    require(not re.search(r"\\(?:section|subsection)\*?\{|\\begin\{(?:abstract|theorem|proof)\}", title), "titlepage is a second manuscript")
    validate_current_authorship(title, current)
    availability = uncomment(files["paper/project-repository.tex"].decode("utf-8"))
    require(not re.search(r"https?://[^\s{}]*(?:github|gitlab)\.[^\s{}]+", main + availability, re.I), "identifying rendered repository URL")
    for identifier in APPROVED_EMAILS + APPROVED_ORCIDS:
        require(identifier not in main + availability, "identifying submission source")
    require({p for p in files if len(PurePosixPath(p).parts)==2 and p.startswith("paper/") and p.endswith(".pdf")}
            == {"paper/main.pdf","paper/titlepage.pdf"}, "exact main/titlepage PDF roles")
    documents = current["current_documents"]
    require(set(documents) == {"paper/main.pdf","paper/titlepage.pdf"}, "submission document metadata roles")
    for pdf, source, role in (("paper/main.pdf","paper/main.tex","anonymous_main"), ("paper/titlepage.pdf","paper/titlepage.tex","identifying_titlepage")):
        record = documents[pdf]
        require(record["role"] == role and record["source"] == source and record["source_sha256"] == digest(files[source])
                and record["pdf_sha256"] == digest(files[pdf]), "submission document byte/source binding")
        require(type(record["pages"]) is int and record["pages"] > 0 and record["page_size_points"] == [486,720], "native acmsmall document geometry/pages")
    require(documents["paper/titlepage.pdf"]["pages"] == 1, "separate titlepage must be one page")
    require(documents["paper/main.pdf"]["pdf_sha256"] == current["pdf_sha256"] and documents["paper/main.pdf"]["pages"] == current["pdf_pages"], "current main document linkage")


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
    database = reference_entries(bib.decode("utf-8"))
    validate_reference_identities({key:database[key] for key in keys})
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
    with tarfile.open(fileobj=io.BytesIO(files["artifact/vendor/acmart-source.tar.gz"]), mode="r:gz") as archive:
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
    validate_submission(files, current)


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
            and supplement["publisher_source_paths"] == list(BIB_PATHS + SUBMISSION_PATHS[:2] + VENDOR_PATHS)
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
