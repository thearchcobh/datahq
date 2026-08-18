create table if not exists public.analytics_opening_hours_daily (
    trading_date date primary key,
    is_scheduled_open boolean not null,
    open_time time,
    close_time time,
    close_next_day boolean not null default false,
    source_week_start date,
    schedule_text text not null,
    source_file text not null default 'Actual_and_ProjectedHours2023_2026.xlsx',
    source_precision text not null default 'exact_minutes',
    imported_at timestamptz not null default now(),
    constraint analytics_opening_hours_daily_times_chk check (
        (is_scheduled_open and open_time is not null and close_time is not null)
        or
        ((not is_scheduled_open) and open_time is null and close_time is null)
    )
);

alter table public.analytics_opening_hours_daily enable row level security;
