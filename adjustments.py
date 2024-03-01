from csv import DictReader
from datetime import datetime, timedelta
from decimal import Decimal

from models import TaxableEvent, Type, SuperTransfer

adjustments_headers = ["Date", "Type", "BTC", "AUD", "Comment"]


class Adjustments:
    def can_load_events(self, path):
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            return reader.fieldnames == adjustments_headers

    def load_events(self, path):
        result = []
        with path.open(newline="") as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                timestamp = datetime.strptime(row["Date"], "%d/%m/%Y")
                btc = Decimal(row["BTC"])
                if row["Type"] == "Buy":
                    aud = Decimal(row["AUD"])
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset="BTC",
                            type=Type.buy,
                            asset_amount=btc,
                            aud_amount=aud,
                        )
                    )
                elif row["Type"] == "Sell":
                    aud = Decimal(row["AUD"])
                    result.append(
                        TaxableEvent(
                            timestamp=timestamp,
                            asset="BTC",
                            type=Type.sell,
                            asset_amount=btc,
                            aud_amount=aud,
                        )
                    )
                elif row["Type"] == "Super":
                    result.append(
                        SuperTransfer(
                            timestamp=timestamp + timedelta(days=1),
                            asset="BTC",
                            asset_amount=btc,
                        )
                    )
        return result
