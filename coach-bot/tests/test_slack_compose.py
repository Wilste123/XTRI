from coach_bot.slack_compose import (
    compact_reply,
    natural_reply,
    sanitize_for_slack,
    strip_self_denial,
)


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


def test_strip_self_denial_replaces_refusal():
    raw = (
        "Beklager misforståelsen. Jeg kan ikke direkte legge inn økten i "
        "Intervals.icu, men jeg kan gi deg instruksjoner."
    )
    out = strip_self_denial(raw)
    assert "kan ikke" not in out.lower()
    assert "beklager misforståelsen" not in out.lower()
    assert "legg" in out.lower() or "ja" in out.lower()


def test_strip_self_denial_keeps_normal_text():
    raw = "Fin økt i dag. Du kan ikke øke volumet for fort nå, hold roen."
    out = strip_self_denial(raw)
    # «kan ikke øke» er legitim coaching og skal ikke fjernes.
    assert "hold roen" in out.lower()


def test_natural_reply_is_plain_text():
    reply = natural_reply("## Status\n\nHei William, du ligger fint an denne uken.")
    assert reply.blocks is None
    assert "##" not in reply.text
    assert "William" in reply.text


def test_strip_denial_of_visuals():
    raw = "Jeg kan ikke lage visuelle fremstillinger, men jeg kan beskrive det."
    out = strip_self_denial(raw).lower()
    assert "kan ikke lage visuelle" not in out


def test_strip_false_action_claim():
    raw = (
        "Her er planen for uken.\n"
        "Jeg legger inn disse øktene nå. Gi meg et øyeblikk!"
    )
    out = strip_self_denial(raw)
    low = out.lower()
    assert "planen for uken" in low
    assert "legger inn disse øktene nå" not in low
    assert "gi meg et øyeblikk" not in low
