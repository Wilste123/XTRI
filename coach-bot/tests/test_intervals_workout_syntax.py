from coach_bot.intervals_workout_syntax import expand_repeat_blocks, estimate_workout_minutes


def test_expand_repeat_blocks_inline():
    raw = """Warmup
- 10m 65% HR

3x
- 5m 90% HR
- 2m 60% HR

Cooldown
- 5m 55% HR
"""
    out = expand_repeat_blocks(raw)
    assert "3x" not in out
    assert out.count("- 5m 90% HR") == 3
    assert out.count("- 2m 60% HR") == 3
    assert estimate_workout_minutes(out) == 10 + 3 * (5 + 2) + 5
