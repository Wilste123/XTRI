from coach_bot import knowledge


def test_topics_loaded():
    t = knowledge.topics()
    assert {"trening", "skade", "ernaering", "race_lofoten"} <= set(t)


def test_search_injury():
    hits = knowledge.search("vondt i kneet etter løping", top_k=2)
    assert hits
    assert any(h.source == "skade" for h in hits)


def test_search_nutrition_carbs():
    hits = knowledge.search("hvor mye karbohydrat per time på lange økter", top_k=2)
    assert any(h.source == "ernaering" for h in hits)


def test_search_race_cold_water():
    hits = knowledge.search("kaldt vann svøm våtdrakt lofoten", top_k=2)
    assert any(h.source == "race_lofoten" for h in hits)


def test_search_empty_query_returns_nothing():
    assert knowledge.search("   ") == []


def test_search_text_renders_source():
    txt = knowledge.search_text("aerob base sone 2", top_k=1)
    assert "trening" in txt
