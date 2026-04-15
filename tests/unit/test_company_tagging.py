from src.normalization.tagging import extract_companies_from_text, infer_company, infer_primary_companies
from src.schemas.raw_result_schema import RawFinding


def _finding(**overrides):
    data = {
        "raw_finding_id": "rf-1",
        "run_id": "run-1",
        "agent_type": "hbm4",
        "query": "HBM4 Micron roadmap",
        "title": "Micron discusses HBM4 qualification roadmap",
        "source_type": "news",
        "signal_type": "direct",
        "source_name": "Example News",
        "published_at": "2026-04-15T00:00:00+00:00",
        "url": "https://example.com/micron-hbm4",
        "raw_content": "Micron said its HBM4 qualification work is continuing with customer sampling.",
    }
    data.update(overrides)
    return RawFinding(**data)


def test_extract_companies_from_text_uses_seed_competitors():
    matches = extract_companies_from_text(
        "Samsung Electronics and Micron are both mentioned in the note.",
        candidates=["Micron", "Samsung", "SK hynix"],
    )
    assert sorted(matches) == ["Micron", "Samsung"]


def test_extract_companies_from_text_restricts_to_candidates_when_given():
    matches = extract_companies_from_text(
        "Samsung, Micron and NVIDIA all appeared in the note.",
        candidates=["Micron", "Samsung"],
    )
    assert sorted(matches) == ["Micron", "Samsung"]


def test_infer_company_uses_title_content_and_seed_competitors():
    finding = _finding(
        title="HBM4 update from SK hynix partner channel",
        raw_content="The note says hynix continues qualification while Micron lags.",
        company=[],
        metadata={"seed_competitors": ["SK hynix", "Micron", "Samsung"]},
    )
    assert infer_company(finding) == ["SK hynix"]


def test_infer_primary_companies_prefers_title_and_query_over_body_mentions():
    companies = infer_primary_companies(
        title="Micron expands HBM4 qualification program",
        query="HBM4 Micron roadmap",
        raw_content=(
            "Micron discussed its roadmap. Analysts also compared Samsung, SK hynix, NVIDIA, AMD, "
            "Broadcom, Marvell, Qualcomm and Apple positions in the broader HBM ecosystem."
        ),
        source_name="Semiconductor News",
        url="https://example.com/micron-hbm4",
        candidates=["Micron", "Samsung", "SK hynix", "NVIDIA", "AMD"],
    )
    assert companies == ["Micron"]


def test_infer_primary_companies_can_return_two_when_title_jointly_scoped():
    companies = infer_primary_companies(
        title="Samsung and SK hynix battle for HBM4 packaging leadership",
        query="HBM4 Samsung SK hynix packaging",
        raw_content="Samsung and SK hynix were both highlighted in the lead section.",
        source_name="Chip News",
        url="https://example.com/hbm4-duopoly",
        candidates=["Samsung", "SK hynix", "Micron"],
    )
    assert companies == ["SK hynix", "Samsung"] or companies == ["Samsung", "SK hynix"]
