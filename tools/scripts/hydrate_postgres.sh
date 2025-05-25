#!/usr/bin/env bash

if ! psql $DATABASE_URL -c "select * from core.systems where date > NOW() - INTERVAL '1 days' order by date desc limit 1;" >/dev/null 2>&1; then
    # If newest data is >24 hour, automatically start a Spansh dump import
    echo "Hydrating..."
    make run-pipeline
else
    echo "Database already hydrated."
fi