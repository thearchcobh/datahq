export const day = ms => new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Dublin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms));
export const addDays = (d,n) => new Date(Date.parse(d+'T12:00:00Z')+n*86400000).toISOString().slice(0,10);
export function monday(d) { return addDays(d,-((new Date(d+'T12:00:00Z').getUTCDay()+6)%7)); }
export function midnight(d) {
  let t=Date.parse(d+'T00:00:00Z');
  const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Dublin',hour:'2-digit',hourCycle:'h23'}).format(new Date(t));
  return t-Number(parts)*3600000;
}
const effective=(rows,d)=>rows.filter(r=>r.effective_from<=d&&(!r.effective_to||r.effective_to>=d)).sort((a,b)=>b.effective_from.localeCompare(a.effective_from))[0];
const round=n=>Math.round(n*100)/100;
export function calculate({asOf,now,sales,cards,opening,rates,pension,overrides,settings}) {
 const date=day(now), week=monday(date), previousWeek=addDays(week,-7), cutoff=Date.parse(asOf), hours=new Map(opening.map(r=>[r.trading_date,r]));
 const warnings=new Set(), segments=[];
 for(const c of cards) {
  if(c.status==='DELETED') continue;
  const start=Date.parse(c.start_at), end=Math.min(c.end_at?Date.parse(c.end_at):cutoff,cutoff);
  if(!Number.isFinite(start)||end<=start) continue;
  if(!c.end_at && end-start>18*3600000) warnings.add('Check an unusually long open shift');
  for(let d=day(start);d<=day(end);d=addDays(d,1)) {
   const a=Math.max(start,midnight(d)), b=Math.min(end,midnight(addDays(d,1)));
   if(b<=a)continue;
   const prev=addDays(d,-1), tradingDate=day(start)===prev&&hours.get(prev)?.close_next_day?prev:d;
   if(tradingDate<previousWeek||tradingDate>date)continue;
   const unpaid=(c.raw_json?.breaks||[]).filter(x=>x.is_paid===false).reduce((s,x)=>s+Math.max(0,Math.min(b,x.end_at?Date.parse(x.end_at):cutoff)-Math.max(a,Date.parse(x.start_at))),0);
   const worked=Math.max(0,b-a-unpaid)/3600000;
   const rate=c.hourly_rate_amount==null?null:Number(c.hourly_rate_amount)/100;
   if(rate==null||!Number.isFinite(rate))warnings.add('Missing hourly wage');
   segments.push({member:c.team_member_id,d:tradingDate,calendarWeek:monday(d),base:rate==null?null:worked*rate,open:!c.end_at});
  }
 }
 const weekly=new Map();
 for(const s of segments){const k=s.member+s.calendarWeek;weekly.set(k,(weekly.get(k)||0)+(s.base||0));}
 const settingsMap=Object.fromEntries(settings.map(s=>[s.key,s.value_json]));
 for(const s of segments){
  const r=effective(rates,s.d), p=effective(pension,s.d), o=effective(overrides.filter(x=>x.team_member_id===s.member),s.d)||{};
  const leave=o.annual_leave_accrual_rate??settingsMap.default_annual_leave_accrual_rate;
  const other=o.other_employer_cost_rate??settingsMap.default_other_employer_cost_rate;
  if(!r||leave==null||other==null||s.base==null){s.cost=null;warnings.add('Incomplete payroll configuration');continue;}
  const prsi=weekly.get(s.member+s.calendarWeek)<=Number(r.weekly_threshold_eur)?Number(r.lower_employer_rate):Number(r.higher_employer_rate);
  s.cost=s.base*(1+Number(leave))*(1+prsi+Number(o.employer_pension_rate??p?.employer_rate??0)+Number(other));
 }
 function period(from,to=date){
  const ss=segments.filter(s=>s.d>=from&&s.d<=to), ls=sales.filter(s=>s.trading_date>=from&&s.trading_date<=to&&Date.parse(s.closed_at)<=cutoff);
  const net=ls.reduce((n,s)=>n+Number(s.sales_ex_vat_eur),0), cost=ss.some(s=>s.cost==null)?null:ss.reduce((n,s)=>n+s.cost,0);
  return {sales:round(net),labour:cost==null?null:round(cost),pct:net>0&&cost!=null?round(cost/net*100):null,openShifts:ss.filter(s=>s.open).length};
 }
 return {version:1,date,weekStart:week,asOf,generatedAt:new Date(now).toISOString(),target:32,estimated:true,stale:now-cutoff>90*60000,warnings:[...warnings],today:period(date),week:period(week),lastWeek:{start:previousWeek,end:addDays(week,-1),...period(previousWeek,addDays(week,-1))},lastFiveDays:Array.from({length:14},(_,i)=>{const d=addDays(previousWeek,i);return {date:d,...period(d,d)};})};
}
