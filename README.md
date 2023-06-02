# Binance Capital Gains Tax Calculator

Script that takes Binance and CoinSpot trades CSV and calculates capital gains
for each year.

## Usage

Put your binance trades from the long-term (>6 month) export feature on binance
into a CSV file in the same directory. Do the same with CoinSpot. Then run:

    ./capital-gains-calculator.py

## How it works

This script works by inspecting rows in the CSV that are related to a
particular market e.g. BTCUSD. It looks at all buys and sells in that market
and matches up sells with buys in first-in-first-out order. It applies a 50%
discount on capital gains held for over 1 year, and also provides the total
without any discounts.

To configure the script, look at the first 3 lines:

    australian_tax_year = True
    base = 'BTC'
    quote = 'AUD'

Setting `australian_tax_year` to False will mean that the tax year will be set
to the normal Jan 1 -> Dec 31 instead of Jul 1 -> Jun 30 as they do in
Australia.

Setting base or quote will change the market.
