#!/usr/bin/env python3

australian_tax_year = True
base = 'BTC'
quote = 'AUD'
current_rate = 80152
super_monthly_payment = 1100

from csv import DictReader
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

coinspot_keys = {"Transaction Date", "Type", "Market", "Amount", "Rate inc. fee", "Rate ex. fee", "Fee", "Fee AUD (inc GST)", "GST AUD", "Total AUD", "Total (inc GST)"}
adjustment_keys = {"Date","Type","BTC","AUD","Comment"}
coinspot_sends_receives_keys = {"Transaction Date","Type","Coin","Status","Fee","Amount","Address","Txid","Aud"}
transactions_keys = {"Timestamp","Date","Time","Type","Transaction ID","Fee","Fee unit","Address","Label","Amount","Amount unit","Fiat (AUD)","Other"}

rows = []
tx_fees = 0

for f in Path('.').iterdir():
  if f.suffix == '.csv':
    print("Loading", f)
    with f.open(newline='') as csvfile:
      if f.stem == 'transactions':
        reader = DictReader(csvfile, delimiter=';')
      else:
        reader = DictReader(csvfile)
      for row in reader:
        # hack to help with efbbbf bytes at start of binance CSV export
        date = None
        for key, value in row.items():
          if 'Date(UTC)' in key:
            date = value
        if date:
          row['Date(UTC)'] = date
        if row.keys() == transactions_keys:
          if row["Type"] == "SENT" and row["Amount unit"] == "BTC":
            assert row["Fee unit"] == "BTC"
            timestamp = datetime.strptime(f"{row['Date']} {row['Time']}00", "%d/%m/%Y %H:%M:%S GMT%z").replace(tzinfo=None)
            rate = float(row["Fiat (AUD)"].replace(",","")) / float(row["Amount"].replace(",", ""))
            btc = float(row["Fee"].replace(",", ""))
            aud = btc * rate
            rows.append((timestamp, "sell", btc, aud, 'transaction-fee'))
            tx_fees += btc
        elif row.keys() == coinspot_sends_receives_keys:
          if row["Type"] == "Send":
            timestamp = datetime.strptime(row['Transaction Date'], "%d/%m/%Y %H:%M %p")
            btc = abs(float(row["Fee"]))
            aud = abs(float(row["Aud"]) / float(row["Amount"]) * btc)
            rows.append((timestamp, "sell", btc, aud, 'coinspot'))
            tx_fees += btc
        elif row.keys() == adjustment_keys:
          timestamp = datetime.strptime(row["Date"], "%d/%m/%Y")
          btc = float(row['BTC'])
          if row['Type'] == 'Buy':
            aud = float(row['AUD'])
            rows.append((timestamp, 'buy', btc, aud, 'adjustment'))
          elif row['Type'] == 'Sell':
            aud = float(row['AUD'])
            rows.append((timestamp, 'sell', btc, aud, 'adjustment'))
          else:
            rows.append((timestamp + timedelta(days=1), 'super', btc, aud, 'adjustment'))
        elif row.keys() == coinspot_keys:
          if row['Market'] == base + '/' + quote:
            timestamp = datetime.strptime(row['Transaction Date'], "%d/%m/%Y %H:%M %p")
            btc = float(row['Amount'])
            aud = float(row['Total AUD'])
            if row['Type'] == 'Buy':
              rows.append((timestamp, 'buy', btc, aud, 'coinspot'))
            else:
              rows.append((timestamp, 'sell', btc, aud, 'coinspot'))
        else:
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
              rows.append((timestamp, 'buy', btc, aud, 'binance'))
            else:
              if feecoin == quote:
                aud -= fee
              else:
                aud -= fee * (aud/btc)
              rows.append((timestamp, 'sell', btc, aud, 'binance'))

# btc, aud, exchange
unique_buying_days = {}

for row in rows:
  if row[1] == 'buy':
    unique_buying_days[f"{row[0].day}/{row[0].month}/{row[0].year}"] = row

for timestamp, side, btc, aud, exchange in unique_buying_days.values():
  if exchange == 'binance':
    rows.append((timestamp, 'sell', 0.0001, aud/btc*0.0001, 'binance'))
    tx_fees += 0.0001

rows.sort()

adjustments = []

buys = []

all_total_profit = 0
total_profit = defaultdict(lambda: 0)
total_discounted_profit = defaultdict(lambda: 0)

