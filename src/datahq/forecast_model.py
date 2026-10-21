"""Daily same-hours seasonal forecast; conservative, separately gated adjustments.
No credentials, network or database writes in this module.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo
import math
import numpy as np

VERSION = 'seasonal-same-hours-v1'
IRISH = ZoneInfo('Europe/Dublin')
WEATHER = ('temp', 'rain', 'wind')

def dt(s): return date.fromisoformat(s[:10])
def shift(d,n): return d+timedelta(days=n)
def clip(x,a,b): return float(np.clip(x,a,b))
def stamp(s): return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(IRISH)

def holiday(d):
    fixed={(1,1):'new-year',(3,17):'patrick',(12,25):'christmas',(12,26):'stephen'}
    if (d.month,d.day) in fixed: return fixed[d.month,d.day]
    first=lambda m: date(d.year,m,1)+timedelta(days=(7-date(d.year,m,1).weekday())%7)
    if d== (date(d.year,2,1) if date(d.year,2,1).weekday()==4 else first(2)): return 'brigid'
    for m in (5,6,8):
        if d==first(m): return f'bank-{m}'
    last=date(d.year,10,31); last-=timedelta(days=last.weekday())
    if d==last:return 'october-bank'
    y=d.year;a=y%19;b=y//100;c=y%100;h=(19*a+b-b//4-(b-(b+8)//25+1)//3+15)%30;l=(32+2*(b%4)+2*(c//4)-h-c%4)%7;m=(a+11*h+22*l)//451
    easter=date(y,(h+l-7*m+114)//31,(h+l-7*m+114)%31+1)
    return 'easter' if d==easter+timedelta(days=1) else None

def hours(row):
    if not row or not row.get('open'):return None
    if not row.get('start') or not row.get('end'):return None
    num=lambda s:int(s[:2])*2+int(s[3:5])/30
    a,b=num(row['start']),num(row['end'])
    return (a,b+48 if row.get('next') or b<=a else b)

class Model:
    def __init__(self,inputs):
        self.inputs=inputs
        self.days={dt(r['date']):r for r in inputs['days']}
        self.dates=sorted(self.days)
        self.calls=defaultdict(list)
        self.capacities={c['ship']:c['capacity'] for c in inputs.get('cruises',[]) if c.get('capacity')}
        latest_year=max((dt(c['arrival']).year for c in inputs.get('cruises',[])),default=0)
        for c in inputs.get('cruises',[]):
            # Old archive entries naturally fall out of the active feed; cancelled
            # calls from the latest season do not count as visits.
            if not c.get('active') and dt(c['arrival']).year==latest_year:continue
            a=stamp(c['arrival']);b=stamp(c['departure']) if c.get('departure') else None
            c={**c,'a':a,'b':b}
            for n in range(max(1,((b.date() if b else a.date())-a.date()).days+1)):
                self.calls[shift(a.date(),n)].append(c)

    @lru_cache(maxsize=60000)
    def amount(self,d,window):
        row=self.days.get(d,{})
        if not row.get('bins'):return None
        a,b=window
        own=hours(row)
        if own is None or min(b,own[1])-max(a,own[0]) < .85*(b-a):return None
        # Half-hour resolution; proportionate overlap at unusual quarter hours.
        value=0
        for k,v in row['bins'].items():
            k=int(k);k=k+48 if k<a and own[1]>48 else k
            value+=float(v)*max(0,min(b,k+1)-max(a,k))
        return value if value>25 else None

    @lru_cache(maxsize=30000)
    def seasonal(self,target,cutoff,window):
        anchor=shift(target,-364); kind=holiday(target)
        candidates=[]
        for off in range(-42,43):
            d=shift(anchor,off)
            if d>=cutoff:continue
            if kind:
                if holiday(d)!=kind:continue
            elif d.weekday()!=target.weekday() or holiday(d):continue
            value=self.amount(d,window)
            if value is not None:candidates.append((d,value,abs(off)))
        near=[x for x in candidates if x[2]<=14]
        use=near if len(near)>=3 or kind and near else sorted(candidates,key=lambda x:x[2])[:5]
        if not use:return None
        weights=np.array([math.exp(-x[2]/14) for x in use]);weights/=weights.sum()
        return float(sum(x[1]*w for x,w in zip(use,weights))),tuple((x[0],float(w)) for x,w in zip(use,weights)),not bool(near and len(near)>=3)

    @lru_cache(maxsize=20000)
    def baseline(self,target,cutoff):
        row=self.days.get(target);window=hours(row)
        if row and row.get('open') is False:return {'baseline':0.,'trend':1.,'value':0.,'comparables':[],'notes':[]}
        if not window:return None
        seasonal=self.seasonal(target,cutoff,window)
        if not seasonal:return None
        base,comps,proxy=seasonal
        ratios=[];same=[]
        for d in self.dates:
            if not shift(cutoff,-70)<=d<cutoff or holiday(d):continue
            actual=self.amount(d,window)
            prior=self.seasonal(d,cutoff,window)
            if actual is None or prior is None or prior[0]<100:continue
            ratio=clip(actual/prior[0],.4,1.8)
            ratios.append(ratio)
            if d.weekday()==target.weekday():same.append(ratio)
        overall=float(np.median(ratios)) if len(ratios)>=14 else 1.
        n=len(same);trend=(n*float(np.median(same))+4*overall)/(n+4) if n else overall
        trend=clip(trend,.5,1.5)
        notes=['Nearby same-weekday seasonal proxy; exact comparison limited'] if proxy else []
        if n<4:notes.append('Limited recent same-weekday trend evidence')
        return {'baseline':base,'trend':trend,'value':base*trend,'comparables':comps,'notes':notes}

    def exposures(self,d,window):
        values=defaultdict(float);details=[]
        if not window:return values,details
        a,b=window
        for c in self.calls.get(d,[]):
            if c['b'] is None:continue # never invent time in port
            start=(c['a'].date()-d).days*48+c['a'].hour*2+c['a'].minute/30
            end=(c['b'].date()-d).days*48+c['b'].hour*2+c['b'].minute/30
            overlap=max(0,min(b,end)-max(a,start))/2
            if not overlap:continue
            weight=min(overlap/8,1.5);port=c['port']
            # Separate ports: a Ringaskiddy call is not a Cobh call.
            values['port:'+port]+=weight
            values['line:'+port+':'+c['line']]+=weight
            values['ship:'+port+':'+c['ship']]+=weight
            capacity=c.get('capacity') or self.capacities.get(c['ship'])
            if capacity:values['capacity:'+port]+=weight*capacity/1000
            details.append({'ship':c['ship'],'line':c['line'],'port':port,'capacity':capacity,'capacity_inferred':not bool(c.get('capacity')) and bool(capacity),'overlap_hours':round(overlap,2)})
        return values,details

    @lru_cache(maxsize=15000)
    def anomaly(self,d,cutoff):
        row=self.days.get(d,{})
        if (row.get('weather_n') or 0)<12 or any(row.get(k) is None for k in WEATHER):return None
        normals=[]
        for p in self.dates:
            if p>=cutoff or p.year>=d.year:continue
            delta=abs(p.timetuple().tm_yday-d.timetuple().tm_yday);delta=min(delta,366-delta)
            r=self.days[p]
            if delta<=30 and (r.get('weather_n') or 0)>=12 and not r.get('weather_forecast') and all(r.get(k) is not None for k in WEATHER):normals.append(r)
        if len(normals)<30:return None
        return np.array([(float(row[k])-float(np.mean([r[k] for r in normals])))/scale for k,scale in zip(WEATHER,(5,10,3))])

    def features(self,d,cutoff,base,names,weather=True):
        window=hours(self.days.get(d));ex,_=self.exposures(d,window)
        x=np.array([ex.get(k,0) for k in names],dtype=float)
        # Adjustment is a difference from the cruise exposure already embedded
        # in the seasonal comparator, preventing a second full cruise uplift.
        for c,w in base['comparables']:
            old,_=self.exposures(c,window);x-=w*np.array([old.get(k,0) for k in names])
        wx=self.anomaly(d,cutoff) if weather else None
        if wx is not None:
            for c,w in base['comparables']:
                old=self.anomaly(c,cutoff)
                if old is not None:wx-=w*old
        return np.r_[x,wx if wx is not None else [0,0,0]]

    def fit(self,cutoff):
        counts=Counter()
        for d in self.dates:
            if shift(cutoff,-730)<=d<cutoff and self.days[d].get('bins'):
                ex,_=self.exposures(d,hours(self.days[d]));counts.update(ex.keys())
        names=sorted(k for k,n in counts.items() if n>=(8 if k.startswith('ship:') else 12 if k.startswith('line:') else 20))
        xs=[];ys=[];rows=[]
        for d in self.dates:
            if not shift(cutoff,-540)<=d<cutoff:continue
            base=self.baseline(d,d)
            window=hours(self.days[d]);actual=self.amount(d,window) if window else None
            if not base or not actual or base['value']<100:continue
            x=self.features(d,d,base,names,weather=not self.days[d].get('weather_forecast'))
            xs.append(x);ys.append(clip(math.log(actual/base['value']),-.8,.8));rows.append((d,base['value'],actual))
        if len(rows)<80:return names,np.zeros(len(names)+3),rows
        x=np.array(xs);y=np.array(ys)
        # Strong ridge shrinkage; ship terms are deviations from line/port terms.
        penalty=np.array([30 if k.startswith('ship:') else 20 for k in names]+[40]*3,dtype=float)
        beta=np.linalg.solve(x.T@x+np.diag(penalty),x.T@y)
        return names,beta,rows

    def adjustment(self,d,cutoff,base,names,beta,cruise=True,weather=True):
        x=self.features(d,cutoff,base,names,weather)
        c=clip(float(x[:-3]@beta[:-3]),math.log(.75),math.log(1.25)) if cruise else 0.
        w=clip(float(x[-3:]@beta[-3:]),math.log(.92),math.log(1.08)) if weather else 0.
        return math.expm1(c),math.expm1(w)

    def validate(self,cutoff):
        records=[]
        # Rolling origins: coefficients and sales trends are trained before each
        # 28-day test block. Weather uses realised conditions, explicitly a
        # conditional diagnostic, not a historical weather-forecast backtest.
        for offset in (112,84,56,28):
            origin=shift(cutoff,-offset);names,beta,_=self.fit(origin)
            for n in range(28):
                d=shift(origin,n)
                base=self.baseline(d,origin);window=hours(self.days.get(d));actual=self.amount(d,window) if window else None
                if not base or not actual or base['value']<100:continue
                c,w=self.adjustment(d,origin,base,names,beta)
                old=[sum(float(v) for v in self.days[p]['bins'].values()) for p in self.dates if shift(origin,-56)<=p<origin and p.weekday()==d.weekday() and self.days[p].get('bins')]
                records.append({'date':str(d),'actual':actual,'base':base['value'],'cruise':base['value']*(1+c),'weather':base['value']*(1+w),'both':base['value']*(1+c)*(1+w),'old':float(np.mean(old)) if old else base['value'],'fold':offset})
        if len(records)<40:return {'days':len(records),'cruise_enabled':False,'weather_enabled':False,'notes':'Insufficient holdout data'},records
        def error(key,rs=records):return sum(abs(r[key]-r['actual']) for r in rs)/sum(r['actual'] for r in rs) if rs and sum(r['actual'] for r in rs)>0 else float('inf')
        base=error('base');cruise=error('cruise');use_c=cruise<base*.98 and sum(error('cruise',[r for r in records if r['fold']==f])<error('base',[r for r in records if r['fold']==f]) for f in (112,84,56,28))>=3
        comparator='cruise' if use_c else 'base';wx='both' if use_c else 'weather'
        use_w=error(wx)<error(comparator)*.99 and sum(error(wx,[r for r in records if r['fold']==f])<error(comparator,[r for r in records if r['fold']==f]) for f in (112,84,56,28))>=3
        final=wx if use_w else comparator
        ratio_errors=[abs(math.log(r['actual']/max(r[final],1))) for r in records]
        return {'days':len(records),'baseline_wape':round(base,4),'old_average_wape':round(error('old'),4),'cruise_wape':round(cruise,4),'weather_conditional_wape':round(error(wx),4),'cruise_enabled':use_c,'weather_enabled':use_w,'selected_wape':round(error(final),4),'interval_log_error':float(np.quantile(ratio_errors,.8)),'weather_validation':'Conditional on realised weather; historical forecast vintages unavailable','cruise_validation':'Uses recorded visit history; historical schedule vintages unavailable'},records

    def forecast(self,cutoff,horizon=230):
        validation,records=self.validate(cutoff)
        names,beta,training=self.fit(cutoff)
        generated=datetime.now(IRISH).isoformat();out=[]
        latest_call=max(self.calls,default=date.min)
        for n in range(horizon):
            d=shift(cutoff,n);base=self.baseline(d,cutoff);row=self.days.get(d,{})
            if base is None:
                out.append({'trading_date':str(d),'sales':None,'notes':['Missing planned hours or comparable sales'],'generated_at':generated});continue
            notes=list(base['notes']);c=w=0.;details=[]
            if base['value']:
                use_c=validation['cruise_enabled'] and d<=latest_call
                wx=row.get('weather_forecast') and (row.get('weather_n') or 0)>=12 and n<14
                fetched=row.get('weather_fetched')
                if fetched and (datetime.now(IRISH)-stamp(fetched)).total_seconds()>48*3600:wx=False
                c,w=self.adjustment(d,cutoff,base,names,beta,use_c,validation['weather_enabled'] and bool(wx))
                # Conservative taper as weather forecast horizon increases.
                w*=max(0,1-n/14)
                _,details=self.exposures(d,hours(row))
                if d>latest_call:notes.append('Cruise schedule coverage unavailable; no cruise adjustment applied')
                elif not validation['cruise_enabled']:notes.append('Cruise adjustment held at zero: validation did not improve reliably')
                if not wx:notes.append('Weather forecast unavailable for this date; no weather adjustment')
                elif not validation['weather_enabled']:notes.append('Weather adjustment held at zero: no reliable improvement in validation')
            pre=base['value'];cruise_eur=pre*c;weather_eur=(pre+cruise_eur)*w;pred=pre+cruise_eur+weather_eur
            components=[]
            if cruise_eur and names:
                contributions=self.features(d,cutoff,base,names,False)[:-3]*beta[:-3]
                total=float(contributions.sum())
                if abs(total)>1e-8:
                    components=[{'factor':name,'adjustment_eur':round(cruise_eur*float(v)/total,2)} for name,v in zip(names,contributions) if abs(v)>.0001]
            spread=max(.15,validation.get('interval_log_error',.4))*(1+min(n,180)/360)
            out.append({'trading_date':str(d),'sales':round(pred,2),'baseline':round(base['baseline'],2),'trend_factor':round(base['trend'],4),'trend_eur':round(pre-base['baseline'],2),'cruise_eur':round(cruise_eur,2),'weather_eur':round(weather_eur,2),'low':round(pred*math.exp(-spread),2),'high':round(pred*math.exp(spread),2),'comparables':[str(c) for c,_ in base['comparables']],'cruise_calls':details,'cruise_components':components,'notes':notes,'generated_at':generated,'model_version':VERSION,'opening':{'start':row.get('start'),'end':row.get('end'),'next':row.get('next'),'open':row.get('open')}})
        return {'generated_at':generated,'as_of':str(cutoff),'model_version':VERSION,'validation':validation,'training_days':len(training),'coefficients':dict(zip(names+list(WEATHER),[round(float(x),6) for x in beta])),'source_sync':self.inputs.get('sync',{}),'days':out,'backtest':records}
