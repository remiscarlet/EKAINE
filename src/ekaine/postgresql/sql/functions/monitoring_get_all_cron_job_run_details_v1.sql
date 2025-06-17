create or replace function monitoring.get_all_cron_job_run_details()
returns setof cron.job_run_details
language sql
security definer
as $$
  SELECT * FROM cron.job_run_details;
$$;
