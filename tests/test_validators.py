import pytest

from validators import (
    MAX_ODDS_AGE_MS,
    STATUS_FINISHED,
    ValidationCode,
    validate_consensus,
    validate_fixture,
    validate_odds_entry,
    validate_odds_recency,
)


@pytest.fixture
def fixture_payload():
    return {
        "fixtureId": "id1002608067131886",
        "status": {
            "live": True,
            "statusId": 1,
            "statusName": "Live"
        },
        "participants": {
            "participant1Name": "Gil Vicente FC",
            "participant2Name": "FC Vizela",
        },
    }


@pytest.fixture
def valid_entry():
    return {
        "bookmaker": "pinnacle",
        "outcomeId": 101,
        "marketId": 101,
        "active": True,
        "price": 1.76,
        "changedAt": 1773074025775,
    }


def test_fixture_is_valid(fixture_payload):
    result = validate_fixture(fixture_payload)

    assert result.is_valid is True


def test_finished_fixture_is_blocked(fixture_payload):
    fixture_payload["status"]["statusName"] = STATUS_FINISHED

    result = validate_fixture(fixture_payload)

    assert result.is_valid is False
    assert result.code == ValidationCode.FIXTURE_NOT_TRADABLE


def test_fixture_with_missing_participants_is_blocked(fixture_payload):
    fixture_payload["participants"]["participant2Name"] = None

    result = validate_fixture(fixture_payload)

    assert result.is_valid is False
    assert result.code == ValidationCode.PARTICIPANTS_MISSING


def test_fixture_with_invalid_id_is_blocked(fixture_payload):
    fixture_payload["fixtureId"] = None

    result = validate_fixture(fixture_payload)

    assert result.is_valid is False
    assert result.code == ValidationCode.FIXTURE_ID_INVALID


def test_valid_odds_entry_passes(valid_entry):
    result = validate_odds_entry(valid_entry)

    assert result.is_valid is True


def test_inactive_odds_entry_is_blocked(valid_entry):
    valid_entry["active"] = False

    result = validate_odds_entry(valid_entry)

    assert result.is_valid is False
    assert result.code == ValidationCode.ODDS_INACTIVE


def test_invalid_price_is_blocked(valid_entry):
    valid_entry["price"] = 1.0

    result = validate_odds_entry(valid_entry)

    assert result.is_valid is False
    assert result.code == ValidationCode.PRICE_INVALID


def test_missing_market_id_is_blocked(valid_entry):
    valid_entry["marketId"] = None

    result = validate_odds_entry(valid_entry)

    assert result.is_valid is False
    assert result.code == ValidationCode.MARKET_ID_MISSING


def test_missing_outcome_id_is_blocked(valid_entry):
    valid_entry["outcomeId"] = None

    result = validate_odds_entry(valid_entry)

    assert result.is_valid is False
    assert result.code == ValidationCode.OUTCOME_ID_MISSING


def test_missing_changed_at_is_blocked(valid_entry):
    valid_entry.pop("changedAt")

    result = validate_odds_entry(valid_entry)

    assert result.is_valid is False
    assert result.code == ValidationCode.CHANGED_AT_MISSING


def test_stale_odds_are_blocked(valid_entry):
    valid_entry["changedAt"] = 1000

    result = validate_odds_recency(
        valid_entry,
        now_ms=30_000,
        max_age_ms=10_000,
    )

    assert result.is_valid is False
    assert result.code == ValidationCode.ODDS_STALE


def test_invalid_changed_at_is_blocked(valid_entry):
    valid_entry["changedAt"] = "not-an-int"

    result = validate_odds_recency(
        valid_entry,
        now_ms=30_000,
        max_age_ms=10_000,
    )

    assert result.is_valid is False
    assert result.code == ValidationCode.CHANGED_AT_INVALID


def test_fresh_odds_pass(valid_entry):
    result = validate_odds_recency(
        valid_entry,
        now_ms=1773074030000,
        max_age_ms=MAX_ODDS_AGE_MS,
    )

    assert result.is_valid is True


def test_cross_bookmaker_outlier_is_blocked():
    odds_by_bookmaker = {
        "pinnacle": {
            "a": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 1.76,
            }
        },
        "betfair-ex": {
            "b": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 1.79,
            }
        },
        "3et": {
            "c": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 1.81,
            }
        },
        "bad-feed": {
            "d": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 4.80,
            }
        },
    }

    target_entry = odds_by_bookmaker["bad-feed"]["d"]

    result = validate_consensus(odds_by_bookmaker, target_entry)

    assert result.is_valid is False
    assert result.code == ValidationCode.CONSENSUS_OUTLIER


def test_consensus_passes_for_normal_price():
    odds_by_bookmaker = {
        "pinnacle": {
            "a": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 1.76,
            }
        },
        "betfair-ex": {
            "b": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 1.79,
            }
        },
        "3et": {
            "c": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 1.81,
            }
        },
        "sharpbet": {
            "d": {
                "marketId": 101,
                "outcomeId": 101,
                "active": True,
                "price": 1.78,
            }
        },
    }

    target_entry = odds_by_bookmaker["sharpbet"]["d"]

    result = validate_consensus(odds_by_bookmaker, target_entry)

    assert result.is_valid is True


def test_consensus_not_enough_references_is_blocked(valid_entry):
    odds_by_bookmaker = {
        "pinnacle": {"a": valid_entry},
        "betfair-ex": {},
    }

    result = validate_consensus(odds_by_bookmaker, valid_entry)

    assert result.is_valid is False
    assert result.code == ValidationCode.NOT_ENOUGH_REFERENCES
