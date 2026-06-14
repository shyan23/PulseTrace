from lib.agent import normalize_sources


def test_google_always_present_even_if_not_requested():
    assert "google" in normalize_sources(["reddit", "hn"])


def test_google_cannot_be_removed():
    # caller passes everything-but-google; gate must still force it in
    assert "google" in normalize_sources(["facebook"])


def test_google_not_duplicated_when_requested():
    out = normalize_sources(["google", "reddit"])
    assert out.count("google") == 1


def test_google_leads_the_list():
    # default source runs first
    assert normalize_sources(["reddit"])[0] == "google"


def test_unknown_sources_dropped_but_google_stays():
    assert normalize_sources(["bogus"]) == ["google"]


def test_empty_input_yields_google_only():
    assert normalize_sources([]) == ["google"]