for (timestamp, side, btc, aud, _) in rows:
  if side == 'buy':
    buys.append({'timestamp': timestamp, 'btc': btc, 'aud': aud})
  elif side == 'super':
    while btc > 0:
      if buys[-1]['btc'] <= btc:
        adjustments.append((buys[-1]['timestamp'], 'Buy', buys[-1]['btc'], buys[-1]['aud'], 'Buy on coinspot'))
        btc -= buys[-1]['btc']
        buys = buys[:-1]
      else:
        fraction = btc / buys[-1]['btc']
        adjustments.append((buys[-1]['timestamp'], 'Buy', btc, buys[-1]['aud'] * fraction, 'Buy on coinspot'))
        buys[-1] = {'timestamp': buys[-1]['timestamp'], 'btc': buys[-1]['btc'] * (1 - fraction), 'aud': buys[-1]['aud'] * (1 - fraction)}
        btc = 0
  else:
    while btc >= 0.00000001:
      if len(buys) == 0:
        print(btc, "BTC produced out of thin air, claiming it was free at", timestamp)
        buys = [{'timestamp': timestamp, 'btc': btc, 'aud': 0}]
      buying_rate = buys[0]['aud'] / buys[0]['btc']
      selling_rate = aud / btc
      if buys[0]['btc'] <= btc:
        amount, buying_timestamp = buys[0]['btc'], buys[0]['timestamp']
        profit = (selling_rate - buying_rate) * amount
        btc -= amount
        aud -= selling_rate * amount
        buys = buys[1:]
      else:
        amount, buying_timestamp = btc, buys[0]['timestamp']
        fraction = btc / buys[0]['btc']
        profit = (selling_rate - buying_rate) * amount
        buys[0] = {'timestamp': buys[0]['timestamp'], 'btc': buys[0]['btc'] - amount, 'aud': buys[0]['aud'] * (1 - fraction)}
        btc = 0
        aud = 0
      if australian_tax_year:
        tax_year = timestamp.year-1 if timestamp.month <= 6 else timestamp.year
      else:
        tax_year = timestamp.year
      discount = (profit >= 0 and buying_timestamp.replace(year=buying_timestamp.year+1) < timestamp)
      print("Made", '$'+str(profit)[:9], "with", "%0.8f"%amount, "buying at", int(buying_rate),"on",buying_timestamp,"selling at", int(selling_rate), "on", timestamp, "50% discount" if discount else "no discount")
      all_total_profit += profit
      total_profit[tax_year] += profit
      if discount:
        profit *= 0.5
      total_discounted_profit[tax_year] += profit

if adjustments:
  print()
  print("Adjustments for superannuation:")
  print()
  print("Date,Type,BTC,AUD,Comment")
  for timestamp, type, btc, aud, comment in adjustments:
    print(f"{timestamp.day}/{timestamp.month}/{timestamp.year},{type},{round(btc, 8)},{aud},{comment}")

print()

print("Tx fees", round(tx_fees, 8))

print()
for year in total_profit.keys():
  print("Total Gapital Gains for year starting","Jul" if australian_tax_year else "Jan",year,"is               ", total_profit[year])
  print("Total Gapital Gains for year starting","Jul" if australian_tax_year else "Jan",year,"with discounts is", total_discounted_profit[year])
print()
remaining_btc = sum([buy['btc'] for buy in buys])
remaining_spent = sum([buy['aud'] for buy in buys])
print("Total remaining btc is", round(remaining_btc, 8), "( $", remaining_btc * current_rate, ", acquired for $", remaining_spent, ")")
print()
print("Total all-time profit if you sold everything now:", remaining_btc * current_rate - remaining_spent + all_total_profit)
print()
if buys:
  print("Next discount date", buys[0]['timestamp'].replace(year=buys[0]['timestamp'].year+1))
  print()

print("Next super monthly payment would look like this in adjustments.csv:")
print()
total_super_btc = 0
while super_monthly_payment > 0:
  if buys[-1]['aud'] >= super_monthly_payment:
    fraction = super_monthly_payment / buys[-1]['aud']
    total_super_btc += buys[-1]['btc']*fraction
    break
  else:
    total_super_btc -= buys[-1]['btc']
    super_monthly_payment -= buys[-1]['aud']
    buys = buys[:-1]
print(f"{datetime.now().strftime('%d/%m/%Y')},Super,{round(total_super_btc, 8)},,Transfer to superannuation")
print()
