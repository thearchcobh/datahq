import {calculate,day,monday,addDays,midnight} from './calculate.mjs';
// A dedicated read-only dashboard credential; plaintext is never committed.
const TOKEN_HASH = 'c0c4761c916121fb5f35090181f485f0929e8bcf8aa0dd49151caaefa2e52564';
const LOCATION='L05Y6CVDJJN86';
const headers={'Content-Type':'application/json','Cache-Control':'no-store','Access-Control-Allow-Origin':'https://thearchcobh.github.io','Access-Control-Allow-Headers':'authorization,content-type','Access-Control-Allow-Methods':'GET,OPTIONS','Vary':'Origin'};
const reply=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers});
const hash=async(s:string)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))).map(x=>x.toString(16).padStart(2,'0')).join('');
let cached:any=null, cachedAt=0;
Deno.serve(async(req:Request)=>{
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers});
 if(req.method!=='GET')return reply({error:'Method not allowed'},405);
 const token=req.headers.get('Authorization')?.replace(/^Bearer /,'')||'';
 if(token.length>100||await hash(token)!==TOKEN_HASH)return reply({error:'Access key not recognised'},401);
 if(cached&&Date.now()-cachedAt<60000)return reply(cached);
 try{
 const base=Deno.env.get('SUPABASE_URL')!,key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
 async function rows(table:string,params:Record<string,string>={}){const result:any[]=[];for(let offset=0;offset<100000;offset+=1000){const q=new URLSearchParams({...params,limit:'1000',offset:String(offset)});const r=await fetch(`${base}/rest/v1/${table}?${q}`,{headers:{apikey:key,Authorization:`Bearer ${key}`},signal:AbortSignal.timeout(25000)});if(!r.ok)throw Error(table+':'+r.status);const chunk=await r.json();result.push(...chunk);if(chunk.length<1000)return result;}throw Error('Dataset limit');}
 const now=Date.now(),today=day(now),start=addDays(monday(today),-7),end=addDays(start,20),year=today.slice(0,4)+'-01-01';
 const sync=await rows('sync_state',{select:'source,last_synced_at',order:'source'});
 const required=['square_orders','square_timecards'].map(s=>sync.find(x=>x.source===s)?.last_synced_at);
 if(required.some(x=>!x))return reply({error:'Awaiting Square sync'},503);
 const asOf=new Date(Math.min(...required.map(x=>Date.parse(x)))).toISOString();
 const [sales,cards,opening,rates,pension,overrides,settings,roster,history,uncosted,weather,cruises]=await Promise.all([
 rows('analytics_sales_lines',{select:'sales_line_id,trading_date,closed_at,sales_ex_vat_eur',trading_date:`gte.${start}`,order:'sales_line_id'}),
 rows('square_timecards',{select:'id,team_member_id,job_id,start_at,end_at,status,hourly_rate_amount,raw_json',start_at:`gte.${addDays(today,-90)}T00:00:00Z`,location_id:`eq.${LOCATION}`,order:'start_at.desc,id'}),
 rows('analytics_opening_hours_daily',{select:'*',trading_date:`gte.${addDays(start,-1)}`,order:'trading_date'}),
 rows('analytics_prsi_rates',{order:'effective_from'}),rows('analytics_pension_default_rates',{order:'effective_from'}),rows('analytics_employee_cost_overrides',{order:'id'}),rows('analytics_settings',{order:'key'}),
 rows('square_scheduled_shifts',{select:'*',start_at:`gte.${start}T00:00:00Z`,location_id:`eq.${LOCATION}`,order:'start_at,id'}),
 rows('analytics_daily_performance',{select:'trading_date,sales_ex_vat_eur,loaded_labour_cost_eur,opening_hours_modelled',trading_date:`gte.${year}`,order:'trading_date'}),
 rows('analytics_uncosted_recent_products',{select:'variation_id,item_name,variation_name',order:'variation_id'}),
 rows('weather_hourly',{select:'time_utc,temp_c,precip_mm,wind_ms,cloud_pct,source_fetched_at,is_forecast',time_utc:`gte.${start}T00:00:00Z`,order:'time_utc'}),
 rows('cruise_calls',{select:'uid,vessel,port,arrival,departure,passengers,active_in_latest_feed',arrival:`gte.${addDays(start,-7)}T00:00:00Z`,active_in_latest_feed:'eq.true',order:'arrival,uid'})]);
 const common={sales,cards,opening,rates,pension,overrides,settings,asOf};
 const actual=new Map();for(let w=0;w<3;w++){const r=calculate({...common,now:Date.parse(addDays(start,w*7+6)+'T12:00:00Z')});for(const d of r.lastFiveDays)actual.set(d.date,d);}
 const upcoming=roster.map(s=>{const draft=s.raw_json?.draft_shift_details,published=s.raw_json?.published_shift_details;const details=draft||published||s;return {...s,...details,draft:!!draft&&JSON.stringify(draft)!==JSON.stringify(published)};}).filter(s=>!s.is_deleted&&s.status!=='DELETED'&&day(s.start_at)>=today&&day(s.start_at)<=end);
 const forecastCards=upcoming.map(s=>{const wage=cards.find(c=>c.team_member_id===s.team_member_id&&c.job_id===s.job_id&&c.hourly_rate_amount!=null);return {...s,hourly_rate_amount:wage?.hourly_rate_amount??null,raw_json:{breaks:[]},status:'CLOSED'};});
 const projected=new Map();for(let w=0;w<3;w++){const finish=addDays(start,w*7+6);const r=calculate({...common,cards:[...cards.filter(c=>day(c.start_at)<today),...forecastCards],now:Date.parse(finish+'T12:00:00Z'),asOf:new Date(midnight(addDays(finish,1))).toISOString()});for(const d of r.lastFiveDays)projected.set(d.date,d);}
 const result=Array.from({length:21},(_,i)=>{const date=addDays(start,i),future=date>=today,shifts=upcoming.filter(s=>day(s.start_at)===date),open=opening.find(x=>x.trading_date===date),closed=open?.is_scheduled_open===false;
 const prior=history.filter(h=>h.trading_date<today&&h.trading_date>=addDays(today,-56)&&new Date(h.trading_date).getUTCDay()===new Date(date).getUTCDay()&&Number(h.sales_ex_vat_eur)>0);
 const forecastSales=closed?0:prior.length>=3?prior.reduce((s,h)=>s+Number(h.sales_ex_vat_eur),0)/prior.length:null;
 const predictedLabour=shifts.length?projected.get(date)?.labour??null:closed?0:null;
 const predictedPct=forecastSales>0&&predictedLabour!=null?predictedLabour/forecastSales*100:null;
 const a:any=actual.get(date)||{},warnings:string[]=[];
 if(future&&!closed&&!shifts.length)warnings.push('not rostered');
 if(shifts.some(s=>s.draft))warnings.push('Includes draft roster changes');
 if(future&&shifts.length&&predictedLabour==null)warnings.push('Missing wage or payroll configuration');
 if(future&&!closed&&forecastSales==null)warnings.push('Not enough comparable sales days to forecast');
 const dayCards=cards.filter(c=>day(c.start_at)===date&&c.status!=='DELETED');
 if(dayCards.some(c=>!c.end_at&&(Date.parse(asOf)-Date.parse(c.start_at)>18*3600000||date<today)))warnings.push('Missing clock-out or unusually long open shift');
 if(dayCards.some(c=>c.hourly_rate_amount==null))warnings.push('Missing hourly wage');
 if(shifts.some(s=>(Date.parse(s.end_at)-Date.parse(s.start_at))/3600000>12))warnings.push('Roster contains a shift longer than 12 hours');
 if(date<today&&!closed&&!dayCards.length)warnings.push('No recorded shifts');
 const fresh=Date.parse(asOf)>=midnight(addDays(date,1));
 if(date<today&&!fresh)warnings.push('Data does not yet cover the full day');
 let p=date>today?predictedPct:a.pct??null,labour=date>today?predictedLabour:a.labour??null,net=date>today?forecastSales:a.sales??null;
 if(future&&!shifts.length&&!closed){p=null;labour=null;}if(date<today&&!closed&&!dayCards.length)p=null;
 const wx=weather.filter(x=>day(x.time_utc)===date&&x.temp_c!=null);const weatherData=wx.length?{low:Math.min(...wx.map(x=>x.temp_c)),high:Math.max(...wx.map(x=>x.temp_c)),rain:wx.reduce((s,x)=>s+(x.precip_mm||0),0),wind:Math.max(...wx.map(x=>x.wind_ms||0))*3.6,cloud:wx.reduce((s,x)=>s+(x.cloud_pct||0),0)/wx.length,fetched:wx.map(x=>x.source_fetched_at).sort().at(-1)}:null;
 return {date,pct:p,labour,sales:net,closed,mode:date<today?'Actual':date===today?'So far':'Forecast',warnings,forecast:{sales:forecastSales,labour:predictedLabour,pct:predictedPct,sampleDays:prior.length},shifts:shifts.map(s=>({start:s.start_at,end:s.end_at,draft:s.draft})),weather:weatherData,cruises:cruises.filter(c=>day(c.arrival)<=date&&day(c.departure||c.arrival)>=date),holiday:holiday(date)};});
 const weeks=[0,1,2].map(w=>{const ds=result.slice(w*7,w*7+7);const parts=ds.map(d=>d.date>=today?{sales:d.forecast.sales,labour:d.forecast.labour,pct:d.forecast.pct,closed:d.closed}:d);const complete=parts.every(d=>d.closed||d.pct!=null);const net=parts.reduce((s,d)=>s+(d.sales||0),0),labour=parts.reduce((s,d)=>s+(d.labour||0),0);return {pct:complete&&net>0?100*labour/net:null,complete,warnings:ds.some(d=>d.warnings.length),sales:net,labour};});
 const ytd=history.filter(h=>h.trading_date>=year&&h.trading_date<today&&h.trading_date<day(Date.parse(asOf))),ySales=ytd.reduce((s,h)=>s+Number(h.sales_ex_vat_eur||0),0),yLabour=ytd.reduce((s,h)=>s+Number(h.loaded_labour_cost_eur||0),0);
 cached={today,start,asOf,generatedAt:new Date().toISOString(),stale:now-Date.parse(asOf)>5400000,days:result,weeks,ytd:{pct:ySales>0?yLabour/ySales*100:null,sales:ySales,labour:yLabour,through:ytd.at(-1)?.trading_date,estimated:true},uncosted,sync,eventsAvailable:false,advisoriesAvailable:false};cachedAt=Date.now();return reply(cached);
 }catch(e){console.error(String(e));return reply({error:'Dashboard data temporarily unavailable'},503);}
});
function holiday(d:string){const y=Number(d.slice(0,4)),fixed=[`${y}-01-01`,`${y}-03-17`,`${y}-12-25`,`${y}-12-26`];if(fixed.includes(d))return 'Irish public holiday';const nth=(m:number,n:number)=>{const first=new Date(Date.UTC(y,m-1,1));return `${y}-${String(m).padStart(2,'0')}-${String(1+(8-first.getUTCDay())%7+7*(n-1)).padStart(2,'0')}`;};if([nth(5,1),nth(6,1),nth(8,1)].includes(d))return 'Irish public holiday';const feb=new Date(Date.UTC(y,1,1)).getUTCDay()===5?`${y}-02-01`:nth(2,1);if(d===feb)return 'St Brigid’s Day';const lastOct=new Date(Date.UTC(y,9,31));lastOct.setUTCDate(31-(lastOct.getUTCDay()+6)%7);if(d===lastOct.toISOString().slice(0,10))return 'October bank holiday';const a=y%19,b=Math.floor(y/100),c=y%100,e=b%4,f=Math.floor((b+8)/25),g=Math.floor((b-f+1)/3),h=(19*a+b-Math.floor(b/4)-g+15)%30,k=c%4,l=(32+2*e+2*Math.floor(c/4)-h-k)%7,m=Math.floor((a+11*h+22*l)/451),month=Math.floor((h+l-7*m+114)/31),dd=(h+l-7*m+114)%31+1;const easter=new Date(Date.UTC(y,month-1,dd+1)).toISOString().slice(0,10);return d===easter?'Easter Monday':null;}
