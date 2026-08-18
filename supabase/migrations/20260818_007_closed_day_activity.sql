create or replace view public.analytics_closed_day_activity as
with sales as (
    select trading_date,
           count(distinct order_id) as orders,
           sum(sales_inc_vat_eur) as sales_inc_vat_eur
    from analytics_sales_lines
    group by trading_date
), labour as (
    select trading_date,
           sum(worked_hours) as worked_hours,
           sum(loaded_labour_cost_eur) as loaded_labour_cost_eur
    from analytics_labour_day_segments
    group by trading_date
)
select
    oh.trading_date,
    oh.schedule_text,
    oh.source_file,
    coalesce(s.orders, 0::bigint) as orders,
    coalesce(s.sales_inc_vat_eur, 0::numeric) as sales_inc_vat_eur,
    coalesce(l.worked_hours, 0::numeric) as worked_hours,
    coalesce(l.loaded_labour_cost_eur, 0::numeric) as loaded_labour_cost_eur
from analytics_opening_hours_daily oh
left join sales s using (trading_date)
left join labour l using (trading_date)
where not oh.is_scheduled_open
  and (coalesce(s.orders, 0::bigint) > 0
       or coalesce(l.worked_hours, 0::numeric) > 0);
