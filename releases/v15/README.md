# V15 — best validated variant

Git tag: **`best-v15`**. The exact frozen runtime is in `runtime/`; all 145 files
retain their SHA-256 values from `manifest.json`. `BEST_VARIANT.json` at the
repository root identifies this release. Root inference Python files also match
this snapshot. No later experimental candidate is included.

| Labeled test set | V14 exact documents | V15 exact documents | V15 boundary F1 |
| --- | ---: | ---: | ---: |
| Original 94 PDFs / 3,115 pages | 1,216 / 1,377 | **1,221 / 1,377** | 95.25% |
| Additional 82 PDFs / 1,793 pages | 705 / 845 | **708 / 845** | 93.21% |

On the earlier 44-PDF subset, V14 scored **94.00% boundary F1**, and V15 scored
**94.38%**. This subset is already included in the original 94 PDFs.
Exact-document recovery requires the complete reference page group to match;
boundary F1 measures split decisions. These are exposed development/regression
sets, so the results do not establish performance on unseen data. The sealed
holdout has not been evaluated.

The September 10 production run processed **74 originals / 1,792 pages** into
**784 PDFs** in **3h 38m 10s**, averaging **7.30 seconds/page**. Every exported
page passed content, orientation and coverage verification. That batch had no
ground truth, so it has no measured accuracy score.

`validation-summary.json` preserves the aggregate scores, cohort results, raw
archive hashes and production timing. Original PDFs, raw model logs and generated
exports remain local; they are not part of this release.

## Run the saved version

From the repository root, on the documented pinned CUDA/SGLang environment:

```bash
cd releases/v15/runtime
bash scripts/start_qwen38_server.sh --inside-container \
  --deployment data/qwen38_deployment_compact_v3.json \
  --cache-dir /workspace/qwen38-cache
```

In a separate shell using the lightweight client environment:

```bash
python releases/v15/runtime/run_production.py /path/to/input \
  --backend qwen38 --thinking off --boundary-method archive-context \
  --request-timeout 600
```

The production driver writes `split/` beside each source. The numbered `obrabN`
folders used for the September 10 delivery were an export step. Keep generated
`obrabN` folders outside future input discovery, or use `--files` to select only
original PDFs. See `runtime/docs/QWEN38.md` for server and client setup.
