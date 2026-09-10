# Qwen3.8 model comparison

Qwen3.8 is a pinned local-server inference backend. The original model swap did not improve historical boundary F1; the new thinking-off archive pipelines improve how page facts and filing conventions are applied. See [the current measured results](QWEN38_RESULTS.md) and [the investigation](QWEN38_ERROR_ANALYSIS.md). Qwen2.5 defaults remain available. The medium evaluation was stopped on 6 September; the active improvements use thinking off.

The recommended method is `--boundary-method archive-context`. `--boundary-method archive-fast` is faster, but failed the full historical accuracy gate. Its optional receipt-heading reconciliation improves one recorded error and adds no model calls; it remains below conservative accuracy. The earlier `archive` V9 and `legacy` modes remain available for reproducible comparisons. Neither mode receives reference labels in its inference prompts.

## Portable pilot package

From the local repository, validate and build the package without installing CUDA or downloading model weights:

```bash
python3 scripts/package_qwen38.py --check
python3 scripts/package_qwen38.py
```

This creates `experiments/qwen38_package.tar.gz`: 20 historical PDFs and five reviewed Gergana PDFs, 817 pages in total, plus the client, launch script, pinned deployment and labels. Its manifest hashes each payload file. Transfer that archive to persistent storage on the GPU host, then extract it and run subsequent commands from its root:

```bash
tar -xzf qwen38_package.tar.gz
cd qwen38_pilot
```

The archive includes `baseline_revision.txt` with the pinned Qwen2.5 **model-weight** revision (separate from the repository revision). The packager itself runs from the original local repository.

## Pinned GPU server

[`data/qwen38_deployment.json`](../data/qwen38_deployment.json) identifies the exact model, quantization, container and launch settings. It currently matches [`qwen38_deployment_compact_v3.json`](../data/qwen38_deployment_compact_v3.json); the first configuration is retained in [`qwen38_deployment_initial.json`](../data/qwen38_deployment_initial.json). The client uses an OpenAI-compatible HTTP endpoint; the model stays on the GPU host. No paid API service is required.

| Setting | Pilot value |
|---|---|
| GPU target | One RTX 5090, 32GB, Linux x86-64 |
| Checkpoint | `RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead` |
| Checkpoint revision | `009632fef96dd349150baa780c984e62e70e91fe` |
| Advertised model | `qwen3.8-27b-009632fe-compact-v3` |
| Runtime | SGLang in the Docker image pinned by digest in the manifest |
| Actual image build commit | `5f55db35e926d50676f75b812640ea2410b0fe0e` |
| Container CUDA | `13.0.3` |
| Minimum Linux driver checked | `580.65.06` |
| Context / concurrency | 32,768 total tokens / one request |
| KV pool cap | `--max-total-tokens 32768` (1GiB FP8 KV on the pilot GPU) |
| Endpoint | `http://127.0.0.1:8000/v1` |

The quantized checkpoint retains BF16 vision and output-head weights; its MLP uses NVFP4 and attention weights use FP8. This is a specific derivative of Qwen3.8, so its results should be named accordingly. [Checkpoint card](https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead)

The [SGLang recipe](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B) provides a single-5090 configuration with vision enabled. Our launch keeps one request, uses FP32 GDN state and disables speculative decoding. It additionally caps context, prefill chunks, image count and the KV pool. Five Mamba state slots match one request with the `extra_buffer` strategy. Upstream validation used 8,192 input / 1,024 output tokens; our two three-page smoke windows now pass. Six images are permitted per request, but their visual tokens and text must fit the total context. The smoke checks do not establish coverage of every six-page window or query type.

The first configuration exhausted GPU memory during image preprocessing: limiting context and concurrency alone still allocated a 158,422-token KV pool, about 4.84GiB. `vision-v2` adds the explicit 32,768-token pool cap, reducing KV allocation to 1GiB and leaving 5.13GiB available at server readiness on the pilot GPU. Static memory fraction remains 0.90; checkpoint, precision and graph settings are unchanged. This adjustment used runtime evidence without consulting labels.

