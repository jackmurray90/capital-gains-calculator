from csv import DictReader
from datetime import datetime
from decimal import Decimal

from models import TaxableEvent, Type

coinbase_headers = [
    "Timestamp",
    "Transaction Type",
    "Asset",
    "Quantity Transacted",
    "Spot Price Currency",
    "Spot Price at Transaction",
    "Subtotal",
    "Total (inclusive of fees and/or spread)",
    "Fees and/or Spread",
    "Notes",
]


class Coinbase:
    def can_load_events(self, path):
        with path.open(newline="") as csvfile:
            csvfile.readline()
            csvfile.readline()
            reader = DictReader(csvfile)
            return reader.fieldnames == coinbase_headers

    def load_events(self, path):
        result = []
        with path.open(newline="") as csvfile:
            csvfile.readline()
            csvfile.readline()
            reader = DictReader(csvfile)
            for row in reader:
                timestamp = datetime.fromisoformat(row["Timestamp"]).replace(
                    tzinfo=None
                )
                aud_amount = row["Total (inclusive of fees and/or spread)"]
                transaction_type = row["Transaction Type"]
                if transaction_type == "Convert":
                    [_, from_amount, from_asset, _, to_amount, to_asset] = row[
                        "Notes"
                    ].split(" ")
                    from_amount, to_amount, fee = (
                        Decimal(from_amount),
                        Decimal(to_amount),
                        Decimal(row["Fees and/or Spread"]),
                    )
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset=from_asset,
                            type=Type.sell,
                            asset_amount=from_amount,
                            aud_amount=aud_amount,
                        )
                    )
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset=to_asset,
                            type=Type.buy,
                            asset_amount=to_amount,
                            aud_amount=aud_amount,
                        )
                    )
                elif transaction_type in ["Buy", "Sell"]:
                    base = row["Asset"]
                    base_amount = Decimal(row["Quantity Transacted"])
                    aud_amount = row["Total (inclusive of fees and/or spread)"]
                    fee = Decimal(row["Fees and/or Spread"])
                    if transaction_type == "Buy":
                        result.append(
                            TaxableEvent(
                                timestamp=timestamp,
                                asset=base,
                                type=Type.buy,
                                asset_amount=base_amount,
                                aud_amount=aud_amount,
                            )
                        )
                    elif transaction_type == "Sell":
                        result.append(
                            TaxableEvent(
                                timestamp=timestamp,
                                asset=base,
                                type=Type.sell,
                                asset_amount=base_amount,
                                aud_amount=aud_amount - fee,
                            )
                        )
        return result
