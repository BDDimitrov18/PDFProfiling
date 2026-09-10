#!/bin/bash
# Retry using the current process exit status, never text from an old log.
# Usage: bash supervisor.sh /workspace/GIS_Pv [run_production.py options]
set -u
cd "$(dirname "$0")" || exit 1
root=${1:-/workspace/GIS_Pv}
if [ "$#" -gt 0 ]; then shift; fi
export HF_HOME=${HF_HOME:-/root/hf_cache} HF_HUB_DISABLE_XET=1
attempts=${PRODUCTION_ATTEMPTS:-80}
delay=${PRODUCTION_RETRY_SECONDS:-15}
python_bin=${PRODUCTION_PYTHON:-python3}
for ((attempt=1; attempt<=attempts; attempt++)); do
  echo "Production attempt $attempt/$attempts $(date -u +%FT%TZ)"
  "$python_bin" run_production.py "$root" "$@"
  result=$?
  if [ "$result" -eq 0 ]; then exit 0; fi
  if [ "$result" -eq 2 ] || [ "$result" -ge 128 ]; then exit "$result"; fi
  if [ "$attempt" -lt "$attempts" ]; then sleep "$delay"; fi
done
echo "Production failed after $attempts attempts" >&2
exit 1
