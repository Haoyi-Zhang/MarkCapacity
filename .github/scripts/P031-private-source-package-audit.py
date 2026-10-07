"""Read-only audit of the approved embedded private P031 tar and extracted tree.

This helper stays outside the exact source export. It does not extract, chmod,
write, fetch, execute package source, or replace the package's own test gates.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

MANIFEST = "artifact/current-project-manifest.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect_archive(path, expected):
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size <= 16_000_000
    assert sha(path.read_bytes()) == expected, "approved private archive digest"
    files = {}
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
        assert len(members) == len({member.name for member in members}) == 102
        for member in members:
            pure = PurePosixPath(member.name)
            assert member.isfile() and 1 < len(pure.parts) and pure.parts[0] == "P031"
            assert not pure.is_absolute() and ".." not in pure.parts and "\\" not in member.name
            assert str(pure) == member.name and member.size <= 2_000_000
            rel = str(PurePosixPath(*pure.parts[1:]))
            mode = 0o755 if pure.suffix == ".sh" else 0o644
            assert member.mode == mode, rel
            files[rel] = archive.extractfile(member).read()
    manifest = json.loads(files[MANIFEST])
    rows = manifest["files"]
    names = [row["path"] for row in rows]
    assert manifest["schema"] == "CURRENT_PROJECT_MANIFEST_V1"
    assert len(names) == len(set(names)) == manifest["file_count"] == 101
    assert set(names) == set(files) - {MANIFEST}
    assert manifest["root_entries"] == sorted({PurePosixPath(rel).parts[0] for rel in files})
    for row in rows:
        rel = row["path"]
        assert type(row["bytes"]) is int and row["bytes"] == len(files[rel])
        assert row["sha256"] == sha(files[rel])
        assert row["mode"] == ("0755" if Path(rel).suffix == ".sh" else "0644")
    return files, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--extracted-root", type=Path)
    args = parser.parse_args()
    files, manifest = inspect_archive(args.archive, args.expected_sha256)
    result = {"scope": "approved archive byte/header binding only",
              "archive_sha256": args.expected_sha256, "regular_files": len(files),
              "manifest_rows": manifest["file_count"], "filesystem_modes_verified": False}
    if args.extracted_root is not None:
        root = args.extracted_root.resolve()
        paths = list(root.rglob("*"))
        assert not any(path.is_symlink() for path in paths)
        actual = {path.relative_to(root).as_posix(): path for path in paths if path.is_file()}
        assert set(actual) == set(files), "exact extracted regular-file inventory"
        assert sorted(path.name for path in root.iterdir()) == manifest["root_entries"]
        inventory = {}
        for rel, path in sorted(actual.items()):
            mode = path.stat().st_mode & 0o777
            assert mode == (0o755 if path.suffix == ".sh" else 0o644), rel
            data = path.read_bytes()
            assert data == files[rel], rel
            inventory[rel] = {"bytes": len(data), "sha256": sha(data), "mode": f"{mode:04o}"}
        assert inventory[MANIFEST]["mode"] == "0644"
        result.update(scope="actual extracted byte/inventory/stat modes, including self-manifest",
                      filesystem_modes_verified=True, inventory=inventory)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
