#!/bin/bash
# Self-healing PRODUCTION supervisor (used for the GIS_Pv run, 2026-06-17).
# Re-runs run_production.py until all PDFs are done; per-PDF resume skips completed ones.
# Outputs + log live on the PERSISTENT /workspace volume so a pod death loses nothing.
# Launch detached:  setsid bash /workspace/supervisor.sh >/tmp/sup_wrap.log 2>&1 </dev/null &
cd /root/PdfCategorization || exit 1
export HF_HOME=/root/hf_cache HF_HUB_DISABLE_XET=1
for attempt in $(seq 1 80); do
  grep -q "PRODUCTION_DONE " /workspace/prod.log 2>/dev/null && break
  echo "=== supervisor attempt $attempt $(date -u +%H:%M:%S) ===" >> /workspace/prod.log
  python3 run_production.py /workspace/GIS_Pv >> /workspace/prod.log 2>&1
  sleep 15
done
echo "SUPERVISOR_EXIT $(date -u)" >> /workspace/prod.log
