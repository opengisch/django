#!/bin/sh
# Runs once, on first container start, via the postgis image's
# docker-entrypoint-initdb.d mechanism. The "default" database
# (POSTGRES_DB) is created by the image itself; this adds the second
# database used by the Django test suite's DATABASES["other"] alias.
set -e

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres <<-SQL
    CREATE DATABASE geodjango2 OWNER "${POSTGRES_USER}";
SQL
