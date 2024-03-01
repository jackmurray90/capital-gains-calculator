from csv import DictReader
from datetime import datetime
from decimal import Decimal

from models import TaxableEvent, Type

binance_headers = [
    '\ufeff"Date(UTC)"',
    "Pair",
    "Side",
    "Price",
    "Executed",
    "Amount",
    "Fee",
]


class Binance:
    def can_load_events(self, path):
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            return (
                "Date(UTC)" in reader.fieldnames[0]
                and reader.fieldnames[1:] == binance_headers[1:]
            )

    def fix_date_header(self, row):
        # Hack to fix bytes at start of binance CSV export
        date = None
        for key, value in row.items():
            if "Date(UTC)" in key:
                date = value
        row["Date(UTC)"] = date

    def load_events(self, path):
        result = []
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                self.fix_date_header(row)
                if row["Pair"] != "BTCAUD":
                    continue
                timestamp = datetime.fromisoformat(row["Date(UTC)"])
                btc = Decimal(row["Executed"][:-3].replace(",", ""))
                aud = Decimal(row["Amount"][:-3].replace(",", ""))
                fee = Decimal(row["Fee"][:-3].replace(",", ""))
                feecoin = row["Fee"][-3:]
                if row["Side"] == "BUY":
                    if feecoin == "BTC":
                        btc -= fee
                    else:
                        btc -= fee * (btc / aud)
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset="BTC",
                            type=Type.buy,
                            asset_amount=btc,
                            aud_amount=aud,
                        )
                    )
                else:
                    if feecoin == "AUD":
                        aud -= fee
                    else:
                        aud -= fee * (aud / btc)
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset="BTC",
                            type=Type.sell,
                            asset_amount=btc,
                            aud_amount=aud,
                        )
                    )

        # Add withdrawal fees.

        unique_buying_days = {}
        for row in result:
            if row.type == Type.buy:
                unique_buying_days[
                    f"{row.timestamp.day}/{row.timestamp.month}/{row.timestamp.year}"
                ] = row

        transfer_fees = []
        for row in unique_buying_days.values():
            transfer_fees.append(
                TaxableEvent(
                    timestamp=row.timestamp,
                    asset="BTC",
                    type=Type.sell,
                    asset_amount=0.0001,
                    aud_amount=row.aud_amount / row.asset_amount * Decimal(0.0001),
                )
            )

        return result + transfer_fees
