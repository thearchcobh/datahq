"""Gate scheduled syncs before installing dependencies; missing hours fail visibly.

Cron covers 08:30–23:30 Europe/Dublin. Expand cron if trading moves outside this.
Manual and push runs bypass the gate. No database writes here.
"""
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DUBLIN = ZoneInfo('Europe/Dublin')


def in_window(rows, now):
    now = now.astimezone(DUBLIN).replace(second=0, microsecond=0)
    if not any(r['trading_date'] == now.date().isoformat() for r in rows):
        raise ValueError('Opening-hours calendar missing for today')
    for row in rows:
        if not row['is_scheduled_open']:
            continue
        day = date.fromisoformat(row['trading_date'])
        start = datetime.combine(day, time.fromisoformat(row['open_time']), DUBLIN)
        end = datetime.combine(day, time.fromisoformat(row['close_time']), DUBLIN)
        if row['close_next_day']:
            end += timedelta(days=1)
        if start <= now <= end + timedelta(minutes=90):
            return True
    return False


def main():
    now = datetime.now(DUBLIN)
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    today = now.date().isoformat()
    query = urlencode({'select': 'trading_date,is_scheduled_open,open_time,close_time,close_next_day',
                       'trading_date': f'in.({yesterday},{today})'})
    key = os.environ['SUPABASE_SECRET_KEY']
    request = Request(os.environ['SUPABASE_URL'] + '/rest/v1/analytics_opening_hours_daily?' + query,
                      headers={'apikey': key, 'Authorization': 'Bearer ' + key})
    with urlopen(request, timeout=20) as response:
        rows = json.load(response)
    allowed = in_window(rows, now)
    print(f'{now.isoformat()}: Square sync enabled={allowed} (trading hours + 90 minutes)')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('run=' + str(allowed).lower() + '\n')


if __name__ == '__main__':
    main()
