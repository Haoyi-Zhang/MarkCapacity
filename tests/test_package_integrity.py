from __future__ import annotations

import csv
import hashlib
import json
import os
import ast
import re
import subprocess
import sys
from pathlib import Path
import unittest
from collections import Counter


ROOT = Path(__file__).resolve().parents[2]
BIB = ROOT / "paper" / "references.bib"
MANUSCRIPT = ROOT / "paper" / "main.tex"
PDF = ROOT / "paper" / "main.pdf"
STATEMENT_AUDIT = ROOT / "artifact" / "paper_support" / "statement_location_audit.json"
RECORDS = ROOT / "artifact" / "literature-evidence" / "records.jsonl"
CITATION_LEDGER = ROOT / "artifact" / "citation_support.csv"
CORRECTNESS_LEDGER = ROOT / "artifact" / "correctness_correspondence.csv"
CLAIM_LEDGER = ROOT / "artifact" / "claim_evidence_ledger.csv"
REFERENCE_CALIBRATION = ROOT / "artifact" / "venue-evidence" / "recent-toplas-reference-calibration.json"
CURRENT_STATE = ROOT / "paper" / "provenance" / "CURRENT-STATE.md"
RESEARCH_PLAN = ROOT / "paper" / "provenance" / "research-plan.md"
PAPER_README = ROOT / "paper" / "README.md"
VISUAL_QA = ROOT / "artifact" / "paper_support" / "visual_qa.json"
PROJECT_MANIFEST = ROOT / "artifact" / "project-manifest.json"
CURRENT_MANIFEST = ROOT / "artifact" / "current-project-manifest.json"
CURRENT_PACKAGE = ROOT / "artifact" / "current-package-metadata.json"
CURRENT_STATEMENTS = ROOT / "artifact" / "paper_support" / "current-statement-locations.json"
EXTERNAL_COMPARISON_AUDIT = ROOT / "artifact" / "external-comparison-audit.json"
REFERENCE_AUDIT = ROOT / "artifact" / "reference-audit-final.csv"
SUBMISSION_MAP = ROOT / "artifact" / "submission-materials-map.json"
TEMPLATE_AUDIT = ROOT / "artifact" / "paper_support" / "template_audit.json"
ARTIFACT_README = ROOT / "artifact" / "README.md"
SCIENTIFIC_RUNNER = ROOT / "artifact" / "run-tests.sh"
PACKAGE_RUNNER = ROOT / "artifact" / "run-package-checks.sh"
ALL_RUNNER = ROOT / "artifact" / "run-all-checks.sh"
CODE_QUALITY_AUDIT = ROOT / "artifact" / "code-quality-audit.json"
REPRODUCTION_REPORT = ROOT / "artifact" / "reproduction-report.json"

sys.path.insert(0, str(ROOT / "artifact"))
from current_export import (BIB_PATHS, VENDOR_PATHS, SUBMISSION_PATHS, EXPORT_ROOTS, ARCHIVE_ENV, collect_export_records,
                            validate_bibliography, validate_vendor, validate_submission, validate_reference_identities, bibliography_keys)


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
    appendix = False
    theorem_counter = 0
    top_level_sections: list[str] = []
    records: dict[str, dict[str, object]] = {}

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == r"\appendix":
            appendix = True
            section_number = 0
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
                "number": f"{chr(64 + section_number) if appendix else section_number}.{theorem_counter}",
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


def tex_command_arguments(text, command):
    """Read balanced literal groups, including nested TeX accents in authors."""
    values = []
    for match in re.finditer(r"\\" + command + r"\{", text):
        start = match.end()
        depth = 1
        i = start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        if depth:
            raise ValueError("unclosed " + command)
        values.append(text[start:i - 1])
    return values


def formal_aliases(text):
    """Consolidated statements keep their old labels as checked aliases."""
    aliases, seen = {}, set()
    pattern = (r"\\begin\{(?:theorem|lemma|proposition|corollary)\}(?:\[[^\]]*\])?\s*"
               r"((?:\\label\{[^{}]+\}\s*)+)")
    for match in re.finditer(pattern, text):
        labels = re.findall(r"\\label\{([^{}]+)\}", match[1])
        if any(label in seen for label in labels) or len(labels) != len(set(labels)):
            raise ValueError("duplicate formal primary/alias label")
        seen.update(labels)
        aliases.update({label:labels[0] for label in labels[1:]})
    return aliases


