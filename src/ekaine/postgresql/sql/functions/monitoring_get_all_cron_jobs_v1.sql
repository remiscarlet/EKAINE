create or replace function monitoring.get_all_cron_jobs()
returns setof cron.job
language sql
security definer
as $$
  SELECT * FROM cron.job;
$$;
