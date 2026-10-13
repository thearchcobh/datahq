import { calculate,day,monday,addDays,midnight } from './calculate.mjs';
// Only the SHA-256 of a dedicated, revocable widget credential is deployed.
// No database credential is supplied to the iPhone.
const TOKEN_HASH = 'a675cb964f622f4e634f386c23793bdc0adeef579457f8e7054b88c772c8ed0e';
const headers={'Content-Type':'application/json','Cache-Control':'no-store'};
const reply=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers});
async function hash(s:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))).map(x=>x.toString(16).padStart(2,'0')).join('');}
Deno.serve(async(req:Request)=>{
 if(req.method!=='GET')return reply({error:'Method not allowed'},405);
 const token=req.headers.get('Authorization')?.replace(/^Bearer /,'')||'';
 if(!/^[a-f0-9]{64}$/.test(token)||await hash(token)!==TOKEN_HASH)return reply({error:'Unauthorized'},401);
 try {
  const base=Deno.env.get('SUPABASE_URL')!, key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  async function rows(table:string,params:Record<string,string>){
   const result=[];
   for(let offset=0;offset<50000;offset+=1000){
    const q=new URLSearchParams({...params,limit:'1000',offset:String(offset)});
    const r=await fetch(`${base}/rest/v1/${table}?${q}`,{headers:{apikey:key,Authorization:`Bearer ${key}`},signal:AbortSignal.timeout(20000)});
    if(!r.ok)throw new Error('Data unavailable');
    const chunk=await r.json();result.push(...chunk);if(chunk.length<1000)return result;
   }
   throw new Error('Dataset exceeds safe limit');
  }
  const sync=await rows('sync_state',{select:'source,last_synced_at',source:'in.(square_orders,square_timecards)',order:'source'});
  if(sync.length!==2||sync.some(s=>!s.last_synced_at))return reply({error:'Awaiting source sync'},503);
  const asOf=new Date(Math.min(...sync.map(s=>Date.parse(s.last_synced_at)))).toISOString(), now=Date.now();
  if(Date.parse(asOf)>now+60000)throw new Error('Invalid source timestamp');
  const today=day(now), week=monday(today), start=new Date(midnight(addDays(week,-1))).toISOString();
  const [sales,cards,opening,rates,pension,overrides,settings]=await Promise.all([
   rows('analytics_sales_lines',{select:'sales_line_id,trading_date,closed_at,sales_ex_vat_eur',closed_at:`gte.${start}`,trading_date:`gte.${week}`,order:'sales_line_id'}),
   rows('square_timecards',{select:'id,team_member_id,start_at,end_at,status,hourly_rate_amount,raw_json',start_at:`gte.${start}`,location_id:'eq.L05Y6CVDJJN86',order:'id'}),
   rows('analytics_opening_hours_daily',{select:'trading_date,close_next_day',trading_date:`gte.${addDays(week,-1)}`,order:'trading_date'}),
   rows('analytics_prsi_rates',{select:'*',order:'effective_from'}),
   rows('analytics_pension_default_rates',{select:'*',order:'effective_from'}),
   rows('analytics_employee_cost_overrides',{select:'*',order:'id'}),
   rows('analytics_settings',{select:'key,value_json',key:'in.(default_annual_leave_accrual_rate,default_other_employer_cost_rate)',order:'key'})
  ]);
  return reply(calculate({asOf,now,sales,cards,opening,rates,pension,overrides,settings}));
 }catch{ return reply({error:'Data temporarily unavailable'},503); }
});
