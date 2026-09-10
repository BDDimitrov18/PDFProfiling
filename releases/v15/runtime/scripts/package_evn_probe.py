#!/usr/bin/env python3
"""Build the small, allowlisted EVN GPU probe package without loading a model.

Run --check to validate all inputs without creating an archive. The default
output is experiments/evn_probe_package.tar.gz, which the repository ignores.
PDF symlinks are dereferenced into regular archive members. No other corpus,
cached output, credential, or local environment file is included.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile


MODEL_REVISION = "7cfb30d71a1f4f49a57592323337a4a4727301da"
ARCHIVE_ROOT = "evn_probe"
FILES = (
    "split.py", "rotation.py", "production_state.py", "run_production.py",
    "eval_boundaries.py", "score_full.py", "evn_sections.py",
    "run_evn_experiment.py", "requirements.txt", "requirements-lock.txt",
    "model_options.py", "qwen38_client.py",
    "data/evn_probe_v1.json", "docs/EVN_EXPERIMENT.md",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def validate_spec(spec):
    """Validate the frozen package's small, explicit request/source schema."""
    if (not isinstance(spec, dict) or spec.get("version") != 1
            or spec.get("id") != "evn-selective-probe-v1"):
        raise ValueError("Expected the frozen evn-selective-probe-v1 specification")
    sources, cases = spec.get("sources"), spec.get("cases")
    if not isinstance(sources, dict) or len(sources) != 4:
        raise ValueError("The initial probe must have exactly four source PDFs")
    if not isinstance(cases, list) or len(cases) != 12:
        raise ValueError("The initial probe must have exactly twelve page requests")
    for name, source in sources.items():
        if (type(name) is not str or PurePosixPath(name).name != name
                or "\\" in name or not name.endswith(".pdf")
                or not isinstance(source, dict)
                or not re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", "")))
                or type(source.get("total_pages")) is not int
                or source["total_pages"] < 1):
            raise ValueError(f"Invalid source specification: {name!r}")
    seen, counts = set(), {"keep": 0, "suppress": 0, "observe": 0}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Every probe page request must be an object")
        name, page, action = case.get("file"), case.get("page"), case.get("expected_action")
        if (name not in sources or type(page) is not int
                or not 1 <= page <= sources[name]["total_pages"] or action not in counts
                or (name, page) in seen):
            raise ValueError("Invalid or duplicate probe page request")
        seen.add((name, page))
        counts[action] += 1
    if counts != {"keep": 9, "suppress": 2, "observe": 1}:
        raise ValueError("Frozen probe requires nine keep, two suppress, one observe")
    if {name for name, _ in seen} != set(sources):
        raise ValueError("Probe source coverage differs from its page requests")


def collect_inputs(root):
    from pypdf import PdfReader

    spec_path = root / "data/evn_probe_v1.json"
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)
    validate_spec(spec)
    entries = []
    for name in FILES:
        path = root / name
        if not path.is_file():
            raise ValueError(f"Missing required package input: {path}")
        data = path.read_bytes()
        if name == "data/evn_probe_v1.json" and data != spec_bytes:
            raise ValueError("Probe specification changed while collecting package inputs")
        entries.append({"path": name, "source_path": name, "source_sha256": sha256(data),
                        "packaged_sha256": sha256(data), "bytes": len(data), "kind": "project_file"})
    for name, source in sorted(spec["sources"].items()):
        relative_source = "eval_full/" + name
        path = root / relative_source
        data = path.read_bytes()  # Read through the eval symlink; archive regular bytes only.
        if sha256(data) != source["sha256"]:
            raise ValueError(f"Source hash differs from frozen specification: {name}")
        if len(PdfReader(io.BytesIO(data)).pages) != source["total_pages"]:
            raise ValueError(f"Source page count differs from frozen specification: {name}")
        entries.append({"path": "probe_sources/" + name, "source_path": relative_source,
                        "source_sha256": sha256(data), "packaged_sha256": sha256(data),
                        "bytes": len(data), "kind": "source_pdf",
                        "total_pages": source["total_pages"]})
    revision = (MODEL_REVISION + "\n").encode()
    entries.append({"path": "model_revision.txt", "source_path": None,
                    "source_sha256": None, "packaged_sha256": sha256(revision),
                    "bytes": len(revision), "kind": "generated_metadata"})
    return spec, entries


def add_bytes(archive, path, data):
    member = tarfile.TarInfo(ARCHIVE_ROOT + "/" + path)
    member.size = len(data)
    member.mode = 0o644
    member.mtime = 0
    archive.addfile(member, io.BytesIO(data))


def validate_archive(path, manifest):
    """Read back exact members and their bytes; links and extra files are rejected."""
    expected = {ARCHIVE_ROOT + "/" + row["path"]: row for row in manifest["contents"]}
    manifest_name = ARCHIVE_ROOT + "/manifest.json"
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        if (len(members) != len(expected) + 1
                or {m.name for m in members} != set(expected) | {manifest_name}
                or any(not m.isfile() for m in members)):
            raise ValueError("Archive contains missing, duplicate, linked, or unlisted members")
        for member in members:
            data = archive.extractfile(member).read()
            if member.name == manifest_name:
                if json.loads(data) != manifest:
                    raise ValueError("Archive manifest does not match its verified contents")
            else:
                row = expected[member.name]
                if len(data) != row["bytes"] or sha256(data) != row["packaged_sha256"]:
                    raise ValueError(f"Archive verification failed: {member.name}")


def build(root, output, spec, entries):
    manifest = {
        "schema_version": 1,
        "experiment_id": spec["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "archive_root": ARCHIVE_ROOT,
        "model_revision": MODEL_REVISION,
        "probe_spec_sha256": next(e["packaged_sha256"] for e in entries
                                   if e["path"] == "data/evn_probe_v1.json"),
        "contents": entries,
        "notes": ["All archive entries are regular files; source PDF links are dereferenced.",
                  "The manifest records every payload file, excluding itself.",
                  "No model weights are included or downloaded by this builder.",
                  "Historical logs and the external validation corpus are not packaged."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".evn-probe-", suffix=".tar.gz", dir=output.parent)
    os.close(fd)
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for row in entries:
                data = ((MODEL_REVISION + "\n").encode() if row["source_path"] is None
                        else (root / row["source_path"]).read_bytes())
                if len(data) != row["bytes"] or sha256(data) != row["packaged_sha256"]:
                    raise ValueError(f"Input changed while packaging: {row['path']}")
                add_bytes(archive, row["path"], data)
            add_bytes(archive, "manifest.json",
                      (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
        validate_archive(temporary, manifest)
        with open(temporary, "rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate inputs without creating an archive")
    parser.add_argument("--output", type=Path, help="Default: experiments/evn_probe_package.tar.gz")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        spec, entries = collect_inputs(root)
        total = sum(e["bytes"] for e in entries)
        print(f"Validated {len(entries)} payload files, 4 PDFs, 12 probe pages; {total:,} bytes before compression")
        if args.check:
            print("Validation only: no archive created and no model loaded")
            return 0
        output = args.output.resolve() if args.output else root / "experiments/evn_probe_package.tar.gz"
        build(root, output, spec, entries)
        print(f"Package: {output}")
        print(f"Archive SHA-256: {sha256(output.read_bytes())}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
