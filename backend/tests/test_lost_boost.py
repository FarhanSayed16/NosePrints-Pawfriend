"""Lost-status ranking boost is for sort order only."""


def test_lost_boost_can_outrank_slightly_higher_cosine():
    boost = 0.03
    candidates = [
        {"status": "registered", "score": 0.55},
        {"status": "lost", "score": 0.54},
    ]
    ranked = sorted(
        candidates,
        key=lambda c: (c["score"] + (boost if c["status"] == "lost" else 0.0), c["score"]),
        reverse=True,
    )
    assert ranked[0]["status"] == "lost"
    assert ranked[0]["score"] == 0.54
