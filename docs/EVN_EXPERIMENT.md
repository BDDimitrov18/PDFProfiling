# Selective EVN experiment, version 1

The next GPU run is a **12-page diagnostic**. It tests whether the model can
transcribe enough literal heading and issuer evidence to apply the existing
human rule: EVN “Търговски условия” is a section within a document.

Codex can perform the setup, transfer, execution, and result review after the user
provides SSH access. The user does not need to install these dependencies or
label more documents. The commands below record how the experiment runs.

## Frozen scope and evidence

`data/evn_probe_v1.json` fixes two required suppressions, nine keep controls, and
one observation across four original PDFs. Only the old 20-source benchmark was
used to choose them. The separate reviewed validation batch was not used to
select cases or tune the rule.

The experimental matcher requires an exact “Търговски условия” heading and a
separate literal issuer field identifying EVN/ЕВН on the same page. It permits
only the normalization documented in the specification and `evn_sections.py`.
Missing or ambiguous evidence preserves the candidate boundary. Page 1 is always
preserved. This experiment does not enable the separate confirmation-alignment
change and does not alter production behavior.

Historical R7-only replay removed two false cuts: `164505881` page 9 and
`145428614` page 66. Old-benchmark F1 changed from 89.0966% to 89.375%; exact
document recovery remained 252/335. That used an older, broader matcher and
cached whole-corpus extraction. **It is not a measured gain for this new
extractor, and it is not evidence of generalization.**

## Machine and package

Use an NVIDIA **RTX 5090 with 32 GB VRAM** ([official specifications](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/)), at least **64 GB system RAM**, and
**160 GB persistent disk**, with a CUDA 12.8 compatible driver and Python 3.11.
Use a persistent workspace so interrupted downloads and completed page
checkpoints survive. Other GPU architectures need a fresh baseline on that same
machine. No model has been loaded locally to establish CUDA compatibility.

After local code and tests are final, build the allowlisted archive:

```bash
python3 scripts/package_evn_probe.py --check
python3 scripts/package_evn_probe.py
```

The ignored `experiments/evn_probe_package.tar.gz` contains the required code,
requirements, this runbook, the frozen specification, and four original PDFs as
regular files in `probe_sources/`. It also includes `manifest.json` with source
and packaged SHA-256 hashes and this exact model/processor revision in
`model_revision.txt`:

```text
7cfb30d71a1f4f49a57592323337a4a4727301da
```

Revision provenance: [the pinned Qwen model commit](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct/commit/7cfb30d71a1f4f49a57592323337a4a4727301da).

The package contains no model weights, historical output logs, credentials, or
external validation PDFs. The builder validates source hashes, PDF page counts,
the 12-case schema, and every archive member. It does not download or load a
model. Its default output is replaced only after archive verification succeeds.

## Remote setup and checks

Place the archive in the machine's persistent workspace, for example
`/workspace`. These commands run on the GPU machine:

```bash
cd /workspace
tar -xzf evn_probe_package.tar.gz
cd evn_probe

python3.11 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path.cwd().resolve()
manifest = json.loads(Path('manifest.json').read_text())
assert manifest['schema_version'] == 1
assert manifest['experiment_id'] == 'evn-selective-probe-v1'
for row in manifest['contents']:
    path = root / row['path']
    assert path.resolve().is_relative_to(root) and not path.is_symlink()
    data = path.read_bytes()
    assert len(data) == row['bytes']
    assert hashlib.sha256(data).hexdigest() == row['packaged_sha256']
assert Path('model_revision.txt').read_text().strip() == manifest['model_revision']
print('Package hashes verified')
PY

apt-get update
apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-osd
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
mkdir -p environment
python -m pip freeze > environment/pip-freeze.txt
nvidia-smi > environment/nvidia-smi.txt
tesseract --list-langs > environment/tesseract-languages.txt
```

