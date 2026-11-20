import json
from pathlib import Path

import pytest

from mlops_flight_delay.drift_retrain import run_check

ROOT = Path(__file__).parents[1]


def _args(tmp_path: Path) -> dict:
    return {
        "reference": ROOT / "data/monitoring/reference.csv",
        "current": ROOT / "data/monitoring/current.csv",
        "training": ROOT / "data/flights_sample.csv",
        "policy_path": ROOT / "monitoring/drift_retrain_lab.json",
        "candidate_dir": tmp_path / "candidates",
        "output": tmp_path / "report.json",
    }


def test_stationary_window_does_not_train(tmp_path: Path) -> None:
    args = _args(tmp_path)
    args["current"] = args["reference"]
    report = run_check(**args)
    assert report["drift"]["status"] == "ok"
    assert report["action"] == "no_retraining"
    assert not args["candidate_dir"].exists()


def test_drift_trains_once_and_reuses_verified_candidate(tmp_path: Path, monkeypatch) -> None:
    args = _args(tmp_path)
    report = run_check(**args)
    assert report["drift"]["status"] == "alert"
    assert report["action"] == "candidate_trained"
    assert report["automatic_promotion"] is False
    candidate = Path(report["candidate_model"])
    assert candidate.is_file()
    assert json.loads(candidate.with_name("summary.json").read_text())["passed"]

    def forbidden(*args, **kwargs):
        pytest.fail("unchanged input retrained instead of reusing verified candidate")

    monkeypatch.setattr("mlops_flight_delay.drift_retrain.train_model", forbidden)
    repeated = run_check(**args)
    assert repeated["action"] == "candidate_reused"
    assert repeated["model_sha256"] == report["model_sha256"]


def test_disabled_policy_blocks_automatic_training(tmp_path: Path) -> None:
    args = _args(tmp_path)
    args["policy_path"] = tmp_path / "disabled.json"
    policy = json.loads((ROOT / "monitoring/drift_retrain_lab.json").read_text())
    policy["automatic_retraining"] = False
    args["policy_path"].write_text(json.dumps(policy))
    assert run_check(**args)["action"] == "no_retraining"
    assert not args["candidate_dir"].exists()


def test_unlabelled_training_fails_without_publishing_candidate(tmp_path: Path) -> None:
    args = _args(tmp_path)
    args["training"] = args["current"]
    with pytest.raises(ValueError, match="столбцы"):
        run_check(**args)
    assert not list(tmp_path.rglob("model.joblib"))
    assert not args["output"].exists()
