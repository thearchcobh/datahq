create table if not exists public.cruise_calls (
    uid text primary key,
    vessel text not null,
    cruise_line text,
    imo text,
    port text,
    arrival timestamptz not null,
    departure timestamptz not null,
    passengers integer,
    marine_traffic_url text,
    source text not null default 'port_of_cork',
    source_feed_url text,
    raw_description text,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    active_in_latest_feed boolean not null default true,
    synced_at timestamptz not null default now()
);

comment on table public.cruise_calls is
    'Historical and future Cork Harbour cruise calls. Rows are retained when calls disappear from the current source feed.';
comment on column public.cruise_calls.active_in_latest_feed is
    'True when the call is present in the latest successfully ingested Port of Cork calendar feed.';

create index if not exists cruise_calls_arrival_idx
    on public.cruise_calls (arrival);
create index if not exists cruise_calls_vessel_arrival_idx
    on public.cruise_calls (vessel, arrival);
create index if not exists cruise_calls_active_arrival_idx
    on public.cruise_calls (active_in_latest_feed, arrival);

alter table public.cruise_calls enable row level security;
revoke all on table public.cruise_calls from anon, authenticated;
grant select, insert, update on table public.cruise_calls to service_role;
