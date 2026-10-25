"""Owner: Member 3 — Tests for drift detection, continuous training, and model promotion."""

from src.drift.drift_check import run_drift_analysis
from src.drift.promote import promote_model
from src.ingest.synthetic import generate_synthetic_data


def test_drift_detected_on_shifted_data():
    """Verify drift detector flags drift when PM pollutants are artificially inflated."""
    ref_df = generate_synthetic_data(cities=["delhi"], days=15, seed=42)
    shifted_df = ref_df.copy()
    shifted_df["pm25"] = shifted_df["pm25"] * 3.5 + 50.0
    shifted_df["pm10"] = shifted_df["pm10"] * 3.0 + 50.0
    shifted_df["aqi"] = shifted_df["aqi"] * 2.5 + 30.0

    res = run_drift_analysis(
        reference_df=ref_df, current_df=shifted_df, drift_threshold=0.20
    )
    assert res["drift_detected"] is True
    assert res["share_drifted"] > 0.20
    assert "pm25" in res["drifted_features"] or "aqi" in res["drifted_features"]


def test_drift_not_detected_on_identical_data():
    """Verify drift detector reports stable data on identical or lightly perturbed distribution."""
    ref_df = generate_synthetic_data(cities=["delhi"], days=15, seed=42)
    curr_df = ref_df.copy()

    res = run_drift_analysis(
        reference_df=ref_df, current_df=curr_df, drift_threshold=0.30
    )
    assert res["drift_detected"] is False
    assert res["share_drifted"] == 0.0


def test_promotion_promotes_when_challenger_is_better(tmp_path):
    """Verify challenger is promoted when challenger MAE < champion MAE."""
    decision_file = tmp_path / "decision.json"
    decision = promote_model(
        challenger_mae=14.2,
        champion_mae=21.5,
        challenger_version="3",
        champion_version="2",
        output_decision_path=decision_file,
    )
    assert decision["promoted"] is True
    assert decision["challenger_version"] == "3"
    assert "better" in decision["reason"].lower()


def test_promotion_rejects_when_challenger_is_worse(tmp_path):
    """Verify champion is retained when challenger MAE >= champion MAE."""
    decision_file = tmp_path / "decision.json"
    decision = promote_model(
        challenger_mae=25.8,
        champion_mae=19.1,
        challenger_version="4",
        champion_version="3",
        output_decision_path=decision_file,
    )
    assert decision["promoted"] is False
    assert decision["champion_version"] == "3"
    assert (
        "retaining" in decision["reason"].lower()
        or "did not improve" in decision["reason"].lower()
    )
