from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
BIB = ROOT / "paper" / "references.bib"
MANUSCRIPT = ROOT / "paper" / "main.tex"
PDF = ROOT / "paper" / "main.pdf"
STATEMENT_AUDIT = ROOT / "paper" / "statement_location_audit.json"
RECORDS = ROOT / "artifact" / "literature-evidence" / "records.jsonl"
CITATION_LEDGER = ROOT / "artifact" / "citation_support.csv"
CORRECTNESS_LEDGER = ROOT / "artifact" / "correctness_correspondence.csv"
CLAIM_LEDGER = ROOT / "artifact" / "claim_evidence_ledger.csv"
REFERENCE_CALIBRATION = ROOT / "artifact" / "venue-evidence" / "recent-toplas-reference-calibration.json"
CURRENT_STATE = ROOT / "CURRENT-STATE.md"
RESEARCH_PLAN = ROOT / "research-plan.md"
PAPER_README = ROOT / "paper" / "README.md"
VISUAL_QA = ROOT / "paper" / "visual_qa.json"
PROJECT_MANIFEST = ROOT / "artifact" / "project-manifest.json"
EXTERNAL_COMPARISON_AUDIT = ROOT / "artifact" / "external-comparison-audit.json"
REFERENCE_AUDIT = ROOT / "artifact" / "reference-audit-final.csv"
SUBMISSION_MAP = ROOT / "artifact" / "submission-materials-map.json"
TEMPLATE_AUDIT = ROOT / "paper" / "template_audit.json"
AUTHOR_PLAN = ROOT / "paper" / "author-plan.json"


FORMAL_ENVIRONMENTS = {"theorem", "lemma", "proposition", "corollary"}
COUNTER_ENVIRONMENTS = FORMAL_ENVIRONMENTS | {"definition", "example", "remark"}
ENVIRONMENT_NAMES = {
    "theorem": "Theorem",
    "lemma": "Lemma",
    "proposition": "Proposition",
    "corollary": "Corollary",
}


