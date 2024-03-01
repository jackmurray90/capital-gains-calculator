from pydantic import BaseModel
from enum import Enum
from decimal import Decimal
from datetime import datetime


class Type(str, Enum):
    buy = "buy"
    sell = "sell"
    transfer = "transfer"


class TaxableEvent(BaseModel):
    timestamp: datetime
    asset: str
    type: Type
    asset_amount: Decimal
    aud_amount: Decimal


class SuperTransfer(BaseModel):
    timestamp: datetime
    asset: str
    asset_amount: Decimal
