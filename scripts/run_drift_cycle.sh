#!/usr/bin/env bash
# Reproducible scheduled LR12 drill. It registers a candidate, never promotes it.
set -euo pipefail
output=${DRIFT_OUTPUT_DIR:-reports/drift-retraining}
mkdir -p "$output"
python -m mlops_flight_delay.drift_retrain \
  --reference "${REFERENCE_DATA:-data/monitoring/reference.csv}" \
  --current "${CURRENT_DATA:-data/monitoring/current.csv}" \
  --training "${TRAINING_DATA:-data/flights_sample.csv}" \
  --policy monitoring/drift_retrain_lab.json \
  --candidate-dir models/drift-candidates \
  --output "$output/drift_report.json"
candidate=$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("candidate_model", ""))' "$output/drift_report.json")
candidate_id=$(python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("candidate_id", ""))' "$output/drift_report.json")
registered_id=""
if [[ -f "$output/registry-candidate.json" ]]; then
  registered_id=$(python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("drift_candidate_id", ""))' "$output/registry-candidate.json")
fi
if [[ -n "$candidate" && "$candidate_id" != "$registered_id" ]]; then
  # The sample has only 24 rows: gate 0.0 tests mechanics, not model quality.
  # Mature BTS quality evaluation and independent champion approval stay separate.
  python -m mlops_flight_delay.registry register \
    --tracking-uri "${MLFLOW_TRACKING_URI:-sqlite:///$output/mlflow.db}" \
    --experiment team3-skif-lr12-candidate-drill \
    --model-name team3-skif-drift-candidates --owner-team team-3 \
    --registered-by "${GITHUB_ACTOR:-ESKoVV}" \
    --model "$candidate" --data "${TRAINING_DATA:-data/flights_sample.csv}" \
    --summary "${candidate%/*}/summary.json" \
    --source-commit "$(git rev-parse HEAD)" --minimum-roc-auc 0.0 \
    --output "$output/registry-candidate.json"
  python -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["drift_candidate_id"]=sys.argv[2]; open(p,"w").write(json.dumps(d,indent=2))' "$output/registry-candidate.json" "$candidate_id"
fi
