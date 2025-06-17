#!/bin/bash
chown postgres:postgres /etc/postgresql/ssl/postgres.key /etc/postgresql/ssl/postgres.crt /etc/postgresql/ssl/root_ca.crt
chmod 600 /etc/postgresql/ssl/postgres.key