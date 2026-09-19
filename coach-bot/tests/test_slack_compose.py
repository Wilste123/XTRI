from coach_bot.slack_compose import compact_reply, sanitize_for_slack


def test_sanitize_strips_headings():
    raw = "## Plan for i morgen\n\n- **Type:** Sykkel\n- Varighet 60 min"
    out = sanitize_for_slack(raw)
    assert "##" not in out
    assert "Plan for i morgen" in out or "Sykkel" in out


def test_compact_reply_short():
    reply = compact_reply("Status", "## Tittel\n\nKort tekst.\n\nNeste: synk kalender.")
    assert reply.blocks is not None
    assert len(reply.blocks) <= 4
    assert "#" not in reply.text
