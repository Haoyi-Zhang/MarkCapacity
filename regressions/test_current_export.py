"""Owned in-memory source-export checks, without private files or TeX runs."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import current_export as validator


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture():
    keys = ["owned%02d" % i for i in range(68)]
    files = {
        "paper/main.tex": ("\\bibliographystyle{ACM-Reference-Format}\n\\bibliography{references}\n"
                           + "\n".join("\\cite{" + key + "}" for key in keys)).encode(),
        "paper/references.bib": "\n".join("@article{" + key + ", title={owned fixture}}" for key in keys).encode(),
        "paper/main.bbl": ("% ACM-Reference-Format-Journals [18-Jan-2012]\n\\begin{thebibliography}{68}\n"
                           + "\n".join("\\bibitem[Owned(2026)]%\n{" + key + "} owned" for key in keys)
                           + "\n\\end{thebibliography}\n").encode(),
        "paper/acmart.cls": b"owned class fixture",
        "paper/acmart.dtx": b"Copyright 2016-2026, Association for Computing Machinery\nLaTeX Project Public License\nmaintained\n",
        "paper/acmart.ins": b"owned extraction fixture",
        "paper/ACM-SOURCE-NOTICE.md": b"owned notice fixture",
        "artifact/results/current/scientific.log": b"retained owned output\n",
        "artifact/owned.sh": b"#!/bin/sh\nexit 0\n",
        "artifact/owned-ledger.csv": b"current owned ledger\n",
    }
    old_ledger_hash = sha(b'earlier owned ledger\n')
    files['artifact/project-manifest.json'] = json.dumps({'files': [
        {'path': 'artifact/owned-ledger.csv', 'sha256': old_ledger_hash}]}).encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name in ("acmart.dtx", "acmart.ins"):
            data = files["paper/" + name]
            info = tarfile.TarInfo("owned-upstream/" + name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    files["paper/acmart-source-v2.19.tar.gz"] = buffer.getvalue()
    current = dict(manuscript_sha256=sha(files["paper/main.tex"]),
                   current_bib_entry_sha256=dict.fromkeys(keys, "fixture"),
                   historical_file_sha256={"artifact/results/current/scientific.log": sha(files["artifact/results/current/scientific.log"])},
                   current_file_sha256={'artifact/owned-ledger.csv': sha(files['artifact/owned-ledger.csv'])},
                   prior_export_file_sha256={'artifact/owned-ledger.csv': old_ledger_hash},
                   publisher_bibliography=dict(path="paper/main.bbl", bytes=len(files["paper/main.bbl"]),
                       sha256=sha(files["paper/main.bbl"]), references_sha256=sha(files["paper/references.bib"]),
                       keys=keys, key_count=68),
                   template_source=dict(release="2.19", date="2026-06-27",
                       upstream_commit="062edc8119be9067a346ce874281eab48b2c29a4",
                       source_url="https://raw.githubusercontent.com/borisveytsman/acmart/062edc8119be9067a346ce874281eab48b2c29a4/acmart.dtx",
                       derived_class_sha256=sha(files["paper/acmart.cls"]),
                       file_sha256={path: sha(files[path]) for path in validator.VENDOR_PATHS}))
    records = {path: (data, "0755" if path.endswith(".sh") else "0644") for path, data in files.items()}
    records[validator.MANIFEST] = (b"manifest fixture", "0644")
    return records, manifest_for(records), current


def manifest_for(records):
    # Independent reference: exact set and byte/mode records, not validator helpers.
    names = sorted(set(records) - {validator.MANIFEST})
    return dict(schema="CURRENT_PROJECT_MANIFEST_V1", file_count=len(names),
                export_roots=['paper', 'artifact'],
                root_entries=sorted({name.split("/")[0] for name in records}),
                files=[dict(path=name, bytes=len(records[name][0]), sha256=sha(records[name][0]),
                            mode=records[name][1]) for name in names])


class CurrentExportTests(unittest.TestCase):
    def test_two_root_zip_rejects_unlisted_members(self):
        records, manifest, current = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Materialize the fixture, with outer project navigation present.
            # collect_export_records must not require that navigation in ZIPs.
            for name, (data, mode) in records.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                path.chmod(int(mode, 8))
            (root / 'README.md').write_text('Project navigation only.', encoding='utf-8')
            self.assertEqual(set(validator.collect_export_records(root)), set(records))
            for extra in (None, 'paper/unlisted-research.txt', 'artifact/unlisted-result.json', 'README.md'):
                with self.subTest(extra=extra):
                    archive = root / 'export.zip'
                    with zipfile.ZipFile(archive, 'w') as output:
                        for name, (data, mode) in records.items():
                            info = zipfile.ZipInfo(name)
                            info.create_system = 3
                            info.external_attr = (0o100000 | int(mode, 8)) << 16
                            output.writestr(info, data)
                        if extra:
                            info = zipfile.ZipInfo(extra)
                            info.create_system = 3
                            info.external_attr = 0o100644 << 16
                            output.writestr(info, b'owned unlisted fixture')
                    with zipfile.ZipFile(archive) as supplied:
                        actual = {item.filename: (supplied.read(item), f'{(item.external_attr >> 16) & 0o777:04o}')
                                  for item in supplied.infolist()}
                    if extra:
                        with self.assertRaisesRegex(ValueError, 'exact current file inventory'):
                            validator.validate_inventory(actual, manifest, current)
                    else:
                        self.assertEqual({name.split('/')[0] for name in actual}, {'paper', 'artifact'})
                        self.assertNotIn('README.md', actual)
                        validator.validate_inventory(actual, manifest, current)

            def make_zip(*, changed=None, omitted=None, extra=None, duplicate=None,
                         bad_mode=None, bad_type=None, dos_file=None):
                archive = root / 'export.zip'
                with zipfile.ZipFile(archive, 'w') as output:
                    for name, (data, mode) in records.items():
                        if name == omitted:
                            continue
                        info = zipfile.ZipInfo(name)
                        info.create_system = 0 if name == dos_file else 3
                        unix_mode = int(mode, 8) if name != bad_mode else 0o666
                        file_type = 0o120000 if name == bad_type else 0o100000
                        info.external_attr = (file_type | unix_mode) << 16
                        output.writestr(info, data + b'changed' if name == changed else data)
                        if name == duplicate:
                            with self.assertWarnsRegex(UserWarning, 'Duplicate name'):
                                output.writestr(copy.copy(info), data)
                    if extra:
                        info = zipfile.ZipInfo(extra)
                        info.create_system = 3
                        info.external_attr = 0o100644 << 16
                        output.writestr(info, b'owned extra fixture')
                return archive

            archive = make_zip()
            supplied = validator.collect_export_records(root, archive)
            self.assertEqual(supplied, records)
            validator.validate_inventory(supplied, manifest, current)
            for arguments in (
                {'bad_mode': 'paper/main.bbl'},
                {'bad_mode': validator.MANIFEST},
                {'bad_type': 'paper/main.bbl'},
                {'dos_file': 'paper/main.bbl'},
                {'omitted': 'paper/main.bbl'},
                {'omitted': validator.MANIFEST},
                {'extra': 'artifact/unlisted-result.json'},
                {'extra': 'README.md'},
                {'changed': 'paper/main.bbl'},
                {'duplicate': 'paper/main.bbl'},
            ):
                with self.subTest(zip_case=arguments):
                    with self.assertRaises(ValueError):
                        validator.collect_export_records(root, make_zip(**arguments))
            archive = make_zip()
            extra = root/'paper/extra-extracted.txt'
            extra.write_bytes(b'owned extracted extra')
            with self.assertRaisesRegex(ValueError, 'archive/extracted exact file inventory'):
                validator.collect_export_records(root, archive)
            extra.unlink()
            original = (root/'paper/main.bbl').read_bytes()
            (root/'paper/main.bbl').write_bytes(original + b'changed')
            with self.assertRaisesRegex(ValueError, 'archive/extracted bytes'):
                validator.collect_export_records(root, archive)
            (root/'paper/main.bbl').write_bytes(original)
            bad_physical = dict(records)
            bad_physical['paper/main.bbl'] = (original, '0666')
            with patch.object(validator, '_requires_posix_modes', return_value=True), \
                 patch.object(validator, '_collect_filesystem_records', return_value=bad_physical):
                with self.assertRaisesRegex(ValueError, 'physical POSIX mode'):
                    validator.collect_export_records(root, archive)
            if not validator._requires_posix_modes():
                with self.assertRaisesRegex(ValueError, 'actual distribution mode'):
                    validator.validate_inventory(validator.collect_export_records(root), manifest, current)

    def test_exact_bibliography_role_and_inputs_unchanged(self):
        records, manifest, current = fixture()
        original = copy.deepcopy((records, manifest, current))
        validator.validate_inventory(records, manifest, current)
        self.assertEqual((records, manifest, current), original)
        validator.validate_bibliography({p: records[p][0] for p in validator.BIB_PATHS}, current)
        # An unused database record is not a rendered reference. Its source
        # bytes remain bound, but the compiled/cited key count must stay 68.
        files = {p: records[p][0] for p in validator.BIB_PATHS}
        files['paper/references.bib'] += b'\n@article{unused, title={owned unused fixture}}\n'
        current['publisher_bibliography']['references_sha256'] = sha(files['paper/references.bib'])
        validator.validate_bibliography(files, current)
        self.assertEqual(current['publisher_bibliography']['key_count'], 68)
        badmeta = copy.deepcopy(current)
        badmeta['publisher_bibliography']['key_count'] = 69
        with self.assertRaisesRegex(ValueError, 'metadata keys'):
            validator.validate_bibliography(files, badmeta)

    def test_extra_bbl_aux_blg_are_rejected_even_if_manifest_is_fresh(self):
        for path in ("paper/extra.bbl", "paper/main.aux", "paper/main.blg", "artifact/main.bbl"):
            records, _, current = fixture()
            records[path] = (b"owned extra", "0644")
            with self.assertRaisesRegex(ValueError, "forbidden debris"):
                validator.validate_inventory(records, manifest_for(records), current)

    def test_inventory_digest_duplicates_and_actual_modes_are_mandatory(self):
        records, manifest, current = fixture()
        mutants = [dict(manifest, files=manifest["files"][:-1]),
                   dict(manifest, files=manifest["files"] + [manifest["files"][0]]), copy.deepcopy(manifest)]
        mutants[-1]["files"][0]["sha256"] = "0" * 64
        for bad in mutants:
            with self.assertRaises(ValueError):
                validator.validate_inventory(records, bad, current)
        bad = dict(records)
        bad["paper/main.bbl"] = (records["paper/main.bbl"][0], "0666")
        with self.assertRaisesRegex(ValueError, "actual distribution mode"):
            validator.validate_inventory(bad, manifest, current)
        bad["paper/main.bbl"] = (records["paper/main.bbl"][0], "0755")
        with self.assertRaisesRegex(ValueError, "actual distribution mode"):
            validator.validate_inventory(bad, manifest_for(bad), current)
        for mode in ("0666", "0755", "0600"):
            with self.subTest(manifest_mode=mode):
                bad = dict(records)
                bad[validator.MANIFEST] = (records[validator.MANIFEST][0], mode)
                fresh = manifest_for(bad)
                self.assertNotIn(validator.MANIFEST, {row["path"] for row in fresh["files"]})
                with self.assertRaisesRegex(ValueError, "actual distribution mode"):
                    validator.validate_inventory(bad, fresh, current)
        bad = dict(records)
        bad.pop(validator.MANIFEST)
        with self.assertRaisesRegex(ValueError, "current manifest file missing"):
            validator.validate_inventory(bad, manifest_for(bad), current)

    def test_bibliography_bytes_keys_and_active_inclusion_are_bound(self):
        records, _, current = fixture()
        files = {p: data for p, (data, _) in records.items()}
        for name, value in (("path", "paper/extra.bbl"), ("sha256", "0" * 64), ("key_count", True)):
            bad = copy.deepcopy(current)
            bad["publisher_bibliography"][name] = value
            with self.assertRaises(ValueError):
                validator.validate_bibliography(files, bad)
        for changed in (files["paper/main.bbl"].replace(b"{owned67}", b"{owned00}"),
                        files["paper/main.bbl"].replace(b"{owned67}", b"{invented}")):
            badfiles = dict(files, **{"paper/main.bbl": changed})
            badmeta = copy.deepcopy(current)
            badmeta["publisher_bibliography"].update(bytes=len(changed), sha256=sha(changed))
            with self.assertRaisesRegex(ValueError, "compiled-key coverage"):
                validator.validate_bibliography(badfiles, badmeta)
        changed = files["paper/main.tex"].replace(b"\\bibliography{references}", b"%\\bibliography{references}")
        badfiles = dict(files, **{"paper/main.tex": changed})
        badmeta = dict(current, manuscript_sha256=sha(changed))
        with self.assertRaisesRegex(ValueError, "inclusion/style"):
            validator.validate_bibliography(badfiles, badmeta)

    def test_retained_log_binding_cannot_be_resealed_by_current_manifest(self):
        records, _, current = fixture()
        records["artifact/results/current/scientific.log"] = (b"changed owned output", "0644")
        with self.assertRaisesRegex(ValueError, "retained log binding"):
            validator.validate_inventory(records, manifest_for(records), current)
        records, _, current = fixture()
        records['artifact/owned-ledger.csv'] = (b'altered owned current ledger', '0644')
        with self.assertRaisesRegex(ValueError, 'current byte binding'):
            validator.validate_inventory(records, manifest_for(records), current)
        records, manifest, current = fixture()
        current['prior_export_file_sha256']['artifact/owned-ledger.csv'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'prior export identity'):
            validator.validate_inventory(records, manifest, current)

    def test_vendor_source_and_original_notice_bindings_are_required(self):
        records, _, current = fixture()
        files = {p: data for p, (data, _) in records.items()}
        validator.validate_vendor(files, current)
        for path in validator.VENDOR_PATHS:
            bad = dict(files)
            bad[path] += b"changed"
            with self.assertRaisesRegex(ValueError, "template source binding"):
                validator.validate_vendor(bad, current)
        bad = copy.deepcopy(current)
        bad["template_source"]["release"] = "2.20"
        with self.assertRaisesRegex(ValueError, "release"):
            validator.validate_vendor(files, bad)
        bad = copy.deepcopy(current)
        bad["template_source"]["upstream_commit"] = "invented"
        with self.assertRaisesRegex(ValueError, "authority"):
            validator.validate_vendor(files, bad)


if __name__ == "__main__":
    unittest.main()
