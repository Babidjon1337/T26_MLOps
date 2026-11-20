"""Bounded HTTP contract smoke test against a deployed service."""

import argparse
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def check(base_url: str, source_commit: str) -> dict:
    for route in ("/healthz", "/readyz"):
        with urllib.request.urlopen(base_url + route, timeout=15) as response:
            assert response.status == 200
    request = urllib.request.Request(
        base_url + "/predict",
        data=json.dumps({"dep_hour": 14, "is_weekend": 0}).encode(),
        headers={"Content-Type": "application/json", "X-Request-ID": "team3-k8s-smoke"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        prediction = json.load(response)
        assert response.headers["X-Request-ID"] == "team3-k8s-smoke"
    assert 0 <= prediction["delay_probability"] <= 1
    assert prediction["model_version"] == "0.2.0"
    with urllib.request.urlopen(base_url + "/metrics", timeout=15) as response:
        metrics = response.read().decode()
    assert f'source_commit="{source_commit}"' in metrics
    assert "prediction_probability_count" in metrics
    return {
        "passed": True,
        "checked_at": datetime.now(UTC).isoformat(),
        "source_commit": source_commit,
        "prediction": prediction,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = check(args.base_url.rstrip("/"), args.source_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
