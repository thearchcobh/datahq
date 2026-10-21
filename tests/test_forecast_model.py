import unittest
from datetime import date,datetime,timedelta
from datahq.forecast_model import Model,holiday,IRISH
from datahq.forecast import check_sources

class ForecastTests(unittest.TestCase):
    def fixture(self):
        start=date(2023,1,1);rows=[]
        for i in range(1200):
            d=start+timedelta(days=i)
            rows.append({'date':str(d),'open':True,'start':'08:00:00','end':'18:00:00','next':False,'bins':{'18':100,'24':100,'32':800},'temp':10,'rain':2,'wind':3,'weather_n':14,'weather_forecast':False})
        return {'days':rows,'cruises':[]}
    def test_same_hours_and_no_future_leakage(self):
        x=self.fixture();target=date(2025,10,21)
        next(r for r in x['days'] if r['date']==str(target))['end']='14:00:00'
        m=Model(x);a=m.baseline(target,target)
        self.assertAlmostEqual(a['value'],200)
        for r in x['days']:
            if r['date']>=str(target):r['bins']={'18':9999999}
        b=Model(x).baseline(target,target)
        self.assertEqual(a,b)
    def test_closed_is_zero_missing_is_unknown(self):
        x=self.fixture();d=date(2025,10,21);r=next(r for r in x['days'] if r['date']==str(d));r['open']=False
        self.assertEqual(Model(x).baseline(d,d)['value'],0)
        r['open']=True;r['start']=None
        self.assertIsNone(Model(x).baseline(d,d))
    def test_missing_comparable_uses_flagged_proxy(self):
        x=self.fixture();d=date(2025,10,21);anchor=d-timedelta(days=364)
        for r in x['days']:
            if abs((date.fromisoformat(r['date'])-anchor).days)<=14:r['bins']=None
        b=Model(x).baseline(d,d);self.assertTrue(any('proxy' in n for n in b['notes']))
    def test_cruise_identity_port_and_overlap(self):
        x=self.fixture();x['cruises']=[{'id':'one','ship':'Ship A','line':'Line A','port':'Cobh','arrival':'2025-10-21T08:00:00Z','departure':'2025-10-21T12:00:00Z','capacity':2000,'active':True},{'id':'two','ship':'Ship B','line':'Line B','port':'Ringaskiddy','arrival':'2025-10-21T19:00:00Z','departure':'2025-10-21T22:00:00Z','capacity':3000,'active':True}]
        m=Model(x);features,details=m.exposures(date(2025,10,21),(16,28))
        self.assertIn('ship:Cobh:Ship A',features);self.assertNotIn('port:Ringaskiddy',features);self.assertEqual(details[0]['overlap_hours'],4)
    def test_weather_is_relative_to_seasonal_norm(self):
        m=Model(self.fixture());self.assertTrue((m.anomaly(date(2025,10,21),date(2025,10,21))==0).all())
    def test_holidays_follow_movable_dates(self):
        self.assertEqual(holiday(date(2026,10,26)),'october-bank');self.assertEqual(holiday(date(2026,4,6)),'easter');self.assertIsNone(holiday(date(2026,10,25)))
    def test_stale_inputs_fail_closed(self):
        now=datetime(2026,10,21,tzinfo=IRISH)
        with self.assertRaises(RuntimeError):check_sources({'sync':{}},now)
        check_sources({'sync':{k:now.isoformat() for k in ('square_orders','weather_open_meteo','cruises')},'days':[{'date':'2026-10-21'}]},now)

if __name__=='__main__':unittest.main()
