from csv import DictReader
from datetime import datetime
from decimal import Decimal

from models import TaxableEvent, Type

trezor_headers = [
    "Timestamp",
    "Date",
    "Time",
    "Type",
    "Transaction ID",
    "Fee",
    "Fee unit",
    "Address",
    "Label",
    "Amount",
    "Amount unit",
    "Fiat (AUD)",
    "Other",
]


class Trezor:
    def can_load_events(self, path):
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile, delimiter=";")
            return reader.fieldnames == trezor_headers

    def load_events(self, path):
        result = []
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile, delimiter=";")
            for row in reader:
                if (row["Type"] == "SELF" or row["Type"] == "SENT") and row[
                    "Amount unit"
                ] == "BTC":
                    assert row["Fee unit"] == "BTC"
                    timestamp = datetime.strptime(
                        f"{row['Date']} {row['Time']}00", "%d/%m/%Y %H:%M:%S GMT%z"
                    ).replace(tzinfo=None)
                    rate = Decimal(row["Fiat (AUD)"].replace(",", "")) / Decimal(
                        row["Amount"].replace(",", "")
                    )
                    btc = Decimal(row["Fee"].replace(",", ""))
                    aud = btc * rate
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset="BTC",
                            type=Type.transfer,
                            asset_amount=btc,
                            aud_amount=aud,
                        )
                    )
        return result
