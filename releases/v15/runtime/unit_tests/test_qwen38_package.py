import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from scripts import package_qwen38 as package


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in package.FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder project content\n")
        self.deployment = {
            "version": 1, "id": "qwen38-27b-nvfp4-v1", "model_family": "qwen3.8",
            "checkpoint": "Vendor/Qwen3.8-27B", "served_model": "qwen38-test", "revision": "a" * 40,
            "runtime": {"image": "registry/runtime@sha256:" + "b" * 64, "commit": "c" * 40},
        }
        write_json(self.root / "data/qwen38_deployment.json", self.deployment)
        write_json(self.root / "data/boundary_corrections.json", {"version": 1, "files": {}})
        self.gts, self.metadata = {}, {}
        for folder, (count, page_count) in package.DATASETS.items():
            gt, files = {}, {}
            (self.root / folder).mkdir()
            for i in range(count):
                name = f"Image_{i:03}.pdf"
                total = page_count - count + 1 if i == 0 else 1
                writer = PdfWriter()
                for _ in range(total):
                    writer.add_blank_page(width=72, height=72)
                data = io.BytesIO()
                writer.write(data)
                pdf_bytes = data.getvalue()
                (self.root / folder / name).write_bytes(pdf_bytes)
                gt[name] = [1]
                files[name] = {"sha256": package.sha256(pdf_bytes), "total_pages": total}
            self.gts[folder], self.metadata[folder] = gt, files
            write_json(self.root / folder / "ground_truth.json", gt)
            write_json(self.root / folder / "masked.json", {})
            write_json(self.root / folder / "strata.json", {name: "fresh" for name in gt})
        reference = {"version": 1, "id": "gt-v3-20", "strata": {n: "fresh" for n in self.gts["eval_full"]},
                     "ground_truth_sha256": package.canonical_hash(self.gts["eval_full"])}
        write_json(self.root / "data/eval_reference.json", reference)
        review = {"version": 1, "label_status": "human_confirmed", "files": {
            n: {"starts": self.gts["eval_gergana"][n], "source_sha256": row["sha256"],
                "total_pages": row["total_pages"]} for n, row in self.metadata["eval_gergana"].items()}}
        write_json(self.root / "data/gergana_review_v1.json", review)
        for folder in package.DATASETS:
            manifest = {"version": 1, "ground_truth_sha256": package.canonical_hash(self.gts[folder]),
                        "files": self.metadata[folder]}
            if folder == "eval_gergana":
                manifest["reference_labels_sha256"] = package.sha256((self.root / "data/gergana_review_v1.json").read_bytes())
            else:
                manifest["corrections_sha256"] = package.sha256((self.root / "data/boundary_corrections.json").read_bytes())
            write_json(self.root / folder / "dataset.json", manifest)

    def collect(self):
        return package.collect_inputs(self.root)

    def test_archive_dereferences_only_listed_pdfs_and_verifies_every_member(self):
        source = self.root / "eval_gergana/Image_000.pdf"
        original = self.root / "private_original.pdf"
        source.rename(original)
        source.symlink_to(original)
        (self.root / ".env").write_text("not for upload")
        (self.root / "eval_full/automatic_output.pdf").write_bytes(original.read_bytes())
        deployment, datasets, entries = self.collect()
        output = self.root / "package.tar.gz"
        manifest = package.build(self.root, output, deployment, datasets, entries)
        self.assertEqual(sum(row["files"] for row in datasets.values()), 25)
        self.assertEqual(sum(row["total_pages"] for row in datasets.values()), 817)
        with tarfile.open(output) as archive:
            members = archive.getmembers()
            self.assertTrue(all(m.isfile() for m in members))
            self.assertEqual(len([m for m in members if m.name.endswith(".pdf")]), 25)
            self.assertNotIn(package.ARCHIVE_ROOT + "/.env", archive.getnames())
            self.assertNotIn(package.ARCHIVE_ROOT + "/private_original.pdf", archive.getnames())
            self.assertNotIn(package.ARCHIVE_ROOT + "/eval_full/automatic_output.pdf", archive.getnames())
            self.assertEqual(archive.extractfile(package.ARCHIVE_ROOT + "/eval_gergana/Image_000.pdf").read(), original.read_bytes())
            self.assertEqual(archive.extractfile(package.ARCHIVE_ROOT + "/baseline_revision.txt").read().decode().strip(), package.BASELINE_REVISION)
        package.validate_archive(output, manifest)

    def test_replaced_source_pdf_is_rejected_against_manifest(self):
        source = self.root / "eval_full/Image_001.pdf"
        source.write_bytes(source.read_bytes() + b"\n% changed source\n")
        with self.assertRaisesRegex(ValueError, "source differs from dataset manifest"):
            self.collect()

    def test_changed_reviewed_source_is_rejected_without_dataset_manifest(self):
        (self.root / "eval_gergana/dataset.json").unlink()
        source = self.root / "eval_gergana/Image_001.pdf"
        source.write_bytes(source.read_bytes() + b"\n% changed source\n")
        with self.assertRaisesRegex(ValueError, "Source differs from human review"):
            self.collect()

    def test_changed_labels_are_rejected_against_human_reference(self):
        gt = self.gts["eval_gergana"]
        gt["Image_000.pdf"] = [1, 2]
        write_json(self.root / "eval_gergana/ground_truth.json", gt)
        with self.assertRaisesRegex(ValueError, "differs from its human review"):
            self.collect()

    def test_path_traversal_in_label_filename_is_rejected(self):
        gt = self.gts["eval_full"]
        gt["../outside.pdf"] = gt.pop("Image_000.pdf")
        write_json(self.root / "eval_full/ground_truth.json", gt)
        with self.assertRaisesRegex(ValueError, "source PDF basenames"):
            self.collect()

    def test_missing_required_runtime_file_is_rejected(self):
        (self.root / "qwen38_client.py").unlink()
        with self.assertRaisesRegex(ValueError, "Missing required package input"):
            self.collect()

    def test_live_model_or_container_tags_are_rejected(self):
        for field, value in [("revision", "main"), ("runtime", {"image": "registry/runtime:latest", "commit": "c" * 40})]:
            with self.subTest(field=field):
                deployment = {**self.deployment, field: value}
                with self.assertRaises(ValueError):
                    package.validate_deployment(deployment)

    def test_source_change_during_build_preserves_previous_archive(self):
        deployment, datasets, entries = self.collect()
        output = self.root / "package.tar.gz"
        output.write_bytes(b"previous valid archive retained")
        (self.root / "split.py").write_text("changed after input validation")
        with self.assertRaisesRegex(ValueError, "Input changed while packaging"):
            package.build(self.root, output, deployment, datasets, entries)
        self.assertEqual(output.read_bytes(), b"previous valid archive retained")
        self.assertEqual(list(self.root.glob(".qwen38-*.tar.gz")), [])

    def test_archive_verification_rejects_unlisted_member(self):
        deployment, datasets, entries = self.collect()
        output = self.root / "package.tar.gz"
        manifest = package.build(self.root, output, deployment, datasets, entries)
        altered = self.root / "altered.tar.gz"
        with tarfile.open(output) as source, tarfile.open(altered, "w:gz") as target:
            for member in source.getmembers():
                target.addfile(member, source.extractfile(member))
            package.add_bytes(target, "unexpected-secret.txt", b"not allowed")
        with self.assertRaisesRegex(ValueError, "unlisted members"):
            package.validate_archive(altered, manifest)

    def test_check_validates_without_creating_archive(self):
        with patch.object(package, "__file__", str(self.root / "scripts/package_qwen38.py")):
            self.assertEqual(package.main(["--check"]), 0)
        self.assertFalse((self.root / "experiments").exists())


if __name__ == "__main__":
    unittest.main()
