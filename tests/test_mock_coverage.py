from notaris.domain import ExtractionField
from notaris.providers.mock import MockExtractionProvider


def test_mock_integer_coverage():
    provider = MockExtractionProvider()
    field_score = ExtractionField(name="Score", description="x", type="integer")
    assert provider._extract_field_value(field_score, "Patient score is 5") == 5
    assert provider._extract_field_value(field_score, "Score is none") is None

    field_age = ExtractionField(name="Age", description="x", type="integer")
    assert provider._extract_field_value(field_age, "65 years old") == 65
    assert provider._extract_field_value(field_age, "patient is fifty") is None


def test_mock_number_coverage():
    provider = MockExtractionProvider()
    field_weight = ExtractionField(name="Weight", description="x", type="number")
    assert provider._extract_field_value(field_weight, "Weight 70.5") == 70.5
    assert provider._extract_field_value(field_weight, "missing") is None


def test_mock_boolean_coverage():
    # just an empty block since we split it
    pass


def test_mock_boolean_markers():
    provider = MockExtractionProvider()
    field = ExtractionField(name="Valid", description="x", type="boolean")
    assert provider._extract_field_value(field, "patient reports nausea") is True
    assert (
        provider._extract_field_value(field, "nothing noted here") is True
    )  # noted is positive
    assert provider._extract_field_value(field, "unknown") is None

    adv_field = ExtractionField(name="Adverse event", description="x", type="boolean")
    assert provider._extract_field_value(adv_field, "no side effects") is False
    assert (
        provider._extract_field_value(adv_field, "patient experienced side effect")
        is True
    )


def test_mock_date_coverage():
    provider = MockExtractionProvider()
    field = ExtractionField(name="Date", description="x", type="date")
    assert provider._extract_field_value(field, "Date was 2023-10-05") == "2023-10-05"
    assert provider._extract_field_value(field, "Date was 10/12/2023") == "2023-10-12"
    assert provider._extract_field_value(field, "Date was 99/99/2023") is None
    assert provider._extract_field_value(field, "Date was unknown") is None


def test_mock_string_coverage():
    provider = MockExtractionProvider()
    field1 = ExtractionField(name="Follow-up", description="x", type="string")
    assert provider._extract_field_value(field1, "follow-up is 6 months") == "6 months"

    field2 = ExtractionField(name="Unrelated", description="x", type="string")
    assert provider._extract_field_value(field2, "some text") is None

    field3 = ExtractionField(name="diagnosis", description="x", type="string")
    assert (
        provider._extract_field_value(field3, "some generic text without pattern")
        is None
    )
