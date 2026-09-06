-- Kargin Archive — usage log table (run once in your Neon SQL editor).
create table if not exists query_log (
  id           bigint generated always as identity primary key,
  ts           timestamptz not null default now(),
  session_id   text not null,            -- random per-tab id (no personal data)
  type         text not null,            -- search | open | filter | findname | copy
  query        text,                     -- the search/name text, when applicable
  mode         text,                     -- exact (future: semantic)
  filters      jsonb,                    -- applied filters at the time
  result_count integer,
  sketch_id    text,                     -- for open/copy
  source       text,                     -- home | watch | findname | stats
  ua           text                      -- coarse user-agent (truncated)
);
create index if not exists query_log_ts_idx   on query_log (ts desc);
create index if not exists query_log_type_idx on query_log (type);

-- Handy queries once data flows:
--   select query, count(*) from query_log where type='search' and query<>'' group by query order by 2 desc limit 30;
--   select query, count(*) from query_log where type='search' and result_count=0 group by query order by 2 desc;  -- zero-result searches
--   select sketch_id, count(*) from query_log where type='open' group by sketch_id order by 2 desc limit 30;