class PublicPackageIntegrityTests(unittest.TestCase):
    def test_bibliography_hash_ledgers_match_exact_entries(self):
        database = parse_bib_entries(BIB.read_text(encoding="utf-8"))
        rendered_keys = bibliography_keys((ROOT / "paper/main.bbl").read_text(encoding="utf-8"))
        self.assertEqual(len(rendered_keys), len(set(rendered_keys)))
        self.assertTrue(set(rendered_keys) <= set(database))
        entries = {key: database[key] for key in rendered_keys}
        current = json.loads(CURRENT_PACKAGE.read_text(encoding="utf-8"))
        self.assertEqual(set(entries), set(current["current_bib_entry_sha256"]))
        records = {
            item["citation_key"]: item
            for item in (
                json.loads(line)
                for line in RECORDS.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
        with CITATION_LEDGER.open(newline="", encoding="utf-8") as handle:
            citation_list=list(csv.DictReader(handle))
        citation_rows = {row["citation_key"]: row for row in citation_list}
        self.assertEqual(len(citation_list),70)

        self.assertEqual(set(entries), set(records))
        self.assertEqual(set(entries), set(citation_rows))
        for key, entry in entries.items():
            digest = sha256_text(entry)
            self.assertEqual(current["current_bib_entry_sha256"][key], digest, key)
            # Active rows bind active bytes; original identities/classification
            # remain separately nested and protected, never silently renamed.
            self.assertEqual(citation_rows[key]["evidence_sha256"], records[key]["local_bib_entry_sha256"], key)
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
        self.assertEqual(len(entries), 70)
        # Preserve the old68identities, including the two replaced works; do not
        # silently rename/reseal their historical hashes to the new originals.
        self.assertEqual(set(current["historical_bib_entry_sha256"]),
            (set(entries) - {"hamming1950", "francis2021domatic", "abramsky1990lazy", "sangiorgi2007environmental"})
            | {"abramsky1993", "sangiorgi2011"})

        validate_reference_identities(entries)
        dois = []
        for key, entry in entries.items():
            if key == "abramsky1990lazy":
                self.assertTrue(entry.startswith("@incollection{"))
                self.assertNotRegex(entry, r"(?im)^\s*doi\s*=")
                continue
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

        # Current70rows carry exact current hashes and bounded body receipts.
        # Dated identities/classifications live in nested historical records;
        # no old live-DOI/full-corpus verdict is inherited by the current claim.
        with REFERENCE_AUDIT.open(newline="", encoding="utf-8") as handle:
            audit_list=list(csv.DictReader(handle))
        audit_rows={row['citation_key']:row for row in audit_list}
        self.assertEqual(len(audit_list),70)
        self.assertEqual(set(entries),set(audit_rows))
        self.assertEqual(len([l for l in RECORDS.read_text(encoding='utf-8').splitlines() if l.strip()]),70)
        self.assertRegex(current['source_support_ledger_sha256'],r'^[0-9a-f]{64}$')
        self.assertRegex(current['current_census_sha256'],r'^[0-9a-f]{64}$')
        status='BOUND_ORIGINAL_BODY_READING_CURRENT_CLAUSES_ONLY'
        expected_contexts=[]
        for key,entry in entries.items():
            row,record,citation=audit_rows[key],records[key],citation_rows[key]
            body=record['current_source_support']
            self.assertEqual(row['exact_entry_sha256'],sha256_text(entry),key)
            self.assertEqual(record['local_bib_entry_sha256'],sha256_text(entry),key)
            self.assertEqual(citation['evidence_sha256'],sha256_text(entry),key)
            kind=re.match(r'@([A-Za-z]+)',entry)[1].upper()
            self.assertEqual(row['scholarly_status'],'DECLARED_DOCUMENT_TYPE_'+kind)
            self.assertEqual(row['metadata_match'],'BOUND_TO_APPROVED_CURRENT_BIB_ENTRY')
            self.assertEqual(row['identifier_status'],'APPROVED_NON_DOI_BOOK_CHAPTER_IDENTITY' if key=='abramsky1990lazy' else 'EXACT_DECLARED_DOI_IDENTITY')
            self.assertEqual(row['single_citation_per_sentence'],'CHECKED_CURRENT_SINGLE_KEY_SURFACE')
            self.assertEqual(row['verdict'],'CURRENT_CLAUSES_BODY_SUPPORTED')
            self.assertEqual(row['external_review_level'],status)
            self.assertEqual(record['verification_status'],status)
            self.assertEqual(citation['verification_status'],status)
            self.assertIs(body['closed_current_claims'],True)
            self.assertTrue(body['primary_url'])
            self.assertTrue(body['version'])
            self.assertTrue(body['actual_inspected_section_page'])
            self.assertNotRegex(body['source_text_kind'].lower(),r'abstract_only|metadata_only|identity_only|not_obtained|uninspected')
            self.assertEqual(citation['source_locator'],body['primary_url'])
            self.assertEqual(citation['source_version'],body['version'])
            self.assertEqual(citation['actual_body_locator'],json.dumps(body['actual_inspected_section_page'],ensure_ascii=False))
            self.assertEqual(row['actual_body_locator'],citation['actual_body_locator'])
            self.assertEqual(row['source_version'],body['version'])
            self.assertEqual(record['source_support_ledger_sha256'],current['source_support_ledger_sha256'])
            self.assertEqual(citation['source_support_ledger_sha256'],current['source_support_ledger_sha256'])
            positions,clauses=body['citation_positions'],body['current_attributed_claims']
            self.assertTrue(positions)
            self.assertEqual(len(positions),len(clauses))
            self.assertEqual(int(row['citation_context_count']),len(positions))
            self.assertEqual(record['local_citation_context_count'],len(positions))
            self.assertEqual(row['manuscript_locations'],citation['manuscript_location'])
            self.assertTrue(row['claim_support'].strip())
            self.assertTrue(row['relevance_category'].strip())
            self.assertIn('NOT_A_COMPLETE_NOTICE_SEARCH',row['notice_check'])
            for pos,clause in zip(positions,clauses):
                self.assertEqual(sha256_text(pos['paragraph']),pos['paragraph_sha256'])
                actual=(ROOT/pos['file']).read_text(encoding='utf-8').replace('\r\n','\n')
                self.assertIn(pos['paragraph'],actual)
                expected_contexts.append((key,pos['file'],int(pos['line']),pos['paragraph_sha256'],clause))
            historical=record['historical_record']
            if key in {'abramsky1990lazy','sangiorgi2007environmental'}:
                self.assertIsNone(historical)
                self.assertEqual(citation['historical_evidence_sha256'],'')
            else:
                self.assertEqual(historical['citation_key'],key)
                self.assertEqual(citation['historical_evidence_sha256'],historical['local_bib_entry_sha256'])
                if key in current['historical_bib_entry_sha256']:
                    self.assertEqual(historical['local_bib_entry_sha256'],current['historical_bib_entry_sha256'][key])
        self.assertIs(current['current_claim_support_complete'],True)
        retired=current['historical_retired_reference_records']
        self.assertEqual(set(retired),{'abramsky1993','sangiorgi2011'})
        for key,item in retired.items():
            self.assertIs(item['old_original_body_not_newly_closed'],True)
            self.assertEqual(item['historical_record']['citation_key'],key)
            self.assertEqual(item['historical_record']['local_bib_entry_sha256'],current['historical_bib_entry_sha256'][key])
        # These are explicitly historical, not today's source-body verdicts.
        for key,old_status in {'hamming1950':'PRIMARY_PUBLISHER_METADATA_ONLY_FULLTEXT_NOT_READ',
                              'francis2021domatic':'PRIMARY_RECORD_AND_COROLLARY_4_1_CONTEXT_READ_NOT_WHOLE_ARTICLE'}.items():
            self.assertEqual(records[key]['historical_record']['verification_status'],old_status)
            self.assertIn('NOT_A_COMPLETE_NOTICE',records[key]['historical_record']['notice_check'])
        with (ROOT/'artifact/citation-contexts.csv').open(newline='',encoding='utf-8') as handle:
            contexts=list(csv.DictReader(handle))
        self.assertEqual(len(contexts),105)
        self.assertEqual([int(r['occurrence']) for r in contexts],list(range(1,106)))
        self.assertEqual(Counter((r['citation_key'],r['source_file'],int(r['source_line']),r['paragraph_sha256'],r['sentence_tex']) for r in contexts),
                         Counter(expected_contexts))
        for row in contexts:
            source=(ROOT/row['source_file']).read_text(encoding='utf-8').replace('\r\n','\n')
            cleaned=re.sub(r'(?<!\\)%[^\n]*',lambda m:' '*len(m[0]),source)
            offset=int(row['source_character_offset'])
            self.assertGreaterEqual(offset,0)
            self.assertRegex(cleaned[offset:],r'^\\cite(?:p|t)?(?:\[[^\]]*\])?\{'+re.escape(row['citation_key'])+r'\}')
            self.assertEqual(cleaned[:offset].count('\n')+1,int(row['source_line']))
            self.assertEqual(row['source_sha256'],sha256_file(ROOT/row['source_file']))
            self.assertEqual(row['external_review_level'],status)
            self.assertEqual(row['local_verdict'],'CURRENT_CLAUSE_BODY_SUPPORTED')

    def test_citation_commands_are_single_key_and_cover_bibliography(self):
        entries = parse_bib_entries(BIB.read_text(encoding="utf-8"))
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        commands = re.findall(r"\\cite(?:\[[^\]]*\])?\{([^{}]+)\}", manuscript)
        self.assertTrue(commands)
        self.assertTrue(all("," not in command and ";" not in command for command in commands))
        cited = {command.strip() for command in commands}
        self.assertEqual(cited, set(bibliography_keys((ROOT / "paper/main.bbl").read_text(encoding="utf-8"))))
        self.assertTrue(cited <= set(entries))
        self.assertEqual(len(commands), 105)

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
        current = json.loads(CURRENT_PACKAGE.read_text(encoding="utf-8"))
        self.assertEqual(current["schema"], "CURRENT_PACKAGE_METADATA_V1")
        self.assertEqual(current["scheduled_tests"], {"scientific": 92, "package": 8, "combined": 100})
        for rel, digest in current["historical_file_sha256"].items():
            self.assertEqual(sha256_file(ROOT / rel), digest, rel)
        for rel, digest in current["current_file_sha256"].items():
            self.assertEqual(sha256_file(ROOT / rel), digest, rel)
        mutable_ledgers = {'artifact/claim_evidence_ledger.csv', 'artifact/correctness_correspondence.csv',
                           'artifact/literature-evidence/records.jsonl', 'artifact/citation_support.csv',
                           'artifact/reference-audit-final.csv'}
        self.assertEqual(set(current['current_file_sha256']), mutable_ledgers | {
            'artifact/citation-contexts.csv','artifact/paper_support/current-statement-locations.json',
            'artifact/paper_support/current-structural-contract.json'})
        self.assertEqual(set(current['prior_export_file_sha256']), mutable_ledgers)
        old_rows = {row['path']: row['sha256'] for row in
                    json.loads(PROJECT_MANIFEST.read_text(encoding='utf-8'))['files']}
        for rel, digest in current['prior_export_file_sha256'].items():
            self.assertEqual(old_rows[rel], digest, rel)
        discovered = []
        for name in current["scientific_modules"]:
            module = ast.parse((ROOT / "artifact/tests" / (name + ".py")).read_text(encoding="utf-8"))
            discovered.extend((name, node.name, method.name)
                              for node in module.body if isinstance(node, ast.ClassDef)
                              for method in node.body if isinstance(method, ast.FunctionDef)
                              and method.name.startswith("test_"))
        self.assertEqual(len(discovered), current["scheduled_tests"]["scientific"])
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        citation_commands = re.findall(r"\\cite(?:p|t)?(?:\[[^\]]*\])?\{([^{}]+)\}", manuscript)
        formal_count = sum(
            len(re.findall(rf"\\begin\{{{environment}\}}", manuscript))
            for environment in FORMAL_ENVIRONMENTS
        )
        proof_count = len(re.findall(r"\\begin\{proof\}", manuscript))
        figure_count = len(re.findall(r"\\begin\{figure\}", manuscript))
        table_count = len(re.findall(r"\\begin\{table\}", manuscript))
        author_count = len(tex_command_arguments(manuscript, "author"))
        section_count = len(re.findall(r"^\\section\{", manuscript, flags=re.MULTILINE))

        self.assertEqual(current["class_options"], "acmsmall,screen,anonymous,nonacm")
        self.assertIn(r"\documentclass[acmsmall,screen,anonymous,nonacm]{acmart}", manuscript)
        self.assertNotRegex(manuscript, r"\\(?:linenumbers|runninglinenumbers)\b")
        validate_submission({rel:(ROOT/rel).read_bytes() for rel in BIB_PATHS+SUBMISSION_PATHS},current)
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
        self.assertEqual(tex_command_arguments(manuscript,"acmDOI"),[""])
        self.assertIn(r"\setcopyright{none}", manuscript)
        self.assertIn(r"\renewcommand{\footnotetextcopyrightpermission}[1]{}", manuscript)
        self.assertIn(r"\settopmatter{printfolios=true,printacmref=false}", manuscript)

        def command_text(command: list[str]) -> str:
            return subprocess.run(
                command,
                check=True,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout

        info = command_text(["pdfinfo", "-enc", "UTF-8", "-isodates", str(PDF)])
        self.assertGreater(current["pdf_pages"], 0)
        self.assertRegex(info, rf"(?m)^Pages:\s+{current['pdf_pages']}$")
        self.assertEqual(current["page_size_points"], [486, 720])
        self.assertRegex(info, r"(?m)^Page size:\s+486 x 720 pts")
        self.assertEqual(current["pdf_sha256"], sha256_file(PDF))
        self.assertEqual(current["manuscript_sha256"], sha256_file(MANUSCRIPT))
        rendered = command_text(["pdftotext", "-enc", "UTF-8", "-layout", str(PDF), "-"])
        self.assertIn("Observational Capacity", rendered)
        self.assertIn("anonymousauthor(s)",re.sub(r"\s+","",rendered).lower())
        author_info=re.search(r"(?m)^Author:[ \t]*([^\r\n]*)",info)
        self.assertTrue(author_info is None or author_info[1].strip()=="", "anonymous PDF author metadata")
        self.assertEqual(sorted(path.name for path in (ROOT / "paper").glob("*.pdf")), ["main.pdf","titlepage.pdf"])
        titlepage=(ROOT/'paper/titlepage.tex').read_text(encoding='utf-8')
        title_info=command_text(["pdfinfo","-enc","UTF-8",str(ROOT/'paper/titlepage.pdf')])
        self.assertRegex(title_info,r"(?m)^Pages:\s+1$")
        self.assertRegex(title_info,r"(?m)^Page size:\s+486 x 720 pts")
        for identifier in current['author_emails']+current['author_orcids']:
            self.assertNotIn(identifier,rendered)

        template_audit = json.loads(TEMPLATE_AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(template_audit["class_options"], "manuscript,screen,review")
        self.assertEqual(template_audit["pages"], 48)
        self.assertTrue(template_audit["line_numbers"])
        self.assertFalse(template_audit["manual_geometry_override"])
        historical_manifest = json.loads(PROJECT_MANIFEST.read_text(encoding="utf-8"))
        historical_rows = {row["path"]: row for row in historical_manifest["files"]}
        self.assertEqual(template_audit["pdf_sha256"], historical_rows["paper/main.pdf"]["sha256"])

        self.assertNotIn(r"\renewcommand{\shortauthors}{Zhang et al.}", manuscript)
        self.assertIn(r"\renewcommand{\shortauthors}{Zhang et al.}",titlepage)
        self.assertEqual((formal_count, proof_count), (52, 52))
        self.assertEqual((figure_count, table_count), (4, 10))
        self.assertEqual((author_count, section_count), (1, 9))
        self.assertEqual(len(re.findall(r"^\\section\{", manuscript.split(r"\appendix")[0], flags=re.MULTILINE)), 8)
        self.assertEqual(len(citation_commands), 105)
        self.assertEqual(tex_command_arguments(manuscript,"author"),["Anonymous Author(s)"])
        self.assertEqual(manuscript.count(r"\affiliation{"), 0)
        self.assertEqual(titlepage.count(r"\affiliation{"), 5)
        self.assertEqual(titlepage.count(r"\authornote{Corresponding author:"), 1)
        self.assertEqual(titlepage.count(r"\orcid{"), 5)
        self.assertEqual(
            re.findall(r"\\orcid\{([^{}]+)\}", titlepage),
            ["0009-0009-3693-786X", "0009-0009-2482-2344", "0000-0002-6377-0884",
             "0000-0002-4462-6916", "0000-0001-7270-9869"],
        )
        self.assertEqual(tex_command_arguments(titlepage, "author"), current["authors_tex"])
        self.assertEqual(tex_command_arguments(titlepage, "email"), current["author_emails"])
        self.assertEqual(tex_command_arguments(titlepage, "authornote"),
                         [current["corresponding_author_note_tex"]])
        self.assertNotRegex(manuscript, r"\\author\{Author [A-F]\}")
        self.assertIn("Retained scientific test baseline & 65", manuscript)
        self.assertIn("Full-project integrity tests & 8", manuscript)

        # The following records describe the retained historical 56/64 suite;
        # current-source counts are checked separately below.
        current_state = CURRENT_STATE.read_text(encoding="utf-8")
        research_plan = RESEARCH_PLAN.read_text(encoding="utf-8")
        paper_readme = PAPER_README.read_text(encoding="utf-8")
        for text in (current_state, research_plan):
            self.assertRegex(text, r"52 (?:formal statements|formal results)")
            self.assertRegex(text, r"(?:four|Four|4) (?:native )?vector figures")
            self.assertRegex(text, r"(?:nine|9) tables")
            self.assertRegex(text, r"68 (?:verified )?scholarly")
            self.assertRegex(text, r"99 single-key")
            self.assertRegex(text, r"56 (?:passing )?scientific")
            self.assertRegex(text, r"8 (?:passing )?package(?:-integrity)?")
            self.assertRegex(text, r"64 (?:checks|total)")
        self.assertIn("92 scientific", paper_readme)
        self.assertIn("combined schedule is 100", paper_readme)

        with CLAIM_LEDGER.open(newline="", encoding="utf-8") as handle:
            claims = {row["claim_id"]: row for row in csv.DictReader(handle)}
        self.assertIn("105 single-key", claims["C25"]["claim_text"])
        self.assertIn("citation_commands=105", claims["C25"]["raw_result"])
        self.assertIn("do not certify entire article fulltexts", claims["C25"]["limitations"])

        visual = json.loads(VISUAL_QA.read_text(encoding="utf-8"))
        self.assertTrue(visual["checks"]["review_line_numbers_present"])
        submission_map = json.loads(SUBMISSION_MAP.read_text(encoding="utf-8"))
        main_rows = [row for row in submission_map["rows"] if row.get("material") == "main review PDF"]
        self.assertEqual(len(main_rows), 1)
        self.assertEqual(submission_map['status'], 'CURRENT_DOCUMENTS_SOURCE_BOUND')
        self.assertEqual(main_rows[0]['status'], 'CURRENT_DOCUMENT_SOURCE_BOUND')
        self.assertEqual(main_rows[0]['path'], 'paper/main.pdf')
        self.assertEqual(main_rows[0]['pdf_sha256'], sha256_file(PDF))
        self.assertEqual(main_rows[0]['source_sha256'], sha256_file(MANUSCRIPT))
        self.assertEqual(main_rows[0]['pages'], current['current_documents']['paper/main.pdf']['pages'])
        title_rows=[r for r in submission_map['rows'] if r['material']=='separate identifying title page']
        self.assertEqual(len(title_rows),1)
        self.assertEqual(title_rows[0]['status'],'CURRENT_DOCUMENT_SOURCE_BOUND')
        self.assertEqual(title_rows[0]['pdf_sha256'],sha256_file(ROOT/'paper/titlepage.pdf'))
        self.assertEqual(title_rows[0]['source_sha256'],sha256_file(ROOT/'paper/titlepage.tex'))
        self.assertEqual(title_rows[0]['pages'],1)

        # The independent scientific entry is genuinely self-contained.  Full
        # package checks are separate and declare both their project-root and
        # Poppler dependencies.
        scientific_runner = SCIENTIFIC_RUNNER.read_text(encoding="utf-8")
        package_runner = PACKAGE_RUNNER.read_text(encoding="utf-8")
        all_runner = ALL_RUNNER.read_text(encoding="utf-8")
        artifact_readme = ARTIFACT_README.read_text(encoding="utf-8")
        self.assertNotIn("test_package_integrity", scientific_runner)
        self.assertNotIn("pdfinfo", scientific_runner)
        self.assertNotIn("pdftotext", scientific_runner)
        self.assertIn("tests.test_woc tests.test_witness_boundaries", scientific_runner)
        self.assertIn("tests.test_package_integrity", package_runner)
        self.assertIn("TOPLAS19_PROJECT_ROOT", package_runner)
        self.assertIn("pdfinfo pdftotext", package_runner)
        self.assertIn("PACKAGE_CHECK_INPUT_ERROR", package_runner)
        self.assertIn("PACKAGE_CHECK_DEPENDENCY_ERROR", package_runner)
        self.assertIn("./run-tests.sh", all_runner)
        self.assertIn("./run-package-checks.sh", all_runner)
        self.assertIn("92 scientific + 8 package-integrity = 100", all_runner)
        self.assertIn("retained baseline: 65 scientific + 8 package-integrity = 73", all_runner)
        self.assertIn("Self-contained scientific reproduction", artifact_readme)
        self.assertIn("Full-project integrity checks", artifact_readme)
        self.assertIn("65 scientific", artifact_readme)
        self.assertIn("8 package-integrity", artifact_readme)
        self.assertIn("92 scientific", artifact_readme)
        self.assertIn("pdfinfo", artifact_readme)
        self.assertIn("pdftotext", artifact_readme)

        quality = json.loads(CODE_QUALITY_AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(quality["scientific_tests"], 56)
        self.assertEqual(quality["package_integrity_tests"], 8)
        self.assertEqual(quality["combined_checks"], 64)
        self.assertIn("missing required source rows are rejected rather than synthesized as empty rows", quality["input_validation_repairs"])
        report = json.loads(REPRODUCTION_REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["scientific_tests"], 56)
        self.assertEqual(report["package_integrity_tests"], 8)
        self.assertEqual(report["combined_checks"], 64)
        self.assertEqual(report["entry_points"]["scientific"], "cd artifact && ./run-tests.sh")
        self.assertEqual(report["entry_points"]["package"], "cd artifact && ./run-package-checks.sh")

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
        generator = (ROOT / 'artifact/figures/build_figures.py').read_text(encoding='utf-8')
        self.assertIn(r'\includegraphics[width=.98\linewidth]{figures/running.pdf}', figure)
        self.assertNotIn(r'\begin{tikzpicture}', manuscript)
        self.assertIn("left-order cell", generator)
        self.assertIn("right-order cell", generator)
        self.assertIn("every source reaches both cells", figure)
        self.assertIn("one fixed message", generator)
        self.assertIn("pure integer fragment", figure)
        self.assertIn('$p^{s}$', generator)
        self.assertIn('$p^{l}$', generator)
        for name in ('running', 'triangle-product', 'stochastic-triangle', 'capacity-closure'):
            self.assertTrue((ROOT / 'paper/figures' / (name + '.pdf')).is_file())
            self.assertEqual((ROOT / 'paper/figures' / (name + '.pdf')).read_bytes(),
                             (ROOT / 'artifact/figures' / (name + '.pdf')).read_bytes())

    def test_project_manifest_covers_exact_public_tree_and_excludes_debris(self):
        manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
        current = json.loads(CURRENT_PACKAGE.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "CURRENT_PROJECT_MANIFEST_V1")
        listed = {row["path"]: row for row in manifest["files"]}
        self.assertEqual(len(listed), len(manifest["files"]))
        self.assertEqual(manifest['export_roots'], ['paper', 'artifact'])
        distribution = collect_export_records(ROOT, os.environ.get(ARCHIVE_ENV))
        actual_paths = set(distribution) - {'artifact/current-project-manifest.json'}
        self.assertEqual(set(listed), actual_paths)
        self.assertEqual(manifest["file_count"], len(actual_paths))
        self.assertEqual(
            manifest["root_entries"],
            sorted(EXPORT_ROOTS),
        )
        forbidden_parts = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}
        forbidden_suffixes = {".pyc", ".pyo", ".aux", ".blg", ".bbl", ".log", ".fls", ".fdb_latexmk", ".toc"}
        publisher_files = {rel: (ROOT / rel).read_bytes() for rel in BIB_PATHS + SUBMISSION_PATHS + VENDOR_PATHS}
        validate_bibliography(publisher_files, current)
        validate_vendor(publisher_files, current)
        validate_submission(publisher_files,current)
        for rel, row in listed.items():
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            self.assertFalse(forbidden_parts.intersection(path.parts), rel)
            if rel == "artifact/results/current/scientific.log":
                # This is retained scientific output, not a TeX build log.
                self.assertEqual(sha256_file(path), current["historical_file_sha256"][rel])
            elif rel == "paper/main.bbl":
                # Only this independently byte/key/source-bound bibliography
                # earns the exception; all inventory/hash/mode checks follow.
                self.assertEqual(current["publisher_bibliography"]["path"], rel)
            else:
                self.assertNotIn(path.suffix, forbidden_suffixes, rel)
            self.assertEqual(row["bytes"], path.stat().st_size, rel)
            self.assertEqual(row["sha256"], sha256_file(path), rel)
            # Distribution modes come from the actual ZIP when explicitly
            # supplied, otherwise the filesystem. The collector also enforces
            # physical modes on POSIX and exact ZIP/extracted-byte agreement.
            declared = "0755" if path.suffix == ".sh" else "0644"
            self.assertEqual(row["mode"], declared, rel)
            self.assertEqual(row["mode"], distribution[rel][1], rel)

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
        aliases=formal_aliases(manuscript)
        self.assertEqual(len(aliases),15)
        self.assertTrue(set(aliases.values())<=set(labels))
        self.assertTrue(set(aliases).isdisjoint(labels))
        # A second spelling is a preserved alias, never another proof count.
        owned=r"\begin{lemma}\label{owned:first}\label{owned:alias}x\end{lemma}"
        self.assertEqual(formal_aliases(owned),{'owned:alias':'owned:first'})
        with self.assertRaisesRegex(ValueError,'duplicate formal'):
            formal_aliases(owned+owned)

        with CORRECTNESS_LEDGER.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        statement_ids = [row["statement_id"] for row in rows]
        self.assertEqual(len(statement_ids), len(set(statement_ids)))
        # All55existing correctness claims survive, including the three old
        # profile claims now sharing one classified statement/proof.
        self.assertEqual(len(statement_ids),55)
        self.assertEqual(set(statement_ids),set(labels)|{'cor:clopen','thm:uniform','cor:uniform-finite-detector'})
        self.assertEqual({row['current_primary_statement_id'] for row in rows},set(labels))
        for row in rows:
            primary=aliases.get(row['statement_id'],row['statement_id'])
            self.assertEqual(row['current_primary_statement_id'],primary)
            self.assertEqual(row['current_label_role'],'alias_with_preserved_narrow_claim' if row['statement_id']!=primary else 'primary_formal_statement')

    def test_manuscript_structure_and_statement_location_audit(self):
        manuscript = strip_tex_comments(MANUSCRIPT.read_text(encoding="utf-8"))
        top_sections, source_records = parse_statement_locations(manuscript)
        audit = json.loads(CURRENT_STATEMENTS.read_text(encoding="utf-8"))
        audit_records = {entry["statement_id"]: entry for entry in audit["entries"]}
        self.assertEqual(len(audit_records),len(audit['entries']))

        self.assertEqual(len(top_sections), 9)
        self.assertEqual(audit["top_level_section_count"], 9)
        self.assertEqual(audit['body_top_level_section_count'], 8)
        self.assertEqual(tex_command_arguments(manuscript,"author"),["Anonymous Author(s)"])
        self.assertEqual(audit["top_level_sections"], top_sections)
        self.assertEqual(len(re.findall(r"\\appendix\b", manuscript)), 1)
        self.assertEqual(top_sections[-1], 'Contract laws and observation profiles')
        self.assertIn(r"\label{app:standard-facts}", manuscript)
        self.assertEqual(audit["manuscript_sha256"], sha256_file(MANUSCRIPT))
        self.assertEqual(audit["pdf_sha256"], sha256_file(PDF))
        self.assertEqual(audit["formal_statement_count"], 52)
        aliases=formal_aliases(manuscript)
        self.assertEqual(len(aliases),15)
        self.assertEqual(audit['label_aliases'],aliases)
        current=json.loads(CURRENT_PACKAGE.read_text(encoding='utf-8'))
        self.assertEqual(current['current_formal_label_aliases'],aliases)
        self.assertEqual(current['current_formal_primary_ids'],sorted(source_records))
        self.assertEqual(current['current_structure'],dict(formal_statements=52,proofs=52,figures=4,tables=10,sections=9,body_sections=8,bibliography_keys=70,citation_commands=105))
        self.assertTrue(set(aliases.values())<=set(source_records))
        self.assertTrue(set(aliases).isdisjoint(source_records))
        self.assertEqual(audit["schema"], "CURRENT_STATEMENT_LOCATIONS_V1")
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
        audit = json.loads(CURRENT_STATEMENTS.read_text(encoding="utf-8"))
        audit_records = {entry["statement_id"]: entry for entry in audit["entries"]}
        aliases=audit['label_aliases']

        with CORRECTNESS_LEDGER.open(newline="", encoding="utf-8") as handle:
            correctness_rows = list(csv.DictReader(handle))
        self.assertEqual(len(correctness_rows),55)
        self.assertEqual({row['current_primary_statement_id'] for row in correctness_rows},set(audit_records))
        for row in correctness_rows:
            primary=aliases.get(row['statement_id'],row['statement_id'])
            self.assertEqual(row['current_primary_statement_id'],primary)
            entry = audit_records[primary]
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
                primary=aliases.get(statement_id,statement_id)
                if primary not in audit_records:
                    continue
                entry = audit_records[primary]
                display = ENVIRONMENT_NAMES[entry["environment"]]
                self.assertIn(
                    f"{display} {entry['number']} (PDF p. {entry['pdf_page']})",
                    row["paper_location"],
                    row["claim_id"],
                )


if __name__ == "__main__":
    unittest.main()
