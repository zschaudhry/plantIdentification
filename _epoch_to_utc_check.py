import datetime

epoch_ms = 954547200000
# Convert milliseconds to seconds
utc_dt = datetime.datetime.utcfromtimestamp(epoch_ms / 1000)
print(utc_dt.isoformat())
