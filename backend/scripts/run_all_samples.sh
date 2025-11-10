#!/usr/bin/env bash
set -euo pipefail

# Root of the backend project (folder that contains PickSample200).
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLE_DIR="${ROOT_DIR}/PickSample200"
RESULTS_DIR="${ROOT_DIR}/results"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

if [[ ! -d "${SAMPLE_DIR}" ]]; then
  echo "Sample directory not found: ${SAMPLE_DIR}" >&2
  exit 1
fi

echo "Checking OCR service health at ${BASE_URL}/health ..."
if ! curl -fsS "${BASE_URL}/health" >/dev/null; then
  echo "OCR service is not reachable. Start the API (uvicorn) before running this script." >&2
  exit 1
fi

mkdir -p "${RESULTS_DIR}"

shopt -s nullglob
sample_files=("${SAMPLE_DIR}"/*.pdf)
shopt -u nullglob

if [[ ${#sample_files[@]} -eq 0 ]]; then
  echo "No PDF samples found in ${SAMPLE_DIR}" >&2
  exit 0
fi

echo "Processing ${#sample_files[@]} sample(s)..."

for sample_path in "${sample_files[@]}"; do
  sample_name="$(basename "${sample_path}")"
  echo "→ ${sample_name}"

  response_file="${RESULTS_DIR}/tmp_response_${sample_name}.json"

  if ! curl -fsS \
    --get \
    --data-urlencode "filename=${sample_name}" \
    --data-urlencode "include_raw=false" \
    "${BASE_URL}/ocr/extract/sample" \
    >"${response_file}"; then
    echo "  Failed to process ${sample_name}" >&2
    rm -f "${response_file}"
    continue
  fi

  if command -v jq >/dev/null 2>&1; then
    doc_filename=$(jq -r '.filename' "${response_file}" 2>/dev/null || echo "")
  else
    doc_filename=""
  fi

  rm -f "${response_file}"

  latest_saved=$(ls -t "${RESULTS_DIR}"/*.json 2>/dev/null | head -n 1)
  if [[ -n "${latest_saved}" ]]; then
    echo "  Saved: ${latest_saved}"
    if [[ -n "${doc_filename}" ]]; then
      echo "  Document filename: ${doc_filename}"
    fi
  else
    echo "  Warning: No JSON output found in ${RESULTS_DIR}; check server logs." >&2
  fi
done

echo "Done. Review generated files in ${RESULTS_DIR}."