The recipe's source-install commit differs from the build commit embedded in its Docker image. We resolved the image's Linux/amd64 digest and recorded its actual build metadata. A mutable tag is not used at launch. The launcher rejects Linux drivers older than `580.65.06` before pulling a container or loading weights, following the CUDA 13.0 GA driver level and R580 compatibility range in the [NVIDIA release notes](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-toolkit-release-notes/index.html#cuda-driver). It does not install or change host drivers. This runtime is separate from the older CUDA-12.8 baseline environment.

Allow persistent storage for approximately 23.75GB of checkpoint tensors, 14.68GB of compressed container layers plus their expanded image, datasets, logs and results. Keeping the older baseline weights needs additional space. Docker storage and the model cache can be on different volumes; both need adequate free space.

From the repository, this check is safe on the local Mac and downloads nothing:

```bash
bash scripts/start_qwen38_server.sh --check
```

On the GPU machine with Docker, NVIDIA Container Toolkit and a compatible driver already available:

```bash
bash scripts/start_qwen38_server.sh --cache-dir /workspace/qwen38-cache
```

For a rented pod that cannot run Docker internally, select this exact image in the provider's pod template:

```text
lmsysorg/sglang@sha256:b91d664a8e4825afc16ab831c6035a6c88ac20ef8bd26da4fe2b9813a9f44376
```

Inside that pod, use the same server arguments without nested Docker:

```bash
bash scripts/start_qwen38_server.sh --inside-container --check
bash scripts/start_qwen38_server.sh --inside-container --cache-dir /workspace/qwen38-cache
```

This mode checks the image's declared SGLang/CUDA environment and the host driver, then starts the server directly. It requires the pinned image to be selected already. Environment fields and the advertised model name are consistency checks, not cryptographic attestation. For a pod started this way, use Ctrl-C in the server terminal to stop it; `docker stop` below applies to the default host-Docker mode.

The launcher downloads the pinned image and weights on first use, then runs in the foreground. The cache survives container removal. `--gpu 0` selects one GPU; `--name pdf-qwen38` controls the container name. The endpoint binds only to the GPU host's loopback interface. In another terminal on that host, check readiness:

```bash
curl --fail http://127.0.0.1:8000/v1/models
```

The response must advertise `qwen3.8-27b-009632fe-compact-v3`. The client checks that advertised identity against the deployment manifest. This catches an accidentally selected server; it is not cryptographic attestation of the running weights or GPU. Retain the server logs and `nvidia-smi` output with the experiment.

For a client running on another computer, forward the endpoint over SSH rather than publishing the model server. Replace the host and port with the machine's actual SSH details:

```bash
ssh -N -L 8000:127.0.0.1:8000 -p <ssh-port> <user>@<gpu-host>
```

## Existing RunPod container

Before changing an existing Pod's image, put the archive and bootstrap on its mounted `/workspace` volume. Confirm the volume attachment and mount path; retain both in the Pod configuration. RunPod documents that image edits reset the container disk while preserving `/workspace` and network-volume data. [Pod updates](https://docs.runpod.io/pods/manage-pods)

From the extracted pilot root on the current Pod, preserve its working public SSH authorization and copy the latest bootstrap:

```bash
findmnt --target /workspace
test -s /root/.ssh/authorized_keys
install -m 0600 /root/.ssh/authorized_keys /workspace/qwen38-pod-authorized_keys
install -m 0700 scripts/bootstrap_qwen38_runpod.sh /workspace/qwen38-pod-bootstrap.sh
bash /workspace/qwen38-pod-bootstrap.sh --check
```

The preserved file contains public authorized keys; private client keys stay on the client. Use the pinned image above, retain TCP port 22, and set the Pod's **Container start command** to:

```text
/bin/bash /workspace/qwen38-pod-bootstrap.sh
```

This command overrides the image's CMD while retaining its NVIDIA entrypoint. The bootstrap restores SSH authorization, generates a fresh Pod host key, checks the SSH configuration and keeps SSH running in the foreground. It appends startup logs to `/workspace/qwen38-pod-bootstrap.log`; model startup remains a separate step. [RunPod start commands](https://docs.runpod.io/pods/templates/manage-templates)

After the reset, obtain the current connection details from RunPod. Its basic SSH proxy supports terminal access; SCP/SFTP require direct SSH over an exposed TCP port. Run the client and server on the Pod to use the loopback endpoint without forwarding. [SSH methods](https://docs.runpod.io/pods/configuration/use-ssh)

An SSH shell may omit the image's runtime environment. Restore only an allowlist of actual values from `/proc/1/environ`: `PATH`, `CUDA_HOME`, `CUDA_VERSION`, `SGLANG_BUILD_COMMIT` and `LD_LIBRARY_PATH`. Avoid printing or copying the entire environment, and do not invent values to satisfy the launcher. `/opt/sglang/bin/python3` selects the image's server environment explicitly. Then use the `--inside-container` launcher commands above and retain the server log on `/workspace`.

## Fixed comparison

The client needs Poppler and Tesseract with OSD data. On an Ubuntu GPU host these system dependencies can be installed with `sudo apt-get update` followed by `sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-osd`. Create a lightweight client environment:

```bash
python3 -m venv .venv-client
source .venv-client/bin/activate
python -m pip install -r requirements-qwen38-client.txt
```

The Qwen3.8 HTTP client itself uses Python's standard library. No local CUDA installation is needed for packaging, CPU checks or the HTTP client. Validate smoke-test inputs before requesting a GPU:

```bash
python smoke_qwen38.py eval_full --run-dir experiments/qwen38-smoke-off --check
```

## Current thinking-off archive commands

Use a separate result directory for each method:

```bash
python eval_boundaries.py eval_full --backend qwen38 --thinking off --boundary-method archive-context --request-timeout 600 --run-dir experiments/archive-context
python eval_boundaries.py eval_full --backend qwen38 --thinking off --boundary-method archive-fast --request-timeout 600 --run-dir experiments/archive-fast
python run_production.py /path/to/originals --backend qwen38 --thinking off --boundary-method archive-context --request-timeout 600
```

Consult the results report before choosing the fast method. Repeating a command
resumes identity-matched work. Run model comparisons sequentially when measuring
throughput. The server and rented Pod have separate lifecycles; stopping a Python
client or the model server does not itself stop Pod billing.

## Historical OFF/medium pilot reproduction

The following commands preserve the original comparison workflow. They are not
required for the new thinking-off archive methods; the medium investigation was
stopped at the user's request.

The pilot runner executes both smoke modes, then evaluates both datasets in each mode and writes strict scores. It runs all ten stages sequentially and stops on the first failure. With the server ready and `.venv-client` active:

```bash
python scripts/run_qwen38_pilot.py --run-dir experiments/qwen38-pilot --check
python scripts/run_qwen38_pilot.py --run-dir experiments/qwen38-pilot
```

Medium thinking now defaults to **16,384 completion tokens**, covering reasoning plus the final answer; thinking off remains at 4,096. To rerun only medium mode with the larger allowance, preserving completed off results:

```bash
python scripts/run_qwen38_pilot.py --thinking medium \
  --medium-max-completion-tokens 16384 \
  --run-dir experiments/qwen38-pilot-medium16k-20260906
```

This runs one smoke stage, both datasets, and their two strict scores. The former 8,192-token configuration remains reproducible with `--medium-max-completion-tokens 8192`. A new completion cap requires new medium checkpoints; do not combine predictions from the two budgets. The server context remains 32,768 tokens, shared by text/images and generated output. A larger allowance reduces the chance of truncation but does not guarantee completion.

Its request timeout defaults to **600 seconds**, allowing for cold kernel compilation and reasoning; standalone client commands default to 180 seconds. Use `--request-timeout` to choose another value before starting a run. The runner records `pilot_status.json`, separate stage results and `stage_logs/attempt-NNN/*.log` beneath its run directory. Repeating the same command rechecks the child checkpoints before reusing completed results; changed inputs or settings require a new directory. Server and Pod lifecycle remain under the operator's control. Run the Qwen2.5 baseline below after stopping the Qwen3.8 server.

For individual stages, use the following commands with separate directories from the runner's results.

Once the server is ready, run the two-window smoke test. It uses the first three-page window and the three-page window containing the largest PDF page by media-box area; labels are not read. It checks real image handling, JSON structure and page references, and saves rotations, final responses and usage. This is a runtime check, not an accuracy score:

```bash
python smoke_qwen38.py eval_full --thinking off \
  --run-dir experiments/qwen38-smoke-off
python smoke_qwen38.py eval_full --thinking medium --max-completion-tokens 16384 \
  --run-dir experiments/qwen38-smoke-medium
```

Check memory use, response truncation and malformed JSON before the full benchmark. Keep a separate result directory for every configuration:

```bash
python eval_boundaries.py eval_full --backend qwen38 \
  --endpoint http://127.0.0.1:8000/v1 \
  --deployment data/qwen38_deployment.json \
  --thinking off --max-completion-tokens 4096 \
  --run-dir experiments/qwen38-full-off

python eval_boundaries.py eval_full --backend qwen38 \
  --endpoint http://127.0.0.1:8000/v1 \
  --deployment data/qwen38_deployment.json \
  --thinking medium --max-completion-tokens 16384 \
  --run-dir experiments/qwen38-full-medium

python score_full.py eval_full experiments/qwen38-full-off/eval_results.json
python score_full.py eval_full experiments/qwen38-full-medium/eval_results.json
```

Repeat the comparison on `eval_gergana`, changing `--run-dir` accordingly. Compare with a fresh Qwen2.5 baseline using the same datasets and rendering, with EVN post-processing and aligned confirmation disabled in both. Stop the Qwen3.8 server before loading the older model on the same card:

```bash
docker stop pdf-qwen38
```

Run the baseline on the Linux GPU host, in its own environment. In inside-container mode, stop the foreground server first instead of using `docker stop`. Then:

```bash
python3 -m venv .venv-baseline
source .venv-baseline/bin/activate
python -m pip install -r requirements.txt
export HF_HOME=/workspace/qwen25-cache
export HF_HUB_DISABLE_XET=1
read -r qwen25_revision < baseline_revision.txt
python eval_boundaries.py eval_full --backend hf --revision "$qwen25_revision" \
  --run-dir experiments/qwen25-full-baseline
python eval_boundaries.py eval_gergana --backend hf --revision "$qwen25_revision" \
  --run-dir experiments/qwen25-gergana-baseline
python score_full.py eval_full experiments/qwen25-full-baseline/eval_results.json
python score_full.py eval_gergana experiments/qwen25-gergana-baseline/eval_results.json
```

The baseline dependencies belong on the GPU host, not the local Mac. Keep the two model processes separate to avoid exhausting GPU memory. Reactivate `.venv-client` for subsequent Qwen3.8 HTTP runs.

Report strict boundary precision/recall/F1, exact documents, per-source errors, elapsed time, calls and response-token usage. The existing `eval_full` cases have already informed development. The separately reviewed Gergana set provides another filing pattern, but should not be called unseen once its examples influence changes. Check changed seams and both datasets before selecting a winner.

## Thinking and response limits

The [official model card](https://huggingface.co/Qwen/Qwen3.8-27B) and the pinned checkpoint's chat template support thinking off or `low`, `medium`, and `xhigh` effort. Upstream defaults to thinking at `xhigh`; the pilot server defaults to thinking off. Each client request explicitly selects its mode. A thinking request must set `enable_thinking=true` as well as its effort. Requests use `preserve_thinking=false`; each page window is independent.

The completion cap covers generated reasoning and the final JSON. It is separate from the old detector's short per-query JSON allowance. A truncated response must be treated as an incomplete query, not a valid negative boundary decision. Reasoning effort is a model instruction, not a hard numeric token budget. Keep the chosen effort, sampling settings and cap fixed and recorded throughout each comparison.

Qwen3.8 queries use server-side constrained decoding: `response_format.type=json_schema`, with every query field required, its native JSON type specified, confidence bounded to 0–100, and additional properties disabled. Nullable style fields remain nullable. The schema is derived from the same field definitions used by the local validator. The pinned SGLang API forwards this schema to its grammar sampler and handles reasoning separately through its configured Qwen parser. No decision values or ground-truth labels are supplied by the schema.

Local validation remains mandatory. Format repair and OFF truncation recovery share one budget, with at most two calls total. A completed answer with invalid JSON/fields gets a required-fields/types reminder with the same images and schema. An OFF answer ending with `finish_reason=length` gets one retry using the original prompt and images, with hard string limits: 160 characters for heading fields and 256 for other strings. Recovery confidence is constrained to whole percentages 0–100. The token cap, sampling and seed stay fixed. No prior answer, reasoning, labels or boundary verdict is supplied to either retry.

These limits address observed repeated `\u00a0` escapes inside a heading; the external compact-JSON whitespace setting alone cannot stop that loop. The pinned XGrammar build was checked to support the string limits, and a live bounded probe completed the failing window in 5.21 seconds. Repeated OFF truncation still fails closed. Transport errors, timeouts, absent finals, ambiguous thinking blocks and medium truncations propagate. Runtime identity records `response_recovery=format_or_bounded_off_length_once_v3`, alongside schema version, retry count and code hashes. Both failed and successful attempts count toward model/token usage.

The 11 original prompt constructions and the HF inference/parsing path remain unchanged. These are comparisons of recorded model configurations, including response validation and sampling. Legacy off mode uses temperature 0.7/top-p 0.8/presence penalty 1.5; thinking modes use 1.0/0.95/0.0. Those paths use top-k 20. The archive methods use positional image labels and greedy decoding: temperature 0, top-p 1, top-k 1, presence penalty 0. All use seed 0. The seed does not guarantee identical outputs across runtimes or GPUs.

Per-PDF and archive seam checkpoints record model calls and available token counts. Missing usage stays unknown. Failed evaluation attempts remain in `run.json`, and archive seam histories retain their attempts. On a resumed source, `processing_seconds` does not include earlier failed-source work; use cumulative seam accounting and controller attempt times for complete run-time comparisons. None of these is total Pod rental cost.

## Historical runtime checks

The launcher has passed Bash syntax, local dry-run and mocked driver-preflight checks. Every server argument was matched against the pinned SGLang source; decode graph batch size and prefill graphs are separate controls. Registry metadata identifies the image entrypoint as NVIDIA's wrapper with no default command, so the launch does not duplicate `python3`. Model revision, vision configuration, chat-template controls, container digest and image build metadata were inspected before loading weights. The pinned image started on an RTX 5090 with matching imported versions: PyTorch `2.13.0+cu130`, SGLang `0.0.0.dev1+g5f55db35e`, Transformers `5.12.1`.

On 2026-09-05, after the initial image-preprocessing OOM and KV-pool adjustment, the first `vision-v2` smoke runs produced the following results, retained locally in the [off smoke record](../experiments/qwen38_gpu_20260905/qwen38-pilot-vision-v2-20260905/smoke-off/smoke_results.json) and [medium smoke record](../experiments/qwen38_gpu_20260905/qwen38-pilot-vision-v2-20260905/smoke-medium/smoke_results.json). These runtime evidence files are separate from the portable pilot archive.

| Mode / completion cap | Three-page queries passed | Aggregate model-call time | Input tokens | Output tokens | Reasoning tokens included in output |
|---|---|---|---|---|---|
| Off / 4,096 | 2/2 | 7.12s | 15,356 | 214 | 0 |
| Medium / 8,192 | 2/2 | 29.44s | 15,352 | 1,712 | 1,509 |

These timings cover two model calls per mode, excluding server startup and PDF preprocessing. They establish image handling and valid responses for those windows, not accuracy or representative throughput. The first full-benchmark attempt then stopped on a missing `signal_on_page` field in the first PDF's response, before the bounded format-repair policy above was added. At that stage there was no completed full-benchmark accuracy result. Later completed results are in the linked results report.

The prompt-only format retry subsequently failed twice on page 23 of `Image_00112022025164052657.pdf` (context pages 22–24), after two completed PDFs / 60 pages. Restarting unchanged reproduced the omission. The constrained-decoding correction uses a new benchmark directory, `qwen38-pilot-schema-v1-20260905`; earlier results remain separate because generation changed. Its regression check uses that exact PDF window, actual 150-DPI rendering and rotation, repeated end queries and a nullable style query in both off and medium modes. Regression records are runtime evidence, not ground-truth accuracy measurements.

## Medium token-limit and whitespace correction (2026-09-06)

The original 8,192-token medium run stopped during title transcription on page 6 of `Image_00112022025164052657.pdf`. A 16,384-token diagnostic reproduced a length stop: 917 reasoning tokens, followed by a final answer of 176,148 characters, predominantly blank lines after a title string. Merely doubling the allowance did not fix this sample.

The pinned SGLang xgrammar backend supports `--constrained-json-disable-any-whitespace`, which compiles schemas with `any_whitespace=False`. The new `compact-v3` deployment enables this flag and explicitly selects xgrammar. It constrains syntactic JSON formatting without removing spaces inside document titles or changing detector prompts. The 16,384-token completion allowance is retained. The earlier deployment manifests and results remain available; new medium results must retain the changed deployment identity.
