import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,cp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {calculate} from '../supabase/functions/arch-dashboard/calculate.mjs';
import {calculate as widget} from '../supabase/functions/arch-labour-widget/calculate.mjs';
import {parseWarnings} from '../supabase/functions/arch-dashboard/warnings.mjs';
const now=Date.parse('2026-10-21T20:00:00Z');
const card=(job,rate)=>({team_member_id:'serena',job_id:job,start_at:'2026-10-21T10:00:00Z',end_at:'2026-10-21T12:00:00Z',hourly_rate_amount:rate,status:'CLOSED'});
const input={now,asOf:new Date(now).toISOString(),cards:[card('floor',10000),card('LVkzRSqcbzS2ZxVYrYAuxMLa',10000)],sales:[{trading_date:'2026-10-21',closed_at:'2026-10-21T18:00:00Z',sales_ex_vat_eur:1000}],opening:[],rates:[{effective_from:'2020-01-01',weekly_threshold_eur:300,lower_employer_rate:.1,higher_employer_rate:.2}],pension:[],overrides:[],settings:[{key:'default_annual_leave_accrual_rate',value_json:0},{key:'default_other_employer_cost_rate',value_json:0}]};
test('daily excludes admin; weekly and PRSI wage threshold include admin',()=>{for(const fn of [calculate,widget]){const r=fn(input);assert.equal(r.today.labour,240);assert.equal(r.today.pct,24);assert.equal(r.week.labour,480);assert.equal(r.week.pct,48);assert.equal(r.today.excludedLabour,240);}assert.equal(widget(input).version,1);assert.equal(widget(input).lastFiveDays.length,5);});
test('missing admin wage does not erase operational daily cost but weekly is unknown',()=>{const r=calculate({...input,cards:[card('floor',10000),card('LVkzRSqcbzS2ZxVYrYAuxMLa',null)]});assert.equal(r.today.labour,220);assert.equal(r.week.labour,null);});
test('past daily and last-week totals keep distinct cost bases',()=>{const shifted={...input,cards:input.cards.map(c=>({...c,start_at:c.start_at.replace('21','14'),end_at:c.end_at.replace('21','14')})),sales:input.sales.map(s=>({...s,trading_date:'2026-10-14',closed_at:'2026-10-14T18:00:00Z'}))};const r=calculate(shifted);assert.equal(r.lastFiveDays.find(d=>d.date==='2026-10-14').labour,240);assert.equal(r.lastWeek.labour,480);});
test('warnings filter county, expiry, cancellation and strip HTML',()=>{const w={level:'Orange',regions:['EI04'],onset:'2026-10-22T22:00:00+01:00',expiry:'2026-10-23T05:00:00+01:00',description:'<p>Heavy &amp; persistent rain</p>'};const r=parseWarnings([w,{...w,regions:['EI01']},{...w,status:'Cancel'},{...w,expiry:'2026-10-20T00:00:00Z'}],now);assert.equal(r.length,1);assert.equal(r[0].description,'Heavy & persistent rain');assert.equal(r[0].level,'orange');assert.throws(()=>parseWarnings({}));});
test('endpoint integrates months, inclusive weekly costs, and overnight warnings',async()=>{
 const dir=await mkdtemp(tmpdir()+'/arch-test-');const originalFetch=globalThis.fetch;const originalDeno=globalThis.Deno;
 try{
 for(const f of ['calculate.mjs','warnings.mjs'])await cp(new URL('../supabase/functions/arch-dashboard/'+f,import.meta.url),dir+'/'+f);
 let source=await readFile(new URL('../supabase/functions/arch-dashboard/index.ts',import.meta.url),'utf8');const tokenHash=Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode('test-only'))).toString('hex');source=source.replace(/const TOKEN_HASH = '[a-f0-9]+';/,`const TOKEN_HASH = '${tokenHash}';`);await writeFile(dir+'/index.ts',source);
 const today=new Date().toISOString().slice(0,10),d=new Date(today+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-(d.getUTCDay()+6)%7-7);const start=d.toISOString().slice(0,10);
 const opening=Array.from({length:250},(_,i)=>({trading_date:new Date(d.getTime()+i*86400000).toISOString().slice(0,10),is_scheduled_open:false}));
 const tables={sync_state:['square_orders','square_timecards'].map(source=>({source,last_synced_at:new Date().toISOString()})),analytics_sales_lines:input.sales.map(s=>({...s,trading_date:today,closed_at:today+'T18:00:00Z'})),square_timecards:input.cards.map(c=>({...c,start_at:today+'T10:00:00Z',end_at:today+'T12:00:00Z'})),analytics_opening_hours_daily:opening,analytics_prsi_rates:input.rates,analytics_pension_default_rates:[],analytics_employee_cost_overrides:[],analytics_settings:input.settings,square_scheduled_shifts:[{...input.cards[1],id:'tasting',start_at:today+'T10:00:00Z',end_at:today+'T12:00:00Z'}],analytics_daily_performance:[],analytics_uncosted_recent_products:[],weather_hourly:[],cruise_calls:[]};
 globalThis.fetch=async url=>new Response(JSON.stringify(String(url).includes('met.ie')?[{level:'orange',regions:['EI04'],headline:'Orange rain',onset:today+'T22:00:00+01:00',expiry:new Date(Date.parse(today+'T00:00:00Z')+86400000).toISOString().slice(0,10)+'T05:00:00+01:00'}]:tables[new URL(url).pathname.split('/').at(-1)]||[]));
 let handler;globalThis.Deno={env:{get:n=>n==='SUPABASE_URL'?'https://fixture.invalid':'fixture'},serve:fn=>handler=fn};await import(dir+'/index.ts');
 const call=(months,key='test-only')=>handler(new Request('https://fixture.invalid?months='+months,{headers:{Authorization:'Bearer '+key}}));
 assert.equal((await call(0,'invalid')).status,401);assert.equal((await call(7)).status,400);
 const a=await (await call(0)).json(),b=await(await call(1)).json(),c=await(await call(2)).json();
 assert.equal(a.days.length,21);assert.ok(b.days.length>a.days.length);assert.ok(c.days.length>b.days.length);assert.equal(c.days.length%7,0);assert.equal(c.weeks.length,c.days.length/7);assert.ok(a.days.find(d=>d.date===today).advisories.length);assert.equal(a.advisoriesAvailable,true);assert.ok(a.weeks[1].labour>0);assert.equal(a.days.find(d=>d.date===today).forecast.labour,0);assert.ok(a.days.find(d=>d.date===today).forecast.allLabour>0);
 }finally{globalThis.fetch=originalFetch;globalThis.Deno=originalDeno;await rm(dir,{recursive:true,force:true});}
});
