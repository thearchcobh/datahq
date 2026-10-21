"""Refresh the stored Arch forecast. Run after the source feeds each morning."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from .forecast_model import Model, IRISH, dt, stamp

log=logging.getLogger(__name__)

def check_sources(inputs, now):
    sync=inputs.get('sync',{})
    # Refuse to replace a good snapshot with a model built on missing sales.
    for name,max_age in [('square_orders',36),('weather_open_meteo',48),('cruises',48)]:
        when=sync.get(name)
        age=(now-stamp(when)).total_seconds()/3600 if when else float('inf')
        closed_gap=False
        if name=='square_orders' and when and age<=7*24:
            calendar={dt(r['date']):r for r in inputs['days']}
            since=stamp(when).date()+timedelta(days=1)
            gap=[since+timedelta(days=i) for i in range(max(0,(now.date()-since).days))]
            closed_gap=bool(gap) and all(calendar.get(d,{}).get('open') is False for d in gap)
        if age>max_age and not closed_gap:
            raise RuntimeError(f'{name} is missing or stale; previous forecast retained')
    dates={r['date'] for r in inputs['days']}
    if str(now.date()) not in dates:raise RuntimeError('Opening calendar does not cover today')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input');parser.add_argument('--output');parser.add_argument('--as-of');args=parser.parse_args()
    client=None
    if args.input:inputs=json.loads(Path(args.input).read_text())
    else:
        from .database import get_client
        client=get_client();inputs=client.rpc('arch_forecast_inputs').execute().data
    now=datetime.now(IRISH);cutoff=dt(args.as_of) if args.as_of else now.date()
    if client:check_sources(inputs,now)
    result=Model(inputs).forecast(cutoff)
    if args.output:Path(args.output).write_text(json.dumps(result,allow_nan=False))
    if client:
        snapshot={'weather':[r for r in inputs['days'] if r['date']>=str(cutoff) and r.get('weather_n')], 'cruises':[c for c in inputs.get('cruises',[]) if dt(c['arrival'])>=cutoff],'sync':inputs.get('sync',{})}
        # Do not archive sales bins in the input snapshot.
        for row in snapshot['weather']:row.pop('bins',None)
        client.rpc('arch_publish_forecast',{'new_payload':result,'input_snapshot':snapshot}).execute()
        from .database import set_sync_state
        set_sync_state('sales_forecast')
    log.info('Forecast %s: %s days; validation %s',cutoff,len(result['days']),json.dumps(result['validation']))

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    main()
