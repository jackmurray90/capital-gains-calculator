from csv import DictReader
from datetime import datetime
from decimal import Decimal

from models import TaxableEvent, Type

coinspot_headers = [
    "Transaction Date",
    "Type",
    "Market",
    "Amount",
    "Rate inc. fee",
    "Rate ex. fee",
    "Fee",
    "Fee AUD (inc GST)",
    "GST AUD",
    "Total AUD",
    "Total (inc GST)",
]
coinspot_sends_receives_headers = [
    "Transaction Date",
    "Type",
    "Coin",
    "Status",
    "Fee",
    "Amount",
    "Address",
    "Txid",
    "Aud",
]


class Coinspot:
    def can_load_events(self, path):
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            return reader.fieldnames == coinspot_headers

    def load_events(self, path):
        result = []
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                base, quote = row["Market"].split("/")
                timestamp = datetime.strptime(
                    row["Transaction Date"], "%d/%m/%Y %H:%M %p"
                )
                base_amount = Decimal(row["Amount"])
                quote_amount = Decimal(row["Rate inc. fee"]) * base_amount
                total_aud = Decimal(row["Total AUD"])
                fee = Decimal(row["Fee AUD (inc GST)"])
                if row["Type"] == "Buy":
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset=base,
                            type=Type.buy,
                            asset_amount=base_amount,
                            aud_amount=total_aud,
                        )
                    )
                    if quote != "AUD":
                        result.append(
                            TaxableEvent(
                                timestamp=timestamp,
                                asset=quote,
                                type=Type.sell,
                                asset_amount=quote_amount,
                                aud_amount=total_aud - fee,
                            )
                        )
                else:
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset=base,
                            type=Type.sell,
                            asset_amount=base_amount,
                            aud_amount=total_aud - fee,
                        )
                    )
                    if quote != "AUD":
                        result.append(
                            TaxableEvent(
                                timestamp=timestamp,
                                asset=quote,
                                type=Type.buy,
                                asset_amount=quote_amount,
                                aud_amount=total_aud,
                            )
                        )
        return result


class CoinspotSendsReceives:
    def can_load_events(self, path):
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            return reader.fieldnames == coinspot_sends_receives_headers

    def load_events(self, path):
        result = []
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                if row["Type"] == "Send":
                    timestamp = datetime.strptime(
                        row["Transaction Date"], "%d/%m/%Y %H:%M %p"
                    )
                    btc = abs(Decimal(row["Fee"]))
                    aud = abs(Decimal(row["Aud"]) / Decimal(row["Amount"])) * btc
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset=row["Coin"],
                            type=Type.transfer,
                            asset_amount=btc,
                            aud_amount=aud,
                        )
                    )
        return result
