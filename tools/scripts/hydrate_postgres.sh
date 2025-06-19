#!/usr/bin/env bash

if ! psql "$EKAINE_DATABASE_URL" -tA -c "SELECT 1 FROM core.systems WHERE date > NOW() - INTERVAL '1 day' LIMIT 1;" | grep -q 1; then
    # If newest data is >24 hour, automatically start a Spansh dump import
    echo "Hydrating..."
    make run-pipeline
else
    echo "Database already hydrated."
fi