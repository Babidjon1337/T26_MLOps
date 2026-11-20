"""SKIF LR12: detect PSI drift and automatically train an isolated candidate.

The accepted training snapshot is explicit. An unlabelled monitoring window is
never used as training data, and this job cannot change the serving champion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd

from mlops_flight_delay.monitoring import build_drift_report
from mlops_flight_delay.train import train_model


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_check(
    *,
    reference: Path,
    current: Path,
    training: Path,
    policy_path: Path,
    candidate_dir: Path,
    output: Path,
) -> dict:
    policy = json.loads(policy_path.read_text())
    drift = build_drift_report(pd.read_csv(reference), pd.read_csv(current), policy)
    report = {
        "schema_version": "1.0.0",
        "checked_at": datetime.now(UTC).isoformat(),
        "drift": drift,
        "automatic_promotion": False,
        "action": "no_retraining",
    }
    if drift["status"] == "alert" and policy.get("automatic_retraining", False):
        hashes = {
            name: sha256_file(path)
            for name, path in (
                ("reference", reference),
                ("current", current),
                ("training", training),
                ("policy", policy_path),
            )
        }
        fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        candidate = candidate_dir / fingerprint / "model.joblib"
        manifest = candidate.with_name("candidate.json")
        reused = False
        if candidate.exists() and manifest.exists():
            previous = json.loads(manifest.read_text())
            reused = previous.get("model_sha256") == sha256_file(candidate)
        if not reused:
            # train_model validates labels and chronological split before writing a bundle.
            score = train_model(training, candidate)
            bundle = joblib.load(candidate)
            metadata = {
                "candidate_id": fingerprint,
                "inputs_sha256": hashes,
                "model_sha256": sha256_file(candidate),
                "validation_roc_auc": score,
                "state": "candidate_requires_review",
            }
            manifest.write_text(json.dumps(metadata, indent=2))
            summary = {
                "passed": True,
                "metrics": bundle["validation_metrics"],
                "evaluation_split": "validation",
                "prepared_sha256": hashes["training"],
            }
            candidate.with_name("summary.json").write_text(json.dumps(summary, indent=2))
        report.update(
            {
                "action": "candidate_reused" if reused else "candidate_trained",
                "candidate_id": fingerprint,
                "candidate_model": candidate.as_posix(),
                "candidate_manifest": manifest.as_posix(),
                "model_sha256": sha256_file(candidate),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "current", "training", "policy", "candidate-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = run_check(
        reference=args.reference,
        current=args.current,
        training=args.training,
        policy_path=args.policy,
        candidate_dir=args.candidate_dir,
        output=args.output,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
