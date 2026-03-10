# Market Making Feed Safeguards

A small Python project demonstrating basic safeguards for consuming odds data from an external API used in a market making system.

## Introduction

When a trading system consumes odds from an external feed, incorrect or corrupted data can lead to costly trades.
This project implements a minimal validation layer that inspects incoming data and blocks suspicious entries before they reach trading logic.

## Features

- Validates fixture state before processing odds
- Validates individual odds entries
- Detects stale price updates
- Detects cross-bookmaker price outliers
- Includes automated failure simulations using tests

## Important notes

- The thresholds used in this project are intentionally simple and should be treated as configurable risk parameters.
- In a production system, freshness checks would likely differ between pregame and in-play markets.
- Consensus checks may need bookmaker-specific tuning depending on market type and liquidity.
- When validation fails, suspicious data should be blocked or quarantined rather than automatically corrected.

## Installation

```bash
git clone https://github.com/anastasiiashchoholieva/market-making-api-safeguards.git
cd market-making-api-safeguards

python -m venv venv
venv\Scripts\activate (on Windows)
source venv/bin/activate (on macOS)

pip install -r requirements.txt