def parse_bib_entries(text: str) -> dict[str, str]:
    """Return exact BibTeX entry text, excluding surrounding blank lines."""
    entries: dict[str, str] = {}
    cursor = 0
    while True:
        start = text.find("@", cursor)
        if start < 0:
            break
        opening = text.find("{", start)
        comma = text.find(",", opening)
        if opening < 0 or comma < 0:
            raise ValueError("malformed BibTeX entry header")
        key = text[opening + 1 : comma].strip()
        depth = 0
        end = None
        for i in range(opening, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise ValueError(f"unterminated BibTeX entry {key}")
        if key in entries:
            raise ValueError(f"duplicate BibTeX key {key}")
        entries[key] = text[start:end].strip()
        cursor = end
    return entries


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_tex_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def parse_statement_locations(text: str) -> tuple[list[str], dict[str, dict[str, object]]]:
    """Derive formal statement numbers, headings, and source ranges from TeX."""
    lines = text.splitlines()
    headings: dict[str, str | None] = {
        "section": None,
        "subsection": None,
        "subsubsection": None,
    }
    section_number = 0
    theorem_counter = 0
    top_level_sections: list[str] = []
    records: dict[str, dict[str, object]] = {}

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        section_match = re.match(r"\\section\{(.+)\}$", stripped)
        if section_match:
            section_number += 1
            theorem_counter = 0
            title = section_match.group(1)
            top_level_sections.append(title)
            headings["section"] = title
            headings["subsection"] = None
            headings["subsubsection"] = None
        else:
            subsection_match = re.match(r"\\subsection\{(.+)\}$", stripped)
            if subsection_match:
                headings["subsection"] = subsection_match.group(1)
                headings["subsubsection"] = None
            else:
                subsubsection_match = re.match(r"\\subsubsection\{(.+)\}$", stripped)
                if subsubsection_match:
                    headings["subsubsection"] = subsubsection_match.group(1)

        begin_match = re.match(
            r"\\begin\{(theorem|lemma|proposition|corollary|definition|example|remark)\}"
            r"(?:\[[^\]]*\])?",
            stripped,
        )
        if not begin_match:
            i += 1
            continue

        environment = begin_match.group(1)
        theorem_counter += 1
        statement_start = i + 1
        label: str | None = None
        j = i
        while j < len(lines):
            label_match = re.search(r"\\label\{([^{}]+)\}", lines[j])
            if label_match and label is None:
                label = label_match.group(1)
            if re.search(rf"\\end\{{{environment}\}}", lines[j]):
                statement_end = j + 1
                break
            j += 1
        else:
            raise ValueError(f"unclosed {environment} environment at line {statement_start}")

        proof_start = proof_end = None
        k = j + 1
        while k < len(lines) and (
            not lines[k].strip() or lines[k].lstrip().startswith("%")
        ):
            k += 1
        if k < len(lines) and re.match(r"\\begin\{proof\}", lines[k].strip()):
            proof_start = k + 1
            ell = k
            while ell < len(lines) and not re.search(r"\\end\{proof\}", lines[ell]):
                ell += 1
            if ell >= len(lines):
                raise ValueError(f"unclosed proof after line {statement_end}")
            proof_end = ell + 1

        if environment in FORMAL_ENVIRONMENTS:
            if label is None:
                raise ValueError(f"unlabeled formal statement at line {statement_start}")
            if label in records:
                raise ValueError(f"duplicate formal label {label}")
            records[label] = {
                "environment": environment,
                "number": f"{section_number}.{theorem_counter}",
                "statement_start_line": statement_start,
                "statement_end_line": statement_end,
                "proof_start_line": proof_start,
                "proof_end_line": proof_end,
                "section": headings["section"],
                "subsection": headings["subsection"],
                "subsubsection": headings["subsubsection"],
            }
        i = j + 1

    return top_level_sections, records


class PublicPackageIntegrityTests(unittest.TestCase):
    def test_bibliography_hash_ledgers_match_exact_entries(self):
        entries = parse_bib_entries(BIB.read_text(encoding="utf-8"))
        records = {
            item["citation_key"]: item
            for item in (
                json.loads(line)
                for line in RECORDS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
        with CITATION_LEDGER.open(newline="", encoding="utf-8") as handle:
            citation_rows = {row["citation_key"]: row for row in csv.DictReader(handle)}

        self.assertEqual(set(entries), set(records))
        self.assertEqual(set(entries), set(citation_rows))
        for key, entry in entries.items():
            digest = sha256_text(entry)
            self.assertEqual(records[key]["local_bib_entry_sha256"], digest, key)
            self.assertEqual(citation_rows[key]["evidence_sha256"], digest, key)
            self.assertEqual(
                records[key].get("hash_basis"),
                "exact local BibTeX entry bytes, excluding surrounding blank lines",
                key,
            )

        # Coverage calibration and anti-padding checks are executable package invariants.
        calibration = json.loads(REFERENCE_CALIBRATION.read_text(encoding="utf-8"))
        counts = sorted(record["reference_count"] for record in calibration["records"])
        self.assertEqual(len(counts), 12)
        self.assertEqual(counts, calibration["reference_counts_sorted"])
        self.assertEqual(calibration["median"], (counts[5] + counts[6]) / 2)
        self.assertEqual(calibration["p75"], counts[8])
        self.assertEqual(calibration["numeric_reference_floor"], 62)
        self.assertGreaterEqual(len(entries), calibration["numeric_reference_floor"])
        self.assertEqual(len(entries), 68)

        dois = []
        for key, entry in entries.items():
            self.assertRegex(entry, r"^@(article|inproceedings)\{")
            match = re.search(r"(?im)^\s*doi\s*=\s*[\{\"]([^}\"]+)", entry)
            self.assertIsNotNone(match, key)
            dois.append(match.group(1).strip().lower())
        self.assertEqual(len(dois), len(set(dois)))

        comparison = json.loads(EXTERNAL_COMPARISON_AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(comparison["cited_scholarly_corpus"]["records"], 68)
        self.assertEqual(comparison["same_venue_calibration"]["records"], 12)
        self.assertEqual(comparison["broader_venue_comparison"]["records"], 23)
        self.assertGreaterEqual(comparison["frontier_watch"]["records"], 4)
        self.assertEqual(comparison["novelty_verdict"], "KEEP_WITH_CALIBRATED_CLAIMS")
        self.assertTrue(comparison["all_frontier_watch_items_compared"])
        self.assertFalse(comparison["preprints_excluded_from_bibliography"])
        self.assertTrue(comparison["preprints_status_labelled_in_bibliography"])
        self.assertEqual(comparison["frontier_watch"]["included_in_bibliography"], 4)

        # Final per-reference audit: every bibliography key has one row, exact
        # entry bytes, a local claim context, and an explicit scholarly-status
        # verdict. Frontier preprints are permitted only as status-labelled
        # related-work comparisons; no theorem or core result may depend on them.
        with REFERENCE_AUDIT.open(newline="", encoding="utf-8") as handle:
            audit_rows = {row["citation_key"]: row for row in csv.DictReader(handle)}
        self.assertEqual(set(entries), set(audit_rows))
        peer_reviewed = 0
        frontier = 0
        for key, entry in entries.items():
            row = audit_rows[key]
            self.assertEqual(row["exact_entry_sha256"], sha256_text(entry), key)
            self.assertEqual(row["metadata_match"], "TRUE", key)
            self.assertIn(row["identifier_status"], {"LIVE_UNIQUE_DOI", "LIVE_UNIQUE_ARXIV_DOI"}, key)
            self.assertEqual(row["single_citation_per_sentence"], "TRUE", key)
            self.assertGreaterEqual(int(row["citation_context_count"]), 1, key)
            self.assertTrue(row["manuscript_locations"].strip(), key)
            self.assertTrue(row["claim_support"].strip(), key)
            self.assertTrue(row["relevance_category"].strip(), key)
            self.assertTrue(row["notice_check"].strip(), key)
            self.assertIn(row["external_review_level"], {"PRIMARY_SOURCE_RECHECKED", "METADATA_RECHECKED", "ARCHIVED_SOURCE_EVIDENCE_AND_LOCAL_CONTEXT_RECHECKED"})
            self.assertNotIn("100%", row["verdict"])
            if row["scholarly_status"] == "PEER_REVIEWED_JOURNAL_OR_FORMAL_CONFERENCE_PAPER":
                peer_reviewed += 1
                self.assertEqual(row["verdict"], "PASS_PEER_REVIEWED", key)
            else:
                frontier += 1
                self.assertEqual(row["verdict"], "PASS_STATUS_LABELLED_FRONTIER", key)
                self.assertEqual(row["relevance_category"], "frontier comparison only", key)
                self.assertTrue(
                    all("Related Work" in location for location in row["manuscript_locations"].split("; ")),
                    key,
                )
        self.assertEqual((peer_reviewed, frontier), (65, 3))

    def test_citation_commands_are_single_key_and_cover_bibliography(self):
        entries = parse_bib_entries(BIB.read_text(encoding="utf-8"))
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        commands = re.findall(r"\\cite(?:\[[^\]]*\])?\{([^{}]+)\}", manuscript)
        self.assertTrue(commands)
        self.assertTrue(all("," not in command and ";" not in command for command in commands))
        cited = {command.strip() for command in commands}
        self.assertEqual(cited, set(entries))
        self.assertEqual(len(commands), 99)

        # Original-research citation shape: one key per command, no adjacent
        # piles, and at most one citation command in each prose sentence.
        adjacent = re.findall(
            r"\\cite(?:p|t)?(?:\[[^]]*\])?\{[^{}]+\}\s*[,;:]?\s*"
            r"\\cite(?:p|t)?(?:\[[^]]*\])?\{[^{}]+\}",
            manuscript,
        )
        self.assertEqual(adjacent, [])
        sentence_violations = []
        for paragraph in re.split(r"\n\s*\n", manuscript):
            sentences = re.split(
                r"(?<=[.!?])(?:[}\)]*)\s+(?=(?:[A-Z\\]))",
                paragraph,
            )
            for sentence in sentences:
                local = re.findall(
                    r"\\cite(?:p|t)?(?:\[[^]]*\])?\{[^{}]+\}", sentence
                )
                if len(local) > 1:
                    sentence_violations.append(sentence)
        self.assertEqual(sentence_violations, [])

    def test_public_summary_counts_and_final_topmatter_are_consistent(self):
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        citation_commands = re.findall(r"\\cite(?:p|t)?(?:\[[^\]]*\])?\{([^{}]+)\}", manuscript)
        formal_count = sum(
            len(re.findall(rf"\\begin\{{{environment}\}}", manuscript))
            for environment in FORMAL_ENVIRONMENTS
        )
        proof_count = len(re.findall(r"\\begin\{proof\}", manuscript))
        figure_count = len(re.findall(r"\\begin\{figure\}", manuscript))
        table_count = len(re.findall(r"\\begin\{table\}", manuscript))
        author_count = len(re.findall(r"^\\author\{(?:Haoyi Zhang|Huaijin Ran|Xunzhu Tang)\}$", manuscript, flags=re.MULTILINE))
        section_count = len(re.findall(r"^\\section\{", manuscript, flags=re.MULTILINE))

        self.assertIn(r"\documentclass[manuscript,screen,review]{acmart}", manuscript)
        self.assertNotIn("anonymous", manuscript.split(r"\documentclass",1)[1].split("\n",1)[0])
        self.assertNotIn(r"\usepackage{geometry}", manuscript)
        self.assertNotRegex(
            manuscript,
            r"\\setlength\{\\(?:textwidth|textheight|oddsidemargin|evensidemargin|topmargin)\}",
        )
        self.assertNotIn(r"\fancypagestyle", manuscript)
        self.assertNotIn(r"\acmVolume", manuscript)
        self.assertNotIn(r"\acmNumber", manuscript)
        self.assertNotIn(r"\acmArticle", manuscript)
        self.assertNotIn(r"\acmYear", manuscript)
        self.assertNotIn(r"\acmMonth", manuscript)
        self.assertNotIn(r"\acmDOI", manuscript)
        self.assertIn(r"\setcopyright{none}", manuscript)
        self.assertIn(r"\renewcommand{\footnotetextcopyrightpermission}[1]{}", manuscript)
        self.assertIn(r"\settopmatter{printfolios=true,printacmref=false}", manuscript)

        def command_text(command: list[str]) -> str:
            return subprocess.run(
                command,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout

        info = command_text(["pdfinfo", str(PDF)])
        self.assertRegex(info, r"(?m)^Pages:\s+48$")
        self.assertRegex(info, r"(?m)^Page size:\s+612 x 792 pts \(letter\)$")
        rendered = command_text(["pdftotext", "-layout", str(PDF), "-"])
        self.assertRegex(rendered, r"(?m)^1\s+Observational Capacity")
        self.assertIn("HAOYI ZHANG", rendered)
        self.assertIn("HUAIJIN RAN", rendered)
        self.assertIn("XUNZHU TANG", rendered)
        self.assertNotIn("ANONYMOUS AUTHOR(S)", rendered)
        self.assertEqual([path.name for path in (ROOT / "paper").glob("*.pdf")], ["main.pdf"])

        template_audit = json.loads(TEMPLATE_AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(template_audit["class_options"], "manuscript,screen,review")
        self.assertEqual(template_audit["pages"], 48)
        self.assertTrue(template_audit["line_numbers"])
        self.assertFalse(template_audit["manual_geometry_override"])
        self.assertEqual(template_audit["pdf_sha256"], sha256_file(PDF))

        self.assertIn(r"\renewcommand{\shortauthors}{Zhang et al.}", manuscript)
        self.assertEqual((formal_count, proof_count), (52, 52))
        self.assertEqual((figure_count, table_count), (4, 9))
        self.assertEqual((author_count, section_count), (3, 8))
        self.assertEqual(len(citation_commands), 99)
        self.assertEqual(manuscript.count(r"\affiliation{"), 3)
        self.assertEqual(manuscript.count(r"\institution{Xi'an Jiaotong-Liverpool University}"), 1)
        self.assertEqual(manuscript.count(r"\city{Suzhou}"), 1)
        self.assertEqual(manuscript.count(r"\country{China}"), 1)
        self.assertEqual(manuscript.count(r"\institution{Nanyang Technological University}"), 1)
        self.assertEqual(manuscript.count(r"\city{Singapore}"), 1)
        self.assertEqual(manuscript.count(r"\country{Singapore}"), 1)
        self.assertIn(r"\institution{University of Luxembourg}", manuscript)
        self.assertIn(r"\country{Luxembourg}", manuscript)
        self.assertIn(r"\email{hyeliozhang@gmail.com}", manuscript)
        self.assertIn(r"\email{huaijin003@e.ntu.edu.sg}", manuscript)
        self.assertIn(r"\email{realdanieltang@gmail.com}", manuscript)
        self.assertIn(r"\vskip 3\baselineskip", manuscript)

        author_plan = json.loads(AUTHOR_PLAN.read_text(encoding="utf-8"))
        self.assertEqual(author_plan["planned_author_count"], 6)
        self.assertEqual(author_plan["unnamed_slots"], [4, 5, 6])
        self.assertEqual(
            [row["name"] for row in author_plan["named_authors"]],
            ["Haoyi Zhang", "Huaijin Ran", "Xunzhu Tang"],
        )
        self.assertIsNone(author_plan["named_authors"][2]["orcid"])
        self.assertEqual(manuscript.count(r"\correspondingauthor"), 1)
        self.assertRegex(
            manuscript,
            r"\\author\{Huaijin Ran\}\n\\correspondingauthor\n\\orcid\{0009-0009-2482-2344\}",
        )
        self.assertEqual(manuscript.count(r"\orcid{"), 2)
        self.assertIn(r"\hypersetup{pdfauthor={Haoyi Zhang, Huaijin Ran, Xunzhu Tang}}", manuscript)
        self.assertNotRegex(manuscript, r"\\author\{Author [A-F]\}")
        self.assertIn("Independent mathematical and integrity tests & 61", manuscript)

        current_state = CURRENT_STATE.read_text(encoding="utf-8")
        research_plan = RESEARCH_PLAN.read_text(encoding="utf-8")
        paper_readme = PAPER_README.read_text(encoding="utf-8")
        for text in (current_state, research_plan, paper_readme):
            self.assertRegex(text, r"52 (?:formal statements|formal results)")
            self.assertRegex(text, r"(?:four|Four|4) (?:native )?vector figures")
            self.assertRegex(text, r"(?:nine|9) tables")
            self.assertRegex(text, r"68 (?:verified )?scholarly")
            self.assertRegex(text, r"99 single-key")
            self.assertRegex(text, r"61 passing")

        with CLAIM_LEDGER.open(newline="", encoding="utf-8") as handle:
            claims = {row["claim_id"]: row for row in csv.DictReader(handle)}
        self.assertIn("99 single-key", claims["C25"]["claim_text"])
        self.assertIn("citation_commands=99", claims["C25"]["raw_result"])
        self.assertIn("61_TEST_SUITE", claims["C25"]["independent_recheck_status"])

        visual = json.loads(VISUAL_QA.read_text(encoding="utf-8"))
        self.assertTrue(visual["checks"]["review_line_numbers_present"])
        submission_map = json.loads(SUBMISSION_MAP.read_text(encoding="utf-8"))
        main_rows = [row for row in submission_map["rows"] if row.get("material") == "main review PDF"]
        self.assertEqual(len(main_rows), 1)
        self.assertIn("FINAL", main_rows[0]["status"])

    def test_running_figure_is_narratively_placed_and_notation_light(self):
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        reference = manuscript.index(
            r"Figure~\ref{fig:running} gives a minimal instance in a pure integer fragment."
        )
        figure_start = manuscript.index(r"\begin{figure}[t]", reference)
        next_paragraph = manuscript.index(
            "Software-watermarking models distinguish", figure_start
        )
        figure_end = manuscript.index(r"\end{figure}", figure_start)
        figure = manuscript[figure_start:figure_end]

        self.assertNotIn(r"\pagebreak[4]", manuscript)
        self.assertLess(reference, figure_start)
        self.assertLess(figure_start, next_paragraph)
        self.assertNotIn(r"q_J", figure)
        self.assertNotIn(r"\Acc_R", figure)
        self.assertNotIn(r"[p]_{\approx}", figure)
        self.assertNotIn(r"J_{\mathsf", figure)
        self.assertNotIn(r"\delta", figure)
        self.assertIn("left-order cell", figure)
        self.assertIn("right-order cell", figure)
        self.assertIn("every source reaches both cells", figure)
        self.assertIn("one fixed message", figure)
        self.assertIn("pure integer fragment", figure)
        self.assertIn(r"p^{\mathsf s}", figure)
        self.assertIn(r"p^{\mathsf l}", figure)

    def test_project_manifest_covers_exact_public_tree_and_excludes_debris(self):
        manifest = json.loads(PROJECT_MANIFEST.read_text(encoding="utf-8"))
        listed = {row["path"]: row for row in manifest["files"]}
        actual_paths = {
            str(path.relative_to(ROOT))
            for path in ROOT.rglob("*")
            if path.is_file() and path != PROJECT_MANIFEST
        }
        self.assertEqual(set(listed), actual_paths)
        self.assertEqual(manifest["file_count"], len(actual_paths))
        self.assertEqual(
            manifest["root_entries"],
            ["paper", "artifact", "research-plan.md", "CURRENT-STATE.md"],
        )
        forbidden_parts = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}
        forbidden_suffixes = {".pyc", ".pyo", ".aux", ".blg", ".bbl", ".log", ".fls", ".fdb_latexmk", ".toc"}
        for rel, row in listed.items():
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            self.assertFalse(forbidden_parts.intersection(path.parts), rel)
            self.assertNotIn(path.suffix, forbidden_suffixes, rel)
            self.assertEqual(row["bytes"], path.stat().st_size, rel)
            self.assertEqual(row["sha256"], sha256_file(path), rel)
            self.assertEqual(row["mode"], f"{path.stat().st_mode & 0o777:04o}", rel)

    def test_formal_statement_labels_match_correctness_ledger(self):
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        begin_pattern = re.compile(
            r"\\begin\{(theorem|lemma|proposition|corollary)\}"
        )
        labeled_begin_pattern = re.compile(
            r"\\begin\{(theorem|lemma|proposition|corollary)\}"
            r"(?:\[[^\]]*\])?\s*\\label\{([^{}]+)\}"
        )

        begins = begin_pattern.findall(manuscript)
        matches = labeled_begin_pattern.findall(manuscript)
        self.assertTrue(begins)
        self.assertEqual(len(matches), len(begins))
        labels = [label for _environment, label in matches]
        self.assertEqual(len(labels), len(set(labels)))

        with CORRECTNESS_LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        statement_ids = [row["statement_id"] for row in rows]
        self.assertEqual(len(statement_ids), len(set(statement_ids)))
        self.assertEqual(set(labels), set(statement_ids))

    def test_manuscript_structure_and_statement_location_audit(self):
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        top_sections, source_records = parse_statement_locations(manuscript)
        audit = json.loads(STATEMENT_AUDIT.read_text(encoding="utf-8"))
        audit_records = {entry["statement_id"]: entry for entry in audit["entries"]}

        self.assertEqual(len(top_sections), 8)
        self.assertEqual(audit["top_level_section_count"], 8)
        self.assertEqual(len(re.findall(r"^\\author\{(?:Haoyi Zhang|Huaijin Ran|Xunzhu Tang)\}$", manuscript, flags=re.MULTILINE)), 3)
        self.assertEqual(audit["top_level_sections"], top_sections)
        self.assertNotRegex(manuscript, r"\\appendix\b")
        self.assertNotRegex(manuscript, r"\bAppendix\b")
        self.assertEqual(audit["manuscript_sha256"], sha256_file(MANUSCRIPT))
        self.assertEqual(audit["pdf_sha256"], sha256_file(PDF))
        self.assertEqual(audit["formal_statement_count"], 52)
        self.assertEqual(set(audit_records), set(source_records))
        self.assertTrue(all(record["proof_start_line"] is not None for record in source_records.values()))
        self.assertTrue(all(record["proof_end_line"] is not None for record in source_records.values()))

        comparable_fields = {
            "environment",
            "number",
            "statement_start_line",
            "statement_end_line",
            "proof_start_line",
            "proof_end_line",
            "section",
            "subsection",
            "subsubsection",
        }
        for statement_id, source_record in source_records.items():
            audited = audit_records[statement_id]
            for field in comparable_fields:
                self.assertEqual(audited[field], source_record[field], f"{statement_id}:{field}")

    def test_ledgers_match_statement_location_audit(self):
        audit = json.loads(STATEMENT_AUDIT.read_text(encoding="utf-8"))
        audit_records = {entry["statement_id"]: entry for entry in audit["entries"]}

        with CORRECTNESS_LEDGER.open(newline="", encoding="utf-8") as handle:
            correctness_rows = list(csv.DictReader(handle))
        self.assertEqual({row["statement_id"] for row in correctness_rows}, set(audit_records))
        for row in correctness_rows:
            entry = audit_records[row["statement_id"]]
            self.assertIn(
                f"main.tex lines {entry['statement_start_line']}-{entry['statement_end_line']}",
                row["paper_location"],
            )
            self.assertIn(
                f"statement {entry['number']}, PDF p. {entry['pdf_page']}",
                row["paper_location"],
            )
            if entry["proof_start_line"] is not None:
                self.assertEqual(
                    row["proof_location"],
                    f"main.tex lines {entry['proof_start_line']}-{entry['proof_end_line']}",
                )

        with CLAIM_LEDGER.open(newline="", encoding="utf-8") as handle:
            claim_rows = list(csv.DictReader(handle))
        for row in claim_rows:
            references = [part.strip() for part in row["theorem_or_lemma"].split(";")]
            for statement_id in references:
                if statement_id not in audit_records:
                    continue
                entry = audit_records[statement_id]
                display = ENVIRONMENT_NAMES[entry["environment"]]
                self.assertIn(
                    f"{display} {entry['number']} (PDF p. {entry['pdf_page']})",
                    row["paper_location"],
                    row["claim_id"],
                )


if __name__ == "__main__":
    unittest.main()
