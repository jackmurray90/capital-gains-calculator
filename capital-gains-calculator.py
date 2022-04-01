#!/usr/bin/env python3

australian_tax_year = True
base = 'BTC'
quote = 'AUD'
current_rate = 63189.59

import csv
from datetime import datetime
import collections

rows = []

with open('trades.csv', newline='') as csvfile:
  reader = csv.DictReader(csvfile)
  for row in reader:

    # hack to help with efbbbf bytes at start of binance CSV export
    for key, value in row.items():
      if key.endswith('Date(UTC)'):
        date = value
    row['Date(UTC)'] = date

    if row['Pair'] == base + quote:
      timestamp = datetime.fromisoformat(row['Date(UTC)'])
      btc = float(row['Executed'][:-3])
      aud = float(row['Amount'][:-3].replace(",",""))
      fee = float(row['Fee'][:-3].replace(",",""))
      feecoin = row['Fee'][-3:]
      if row['Side'] == 'BUY':
        if feecoin == base:
          btc -= fee
        else:
          btc -= fee * (btc/aud)
        rows.append((timestamp, 'buy', btc, aud))
      else:
        if feecoin == quote:
          aud -= fee
        else:
          aud -= fee * (aud/btc)
        rows.append((timestamp, 'sell', btc, aud))

rows.sort()

buys = []

all_total_profit = 0
total_profit = collections.defaultdict(lambda: 0)
total_discounted_profit = collections.defaultdict(lambda: 0)

for (timestamp, side, btc, aud) in rows:
  if side == 'buy':
    buys.append({'timestamp': timestamp, 'btc': btc, 'aud': aud})
  else:
    while btc > 0:
      buying_rate = buys[0]['aud'] / buys[0]['btc']
      selling_rate = aud / btc
      if buys[0]['btc'] < btc:
        amount = buys[0]['btc']
        profit = (selling_rate - buying_rate) * buys[0]['btc']
        btc -= buys[0]['btc']
        aud -= selling_rate * buys[0]['btc']
        buying_timestamp = buys[0]['timestamp']
        buys = buys[1:]
      else:
        amount = btc
        fraction = btc / buys[0]['btc']
        profit = (selling_rate - buying_rate) * btc
        buying_timestamp = buys[0]['timestamp']
        buys[0] = {'timestamp': buys[0]['timestamp'], 'btc': buys[0]['btc'] - btc, 'aud': buys[0]['aud'] * (1 - fraction)}
        btc = 0
        aud = 0
      if australian_tax_year:
        tax_year = timestamp.year-1 if timestamp.month <= 6 else timestamp.year
      else:
        tax_year = timestamp.year
      discount = buys[0]['timestamp'].replace(year=buys[0]['timestamp'].year+1) < timestamp
      print("Made", '$'+str(profit)[:9], "with", "%0.8f"%amount, "buying at", int(buying_rate),"on",buying_timestamp,"selling at", int(selling_rate), "on", timestamp, "50% discount" if discount else "no discount")
      all_total_profit += profit
      total_profit[tax_year] += profit
      if discount:
        profit *= 0.5
      total_discounted_profit[tax_year] += profit

print()
for year in total_profit.keys():
  print("Total Gapital Gains for year starting","Jul" if australian_tax_year else "Jan",year,"is               ", total_profit[year])
  print("Total Gapital Gains for year starting","Jul" if australian_tax_year else "Jan",year,"with discounts is", total_discounted_profit[year])
print()
remaining_btc = sum([buy['btc'] for buy in buys])
remaining_spent = sum([buy['aud'] for buy in buys])
print("Total remaining btc is", remaining_btc, "( $", remaining_btc * current_rate, ", acquired for $", remaining_spent, ")")
print()
print("Total all-time profit if you sold everything now:", remaining_btc * current_rate - remaining_spent + all_total_profit)
print()
