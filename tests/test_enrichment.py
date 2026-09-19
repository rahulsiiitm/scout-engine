from scout_engine.enrich.conversion import detect_conversion_signal
from scout_engine.enrich.eligibility import (
    extract_experience,
    extract_graduation_years,
    extract_internship_duration_months,
)
from scout_engine.enrich.research import classify_research_requirement


def test_explicit_ppo_is_not_inferred_from_vague_language():
    signal, evidence = detect_conversion_signal("Internship with a pre-placement offer for top performers.")
    assert signal == "explicit"
    assert evidence
    signal, _ = detect_conversion_signal("Join our internship and learn from the engineering team.")
    assert signal == "unknown"


def test_experience_and_graduation_extraction():
    assert extract_experience("Requires 0-2 years of software engineering experience.") == (0.0, 2.0)
    assert extract_experience("Minimum 3 years experience.") == (3.0, None)
    assert extract_graduation_years("Graduating in 2027 or 2028") == [2027, 2028]
    assert extract_graduation_years("Copyright 2026. Apply now.") == []


def test_internship_duration():
    assert extract_internship_duration_months("This is a 6-month internship.") == 6
    assert extract_internship_duration_months("Duration: 4 to 6 months.") == 5


def test_research_publication_requirement_detection():
    heavy, pubs = classify_research_requirement(
        "Research Engineer",
        "Candidates should have publications at top-tier conferences such as NeurIPS.",
    )
    assert heavy is True
    assert pubs is True
