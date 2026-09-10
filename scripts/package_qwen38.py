#!/usr/bin/env python3
"""Build the allowlisted Qwen3.8 pilot package without downloading model weights.

The 20 historical and five human-reviewed validation PDFs are checked against
their reference records. Evaluation symlinks become regular archive files.
--check validates inputs without creating experiments/qwen38_package.tar.gz.
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


BASELINE_REVISION = "7cfb30d71a1f4f49a57592323337a4a4727301da"
ARCHIVE_ROOT = "qwen38_pilot"
FILES = (
    "split.py", "rotation.py", "production_state.py", "run_production.py",
    "eval_boundaries.py", "score_full.py", "model_options.py", "qwen38_client.py",
    "smoke_qwen38.py", "requirements.txt", "requirements-lock.txt",
    "requirements-qwen38-client.txt", "data/qwen38_deployment.json", "docs/QWEN38.md",
    "data/qwen38_deployment_initial.json", "data/qwen38_deployment_vision_v2.json",
    "data/qwen38_deployment_compact_v3.json",
    "scripts/start_qwen38_server.sh", "scripts/bootstrap_qwen38_runpod.sh",
    "scripts/run_qwen38_pilot.py", "data/gergana_review_v1.json",
    "data/eval_reference.json", "data/boundary_corrections.json",
    "feature_pipeline.py", "filing_features.py", "filing_boundary_v5b.py",
    "filing_boundary.py", "pair_boundary.py", "page_profile.py",
    "profile_policy_v4b.py", "labeled_qwen38.py", "docs/QWEN38_IMPROVEMENT_LOG.md",
    "feature_refinement.py", "filing_features_v7.py", "refinement_policy.py",
    "boundary_facts.py", "boundary_fact_policy.py", "feature_fact_recovery.py",
    "plot_facts.py", "filing_unit_policy.py",
    "thermal_transition.py", "anchor_facts.py", "feature_context_recovery.py",
    "structural_facts.py", "structural_fact_policy.py", "supported_receipt_policy.py",
    "docs/QWEN38_ERROR_ANALYSIS.md", "docs/QWEN38_LABEL_QUESTIONS.md",
    "docs/QWEN38_RESULTS.md", "receipt_consistency.py",
)
FILES += ('page_artifact.py', 'artifact_policy.py', 'artifact_recovery.py', 'sequential_policy.py', 'sequential_recovery.py', 'page_identity.py', 'identity_policy.py', 'identity_selection.py', 'independent_page_recovery.py', 'identity_recovery.py', 'legal_identity.py', 'legal_crop_policy.py', 'filing_identity.py', 'filing_crop_identity.py', 'report_ocr_policy.py', 'report_ocr_recovery.py', 'docs/QWEN38_V13_EXPERIMENT.md')
DATASETS = {"eval_full": (20, 733), "eval_gergana": (5, 84)}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value):
    return sha256(json.dumps(value, sort_keys=True).encode())


def basename(name):
    return (type(name) is str and PurePosixPath(name).name == name
            and "\\" not in name and name.endswith(".pdf"))


def validate_deployment(deployment):
    if (not isinstance(deployment, dict) or deployment.get("version") != 1
            or deployment.get("id") not in {"qwen38-27b-nvfp4-v1", "qwen38-27b-nvfp4-vision-v2", "qwen38-27b-nvfp4-compact-v3"}
            or deployment.get("model_family") != "qwen3.8"
            or type(deployment.get("checkpoint")) is not str or not deployment["checkpoint"]
            or type(deployment.get("served_model")) is not str or not deployment["served_model"]
            or not re.fullmatch(r"[0-9a-f]{40}", str(deployment.get("revision", "")))):
        raise ValueError("Expected a versioned Qwen3.8 deployment with an exact model revision")
    runtime = deployment.get("runtime")
    if (not isinstance(runtime, dict)
            or not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", str(runtime.get("image", "")))
            or not re.fullmatch(r"[0-9a-f]{40}", str(runtime.get("commit", "")))):
        raise ValueError("Qwen3.8 runtime must pin the container digest and source commit")


def file_entry(name, data, kind="project_file", **metadata):
    return {"path": name, "source_path": name, "source_sha256": sha256(data),
            "packaged_sha256": sha256(data), "bytes": len(data), "kind": kind, **metadata}


def collect_dataset(root, folder, reference, review, project_bytes):
    from pypdf import PdfReader

    entries, totals, actual_hashes = [], {}, {}
    gt_path = folder + "/ground_truth.json"
    gt_bytes = (root / gt_path).read_bytes()
    gt = json.loads(gt_bytes)
    count, pages = DATASETS[folder]
    if not isinstance(gt, dict) or len(gt) != count or not all(basename(n) for n in gt):
        raise ValueError(f"{folder}: expected exactly {count} source PDF basenames")
    if folder == "eval_full":
        if (set(gt) != set(reference["strata"])
                or canonical_hash(gt) != reference["ground_truth_sha256"]):
            raise ValueError("Historical ground truth differs from its reviewed reference")
    else:
        if (review.get("label_status") != "human_confirmed"
                or set(gt) != set(review["files"])
                or gt != {n: row["starts"] for n, row in review["files"].items()}):
            raise ValueError("Gergana ground truth differs from its human review record")
    entries.append(file_entry(gt_path, gt_bytes, "dataset_metadata"))
    optional = {}
    for name in ("masked.json", "strata.json", "dataset.json"):
        path = root / folder / name
        if path.is_file():
            data = path.read_bytes()
            optional[name] = json.loads(data)
            entries.append(file_entry(folder + "/" + name, data, "dataset_metadata"))
    for name, starts in sorted(gt.items()):
        path = folder + "/" + name
        data = (root / path).read_bytes()  # Dereference only the explicitly listed PDF.
        total = len(PdfReader(io.BytesIO(data)).pages)
        if (type(starts) is not list or not starts or starts[0] != 1
                or any(type(p) is not int or not 1 <= p <= total for p in starts)
                or starts != sorted(set(starts))):
            raise ValueError(f"Invalid ground-truth starts: {folder}/{name}")
        totals[name], actual_hashes[name] = total, sha256(data)
        if folder == "eval_gergana":
            reviewed = review["files"][name]
            if total != reviewed["total_pages"] or actual_hashes[name] != reviewed["source_sha256"]:
                raise ValueError(f"Source differs from human review: {name}")
        entries.append(file_entry(path, data, "source_pdf", total_pages=total))
    if sum(totals.values()) != pages:
        raise ValueError(f"{folder}: expected {pages} total source pages")
    strata = optional.get("strata.json")
    if strata is not None:
        if (not isinstance(strata, dict) or set(strata) != set(gt)
                or any(type(v) is not str or not v for v in strata.values())
                or (folder == "eval_full" and strata != reference["strata"])):
            raise ValueError(f"{folder}: strata do not agree with the dataset")
    masked = optional.get("masked.json", {})
    if not isinstance(masked, dict) or set(masked) - set(gt):
        raise ValueError(f"{folder}: invalid mask coverage")
    for name, ranges in masked.items():
        if (type(ranges) is not list or any(type(pair) is not list or len(pair) != 2
                or any(type(p) is not int for p in pair) or not 1 <= pair[0] <= pair[1] <= totals[name]
                for pair in ranges)):
            raise ValueError(f"{folder}: invalid masked page range")
    dataset = optional.get("dataset.json")
    if dataset is not None:
        if (not isinstance(dataset, dict) or dataset.get("version") != 1
                or dataset.get("ground_truth_sha256") != canonical_hash(gt)
                or not isinstance(dataset.get("files"), dict) or set(dataset["files"]) != set(gt)):
            raise ValueError(f"{folder}: invalid or stale dataset manifest")
        for name, row in dataset["files"].items():
            if (not isinstance(row, dict) or row.get("sha256") != actual_hashes[name]
                    or type(row.get("total_pages")) is not int or row["total_pages"] != totals[name]):
                raise ValueError(f"{folder}: source differs from dataset manifest: {name}")
        if folder == "eval_gergana" and dataset.get("reference_labels_sha256") != sha256(project_bytes["data/gergana_review_v1.json"]):
            raise ValueError("Gergana dataset manifest refers to different human labels")
        if (folder == "eval_full" and "corrections_sha256" in dataset
                and dataset["corrections_sha256"] != sha256(project_bytes["data/boundary_corrections.json"])):
            raise ValueError("Historical dataset manifest refers to different boundary corrections")
    return entries, {"files": count, "total_pages": pages,
                     "ground_truth_sha256": canonical_hash(gt),
                     "dataset_manifest_present": dataset is not None}


def collect_inputs(root):
    project_bytes, entries = {}, []
    for name in FILES:
        path = root / name
        if not path.is_file():
            raise ValueError(f"Missing required package input: {path}")
        data = path.read_bytes()
        project_bytes[name] = data
        entries.append(file_entry(name, data))
    deployment = json.loads(project_bytes["data/qwen38_deployment.json"])
    validate_deployment(deployment)
    reference = json.loads(project_bytes["data/eval_reference.json"])
    review = json.loads(project_bytes["data/gergana_review_v1.json"])
    datasets = {}
    for folder in DATASETS:
        dataset_entries, datasets[folder] = collect_dataset(root, folder, reference, review, project_bytes)
        entries.extend(dataset_entries)
    revision = (BASELINE_REVISION + "\n").encode()
    entries.append({"path": "baseline_revision.txt", "source_path": None, "source_sha256": None,
                    "packaged_sha256": sha256(revision), "bytes": len(revision), "kind": "generated_metadata"})
    return deployment, datasets, entries


def add_bytes(archive, path, data):
    member = tarfile.TarInfo(ARCHIVE_ROOT + "/" + path)
    member.size, member.mtime = len(data), 0
    member.mode = 0o755 if path == "scripts/start_qwen38_server.sh" else 0o644
    archive.addfile(member, io.BytesIO(data))


def validate_archive(path, manifest):
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
                    raise ValueError("Archive manifest does not match verified contents")
            else:
                row = expected[member.name]
                if len(data) != row["bytes"] or sha256(data) != row["packaged_sha256"]:
                    raise ValueError(f"Archive verification failed: {member.name}")


def build(root, output, deployment, datasets, entries):
    manifest = {
        "schema_version": 1, "experiment_id": deployment["id"], "archive_root": ARCHIVE_ROOT,
        "created_at": datetime.now(timezone.utc).isoformat(), "baseline_revision": BASELINE_REVISION,
        "candidate_checkpoint": deployment["checkpoint"], "candidate_revision": deployment["revision"],
        "candidate_runtime_image": deployment["runtime"]["image"], "datasets": datasets,
        "deployment_sha256": next(row["packaged_sha256"] for row in entries
                                   if row["path"] == "data/qwen38_deployment.json"),
        "contents": entries,
        "notes": ["Every archive member is a regular file; PDF symlinks are dereferenced.",
                  "The manifest hashes every payload file, excluding itself.",
                  "No model weights, automatic split outputs, caches, or credentials are included.",
                  "Historical and human-reviewed validation data remain separate datasets."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".qwen38-", suffix=".tar.gz", dir=output.parent)
    os.close(fd)
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for row in entries:
                data = ((BASELINE_REVISION + "\n").encode() if row["source_path"] is None
                        else (root / row["source_path"]).read_bytes())
                if len(data) != row["bytes"] or sha256(data) != row["packaged_sha256"]:
                    raise ValueError(f"Input changed while packaging: {row['path']}")
                add_bytes(archive, row["path"], data)
            add_bytes(archive, "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
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
    parser.add_argument("--output", type=Path, help="Default: experiments/qwen38_package.tar.gz")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        deployment, datasets, entries = collect_inputs(root)
        total = sum(row["bytes"] for row in entries)
        print(f"Validated {len(entries)} payload files, 25 PDFs, 817 pages; {total:,} bytes before compression")
        if args.check:
            print("Validation only: no archive created and no model loaded")
            return 0
        output = args.output.resolve() if args.output else root / "experiments/qwen38_package.tar.gz"
        build(root, output, deployment, datasets, entries)
        print(f"Package: {output}")
        print(f"Archive SHA-256: {sha256(output.read_bytes())}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
