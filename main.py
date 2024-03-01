#!/usr/bin/env python3

from collections import defaultdict
from pathlib import Path
from datetime import datetime

from coinspot import Coinspot, CoinspotSendsReceives
from coinbase import Coinbase
from binance import Binance
from trezor import Trezor
from adjustments import Adjustments
from models import TaxableEvent, Type, SuperTransfer

australian_tax_year = True
current_rate = 80152
super_monthly_payment = 1100

exchanges = [
    Coinspot(),
    CoinspotSendsReceives(),
    Coinbase(),
    Binance(),
    Trezor(),
    Adjustments(),
]

events = defaultdict(lambda: [])

for f in Path(".").iterdir():
    if f.suffix == ".csv":
        for exchange in exchanges:
            if exchange.can_load_events(f):
                print("Loading", f)
                for event in exchange.load_events(f):
                    events[event.asset].append(event)
                break
        else:
            print("Unable to parse", f)

all_total_profit = 0
total_profit = defaultdict(lambda: 0)
total_discounted_profit = defaultdict(lambda: 0)

adjustments = []

for asset in events:
    events[asset].sort(key=lambda x: x.timestamp)
    buys = []
    for event in events[asset]:
        if australian_tax_year:
            tax_year = (
                event.timestamp.year - 1
                if event.timestamp.month <= 6
                else event.timestamp.year
            )
        else:
            tax_year = event.timestamp.year
        if isinstance(event, SuperTransfer):
            while event.asset_amount > 0:
                if buys[-1].asset_amount <= event.asset_amount:
                    adjustments.append(
                        (
                            buys[-1].timestamp,
                            "Buy",
                            buys[-1].asset_amount,
                            buys[-1].aud_amount,
                            "Buy on coinspot",
                        )
                    )
                    event.asset_amount -= buys[-1].asset_amount
                    buys = buys[:-1]
                else:
                    fraction = event.asset_amount / buys[-1].asset_amount
                    adjustments.append(
                        (
                            buys[-1].timestamp,
                            "Buy",
                            event.asset_amount,
                            buys[-1].aud_amount * fraction,
                            "Buy on coinspot",
                        )
                    )
                    buys[-1] = TaxableEvent(
                        timestamp=buys[-1].timestamp,
                        asset=asset,
                        type=Type.buy,
                        asset_amount=buys[-1].asset_amount * (1 - fraction),
                        aud_amount=buys[-1].aud_amount * (1 - fraction),
                    )
                    event.asset_amount = 0
        elif event.type == Type.transfer:
            all_total_profit -= event.aud_amount
            total_profit[tax_year] -= event.aud_amount
            total_discounted_profit[tax_year] -= event.aud_amount
        elif event.type == Type.buy:
            buys.append(event)
        else:
            selling_rate = event.aud_amount / event.asset_amount
            while event.asset_amount > 0:
                if len(buys) == 0:
                    print(
                        event.asset_amount,
                        asset,
                        "produced out of thin air, claiming it was free at",
                        event.timestamp,
                    )
                    buys = [
                        TaxableEvent(
                            timestamp=event.timestamp,
                            asset=asset,
                            type=Type.buy,
                            asset_amount=event.asset_amount,
                            aud_amount=0,
                        )
                    ]
                buying_rate = buys[0].aud_amount / buys[0].asset_amount
                if buys[0].asset_amount <= event.asset_amount:
                    amount, buying_timestamp = buys[0].asset_amount, buys[0].timestamp
                    profit = (selling_rate - buying_rate) * amount
                    event.asset_amount -= amount
                    event.aud_amount -= selling_rate * amount
                    buys = buys[1:]
                else:
                    amount, buying_timestamp = event.asset_amount, buys[0].timestamp
                    fraction = event.asset_amount / buys[0].asset_amount
                    profit = (selling_rate - buying_rate) * amount
                    buys[0] = TaxableEvent(
                        timestamp=buys[0].timestamp,
                        asset=asset,
                        type=Type.buy,
                        asset_amount=buys[0].asset_amount - amount,
                        aud_amount=buys[0].aud_amount * (1 - fraction),
                    )
                    event.asset_amount = 0
                    event.aud_amount = 0
                discount = (
                    profit >= 0
                    and buying_timestamp.replace(year=buying_timestamp.year + 1)
                    < event.timestamp
                )
                print(
                    "Made",
                    "$" + str(profit)[:9],
                    "with",
                    "%0.8f" % amount,
                    asset,
                    "buying at",
                    "%0.2f" % buying_rate,
                    "on",
                    buying_timestamp,
                    "selling at",
                    "%0.2f" % selling_rate,
                    "on",
                    event.timestamp,
                    "50% discount" if discount else "no discount",
                )
                all_total_profit += profit
                total_profit[tax_year] += profit
                if discount:
                    profit /= 2
                total_discounted_profit[tax_year] += profit

if adjustments:
    print()
    print("Adjustments for superannuation:")
    print()
    print("Date,Type,BTC,AUD,Comment")
    for timestamp, type, btc, aud, comment in adjustments:
        print(
            f"{timestamp.day}/{timestamp.month}/{timestamp.year},{type},{round(btc, 8)},{aud},{comment}"
        )

print()
for year in sorted(total_profit.keys()):
    print(
        "Total Gapital Gains for year starting",
        "Jul" if australian_tax_year else "Jan",
        year,
        "is               ",
        total_profit[year],
    )
    print(
        "Total Gapital Gains for year starting",
        "Jul" if australian_tax_year else "Jan",
        year,
        "with discounts is",
        total_discounted_profit[year],
    )
print()

remaining_btc = sum([buy.asset_amount for buy in buys])
remaining_spent = sum([buy.aud_amount for buy in buys])
print(
    "Total remaining btc is",
    round(remaining_btc, 8),
    "( $",
    round(remaining_btc * current_rate, 2),
    ", acquired for $",
    round(remaining_spent, 2),
    ")",
)
print()
print(
    "Total all-time profit if you sold everything now:",
    round(remaining_btc * current_rate - remaining_spent + all_total_profit, 2),
)
print()
if buys:
    print(
        "Next discount date", buys[0].timestamp.replace(year=buys[0].timestamp.year + 1)
    )
    print()

print("Next super monthly payment would look like this in adjustments.csv:")
print()
total_super_btc = 0
while super_monthly_payment > 0:
    if buys[-1].aud_amount >= super_monthly_payment:
        fraction = super_monthly_payment / buys[-1].aud_amount
        total_super_btc += buys[-1].asset_amount * fraction
        break
    else:
        total_super_btc += buys[-1].asset_amount
        super_monthly_payment -= buys[-1].aud_amount
        buys = buys[:-1]
print(
    f"{datetime.now().strftime('%d/%m/%Y')},Super,{round(total_super_btc, 8)},,Transfer to superannuation"
)
print()