Python 3.11 and its `venv` support must already be present in the chosen machine
image. The pinned stack includes PyTorch 2.8.0 and torchvision 0.23.0 CUDA 12.8
wheels, a pairing listed by [PyTorch's official installation reference](https://pytorch.org/get-started/previous-versions/).
The model revision is shared by the model and processor. Pinning does not prove
that every inference dependency works on the target GPU; the checks and small
probe establish that before longer evaluation.

Run this preflight **before downloading model weights**:

```bash
python - <<'PY'
import json, sys
from pathlib import Path
import torch, torchvision, transformers, bitsandbytes, accelerate
import PIL, pytesseract
from run_production import preflight
preflight()
assert sys.version_info[:2] == (3, 11), sys.version
assert torch.__version__ == '2.8.0+cu128', torch.__version__
assert torchvision.__version__ == '0.23.0+cu128', torchvision.__version__
assert torch.version.cuda == '12.8', torch.version.cuda
assert torch.cuda.is_available(), 'CUDA is unavailable'
device = torch.cuda.get_device_properties(0)
assert device.total_memory >= 30 * 1024**3, 'Expected a GPU with at least 32 GB nominal VRAM'
value = (torch.ones(8, device='cuda') * 2).sum().item()
assert value == 16
record = {'python': sys.version, 'torch': torch.__version__,
          'torchvision': torchvision.__version__, 'cuda': torch.version.cuda,
          'gpu': device.name, 'vram_bytes': device.total_memory,
          'transformers': transformers.__version__, 'pillow': PIL.__version__}
Path('environment/cuda-preflight.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
PY
```

If package installation, imports, CUDA allocation, or system-tool checks fail,
resolve that failure before starting inference. Record any changed dependency
pins and use a fresh run directory and environment baseline.

## Run only the initial probe, then review

```bash
export HF_HOME=/workspace/hf_cache
export HF_HUB_DISABLE_XET=1
read -r EVN_MODEL_REVISION < model_revision.txt
python run_evn_experiment.py probe probe_sources \
  --spec data/evn_probe_v1.json \
  --revision "$EVN_MODEL_REVISION" \
  --dpi 150 \
  --run-dir experiments/evn_probe_v1
```

This first inference command downloads the pinned model into the persistent
cache if necessary. It requests one marker transcription for each of the 12
frozen pages. Rotation uses the existing local OCR path. Per-page checkpoints
allow the identical command to resume without repeating completed requests.

**Stop after the probe.** Codex reviews `probe_results.json`, every raw response
under `pages/`, the recorded rotations, and `run.json` before proceeding. Passing
requires both target suppressions, all nine keep controls, no failed calls, and
valid transcription output. The page-51 observation is reported separately.
Inspect any unexpected absence or longer heading instead of changing the prompt
or matcher during the run. Any revised approach gets a new version, expectations,
package, and run directory.

The specification also records an optional 92-candidate context check on the
two target PDFs. The current runner has **no command for that intermediate
stage**. Do not substitute the 12-page probe result for it. It can be implemented
as a separately recorded follow-up, or the next validation can cover all
candidates in the full old benchmark.

## Later paired evaluation, after the probe review

The initial package contains only four probe sources. Before the following
commands, Codex must transfer the complete, physically dereferenced `eval_full`
and `eval_gergana` datasets with their unchanged ground-truth, mask, and stratum
files, and verify the source hashes. Keep the code, dependency versions, model
revision, GPU, and DPI fixed. Do not enable `--align-confirmation`.

First produce a fresh full-pipeline baseline on the historical 20 sources, then
apply the frozen rule to every proposed start from that baseline:

```bash
python eval_boundaries.py eval_full \
  --revision "$EVN_MODEL_REVISION" --dpi 150 --tolerance 0 \
  --run-dir experiments/evn_full_baseline_v1
python run_evn_experiment.py apply eval_full \
  --revision "$EVN_MODEL_REVISION" --dpi 150 \
  --baseline-dir experiments/evn_full_baseline_v1 \
  --run-dir experiments/evn_full_candidate_v1
```

Review all changed starts, strict boundary F1 and exact-document recovery by
stratum, plus extra model calls and elapsed time in `comparison.json`. The
recorded timings cover successful processing, including rendering and source
hash checks; they exclude model loading and failed attempts and do not measure
total GPU billing time. The
candidate must not remove a true start or regress any stratum. A positive old
benchmark delta is insufficient for adoption because those errors informed the
rule.

If those checks justify continuation, run the separately reviewed validation
batch in the same environment without adapting the rule to its labels:

```bash
python eval_boundaries.py eval_gergana \
  --revision "$EVN_MODEL_REVISION" --dpi 150 --tolerance 0 \
  --run-dir experiments/evn_gergana_baseline_v1
python run_evn_experiment.py apply eval_gergana \
  --revision "$EVN_MODEL_REVISION" --dpi 150 \
  --baseline-dir experiments/evn_gergana_baseline_v1 \
  --run-dir experiments/evn_gergana_candidate_v1
```

Compare the two freshly measured versions. Existing automatic outputs are not
a same-environment baseline. Report unchanged results and zero EVN coverage if
the batch contains no applicable cases; that cannot establish benefit or broad
safety. Keep the candidate experimental until the full evidence and processing
cost justify adoption. Save and transfer the result directories before shutting
down the GPU machine.
