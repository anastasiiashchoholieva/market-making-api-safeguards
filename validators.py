from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import median
from typing import Any


@dataclass
class ValidationResult:
    is_valid: bool
    code: "ValidationCode | None" = None


class ValidationCode(str, Enum):
    # Fixture-related
    FIXTURE_ID_INVALID = "fixture_id_invalid"
    FIXTURE_NOT_TRADABLE = "fixture_not_tradable"
    PARTICIPANTS_MISSING = "participants_missing"

    # Odds entry–related
    ODDS_INACTIVE = "odds_entry_inactive"
    PRICE_INVALID = "invalid_price"
    MARKET_ID_MISSING = "market_id_missing"
    OUTCOME_ID_MISSING = "outcome_id_missing"
    CHANGED_AT_MISSING = "changed_at_missing"

    # Recency-related
    CHANGED_AT_INVALID = "invalid_changed_at"
    ODDS_STALE = "stale_odds"

    # Consensus-related
    NOT_ENOUGH_REFERENCES = "not_enough_references_for_consensus"
    CONSENSUS_OUTLIER = "consensus_price_outlier"


STATUS_FINISHED = "Finished"

NON_TRADABLE_STATUS_NAMES = {STATUS_FINISHED, }
MIN_CONSENSUS_REFERENCE_PRICES = 3
MIN_VALID_DECIMAL_ODDS = 1.0
MAX_ODDS_AGE_MS = 15_000
MAX_DEVIATION_RATIO = 0.35


def validate_fixture(fixture: dict[str, Any]) -> ValidationResult:
    fixture_id = fixture.get("fixtureId")
    status = fixture.get("status")
    participants = fixture.get("participants")

    if fixture_id is None or not isinstance(fixture_id, str):
        return ValidationResult(
            False,
            code=ValidationCode.FIXTURE_ID_INVALID,
        )

    if status["statusName"] in NON_TRADABLE_STATUS_NAMES:
        return ValidationResult(
            False,
            code=ValidationCode.FIXTURE_NOT_TRADABLE,
        )

    if (
        participants["participant1Name"] is None
        or participants["participant2Name"] is None
    ):
        return ValidationResult(
            False,
            code=ValidationCode.PARTICIPANTS_MISSING,
        )

    return ValidationResult(True)


def validate_odds_entry(entry: dict[str, Any]) -> ValidationResult:
    if "active" not in entry or entry["active"] is not True:
        return ValidationResult(
            False,
            code=ValidationCode.ODDS_INACTIVE,
        )

    price = entry["price"]
    if not isinstance(price, (int, float)) or price <= MIN_VALID_DECIMAL_ODDS:
        return ValidationResult(
            False,
            code=ValidationCode.PRICE_INVALID,
        )

    if "marketId" not in entry or entry["marketId"] is None:
        return ValidationResult(
            False,
            code=ValidationCode.MARKET_ID_MISSING,
        )

    if "outcomeId" not in entry or entry["outcomeId"] is None:
        return ValidationResult(
            False,
            code=ValidationCode.OUTCOME_ID_MISSING,
        )

    if "changedAt" not in entry or entry["changedAt"] is None:
        return ValidationResult(
            False,
            code=ValidationCode.CHANGED_AT_MISSING,
        )

    return ValidationResult(True)


def validate_odds_recency(
    entry: dict[str, Any],
    now_ms: int,
    max_age_ms: int = MAX_ODDS_AGE_MS,
) -> ValidationResult:
    changed_at = entry["changedAt"]

    if not isinstance(changed_at, int):
        return ValidationResult(
            False,
            code=ValidationCode.CHANGED_AT_INVALID,
        )

    if now_ms - changed_at > max_age_ms:
        return ValidationResult(
            False,
            code=ValidationCode.ODDS_STALE,
        )

    return ValidationResult(True)


def validate_consensus(
    odds_by_bookmaker: dict[str, dict[str, dict[str, Any]]],
    target_entry: dict[str, Any],  # The price update entry to validate
    max_deviation_ratio: float = MAX_DEVIATION_RATIO,
) -> ValidationResult:
    """
    Validate that the price in `target_entry` is consistent with bookmakers'
    consensus. The function collects prices from other bookmakers for the same
    `marketId` and `outcomeId`, computes the median reference price, and checks
    whether the target price deviates too much from that reference. If the
    deviation exceeds `max_deviation_ratio`, the price is considered an
    outlier.
    """
    market_id = target_entry["marketId"]
    outcome_id = target_entry["outcomeId"]
    target_price = target_entry["price"]

    prices: list[float] = []
    for bookmaker_entries in odds_by_bookmaker.values():
        for entry in bookmaker_entries.values():
            if (
                entry["marketId"] == market_id
                and entry["outcomeId"] == outcome_id
                and entry["active"] is True
            ):
                prices.append(entry["price"])

    if len(prices) < MIN_CONSENSUS_REFERENCE_PRICES:
        return ValidationResult(
            False,
            code=ValidationCode.NOT_ENOUGH_REFERENCES,
        )

    reference_price = median(prices)
    deviation = abs(target_price - reference_price) / reference_price

    if deviation > max_deviation_ratio:
        return ValidationResult(
            False,
            code=ValidationCode.CONSENSUS_OUTLIER,
        )

    return ValidationResult(True)
