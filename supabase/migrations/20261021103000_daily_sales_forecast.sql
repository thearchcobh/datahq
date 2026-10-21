-- Daily forecasting state. All access is server-side through existing credentials.
begin;
create table public.arch_forecast_runs (
 id uuid primary key default gen_random_uuid(),
 generated_at timestamptz not null unique,
 as_of date not null,
 model_version text not null,
 payload jsonb not null,
 input_snapshot jsonb not null default '{}'::jsonb
);
create table public.arch_forecast_current (
 singleton boolean primary key default true check (singleton),
 run_id uuid not null references public.arch_forecast_runs(id),
 payload jsonb not null
);
alter table public.arch_forecast_runs enable row level security;
alter table public.arch_forecast_current enable row level security;
revoke all on public.arch_forecast_runs,public.arch_forecast_current from public,anon,authenticated;
grant select,insert,update on public.arch_forecast_runs,public.arch_forecast_current to service_role;
create function public.arch_forecast_inputs() returns jsonb
language sql stable security invoker set search_path=public,pg_temp as $forecast_inputs$
with bins as (
 select trading_date, floor(extract(epoch from closed_at_local::time)/1800)::int as bin, round(sum(sales_ex_vat_eur),2) as sales
 from analytics_sales_lines where trading_date < (now() at time zone 'Europe/Dublin')::date group by 1,2
), sales as (select trading_date,jsonb_object_agg(bin,sales) as bins from bins group by 1),
weather as (select (time_utc at time zone 'Europe/Dublin')::date as d, round(avg(temp_c)::numeric,2) temp,round(sum(precip_mm)::numeric,2) rain,round(avg(wind_ms)::numeric,2) wind,count(*) n,bool_or(is_forecast) forecast,max(source_fetched_at) fetched from weather_hourly where extract(hour from time_utc at time zone 'Europe/Dublin') between 8 and 21 group by 1)
select jsonb_build_object('days',(select jsonb_agg(jsonb_build_object('date',o.trading_date,'open',o.is_scheduled_open,'start',o.open_time,'end',o.close_time,'next',o.close_next_day,'bins',s.bins,'temp',w.temp,'rain',w.rain,'wind',w.wind,'weather_n',w.n,'weather_forecast',w.forecast,'weather_fetched',w.fetched) order by o.trading_date) from analytics_opening_hours_daily o left join sales s using(trading_date) left join weather w on w.d=o.trading_date),'cruises',(select jsonb_agg(jsonb_build_object('id',uid,'ship',vessel,'line',cruise_line,'port',port,'arrival',arrival,'departure',departure,'capacity',passengers,'active',active_in_latest_feed)) from cruise_calls),'sync',(select jsonb_object_agg(source,last_synced_at) from sync_state)) as inputs
$forecast_inputs$;
revoke all on function public.arch_forecast_inputs() from public,anon,authenticated;
grant execute on function public.arch_forecast_inputs() to service_role;
create function public.arch_publish_forecast(new_payload jsonb, input_snapshot jsonb default '{}'::jsonb)
returns uuid language plpgsql security invoker set search_path=public,pg_temp as $publish$
declare new_id uuid; generated timestamptz;
begin
 perform pg_advisory_xact_lock(58132947);
 generated := (new_payload->>'generated_at')::timestamptz;
 if generated is null or generated>now()+interval '5 minutes' or
    jsonb_typeof(new_payload->'days') is distinct from 'array' or jsonb_array_length(new_payload->'days')<21 or
    new_payload->>'model_version' is null or new_payload->>'as_of' is null then
   raise exception 'Invalid forecast payload';
 end if;
 if exists(select 1 from public.arch_forecast_current where (payload->>'generated_at')::timestamptz>generated) then
   raise exception 'Refusing to replace a newer forecast';
 end if;
 insert into public.arch_forecast_runs(generated_at,as_of,model_version,payload,input_snapshot)
 values(generated,(new_payload->>'as_of')::date,new_payload->>'model_version',new_payload,input_snapshot)
 on conflict(generated_at) do nothing returning id into new_id;
 if new_id is null then select id into new_id from public.arch_forecast_runs where generated_at=generated; end if;
 insert into public.arch_forecast_current(singleton,run_id,payload) values(true,new_id,new_payload)
 on conflict(singleton) do update set run_id=excluded.run_id,payload=excluded.payload;
 return new_id;
end
$publish$;
revoke all on function public.arch_publish_forecast(jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.arch_publish_forecast(jsonb,jsonb) to service_role;
commit;
