"""G2 matching honesty — thresholds, empty candidates, queue statuses."""

from unittest.mock import patch
from uuid import uuid4

from app.schemas import MatchCandidate
from app.services.matcher import (
    apply_candidate_honesty,
    decide_match_band,
    resolve_match_thresholds,
    staff_queue_statuses,
)


def _cand(score: float) -> MatchCandidate:
    return MatchCandidate(
        dog_id=uuid4(),
        dog_name="Test",
        breed="Unknown",
        color="Unknown",
        similarity_score=score,
        matched_image_url="/uploads/x.jpg",
        profile_photo_url=None,
        status="registered",
    )


def test_normal_bands():
    with patch("app.services.matcher.settings") as cfg:
        cfg.MATCH_STRICT_DEMO = False
        cfg.MATCH_THRESHOLD = 0.56
        cfg.MATCH_THRESHOLD_LOW = 0.51
        found, band, status = decide_match_band(0.70)
        assert found and band == "likely" and status == "matched"
        found, band, status = decide_match_band(0.53)
        assert found and band == "possible" and status == "possible_match"
        found, band, status = decide_match_band(0.40)
        assert not found and band == "none" and status == "no_match"


def test_strict_demo_disables_possible():
    with patch("app.services.matcher.settings") as cfg:
        cfg.MATCH_STRICT_DEMO = True
        cfg.MATCH_THRESHOLD_STRICT = 0.60
        cfg.MATCH_THRESHOLD = 0.56
        cfg.MATCH_THRESHOLD_LOW = 0.51
        t_high, t_low, allow = resolve_match_thresholds()
        assert t_high == 0.60 and t_low == 0.60 and allow is False
        found, band, status = decide_match_band(0.55, t_high=t_high, t_low=t_low, allow_possible=allow)
        assert not found and band == "none"
        found, band, status = decide_match_band(0.61, t_high=t_high, t_low=t_low, allow_possible=allow)
        assert found and band == "likely"


def test_staff_queue_likely_only_in_strict():
    with patch("app.services.matcher.settings") as cfg:
        cfg.MATCH_STRICT_DEMO = True
        cfg.MATCH_QUEUE_LIKELY_ONLY = False
        assert staff_queue_statuses() == ("matched",)
        cfg.MATCH_STRICT_DEMO = False
        cfg.MATCH_QUEUE_LIKELY_ONLY = True
        assert staff_queue_statuses() == ("matched",)
        cfg.MATCH_QUEUE_LIKELY_ONLY = False
        assert staff_queue_statuses() == ("matched", "possible_match")


def test_g21_empty_candidates_and_zero_top_score_below_threshold():
    """P1.6 / P1.4: below T_low → no candidates, response top_score 0 (audit keeps NN)."""
    cands = [_cand(0.42), _cand(0.10)]
    found, band, status, out, top, audit = apply_candidate_honesty(
        cands, t_high=0.56, t_low=0.51, allow_possible=True
    )
    assert found is False
    assert band == "none"
    assert status == "no_match"
    assert out == []
    assert top == 0.0
    assert audit == 0.42


def test_g21_filters_subthreshold_neighbors_keeps_likely():
    cands = [_cand(0.72), _cand(0.40), _cand(0.55)]
    found, band, status, out, top, audit = apply_candidate_honesty(
        cands, t_high=0.56, t_low=0.51, allow_possible=True
    )
    assert found is True
    assert band == "likely"
    assert [c.similarity_score for c in out] == [0.72, 0.55]
    assert top == 0.72
    assert audit == 0.72
