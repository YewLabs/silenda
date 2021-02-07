#!/bin/bash -x

trap "kill 0" EXIT

export DJANGO_ENV=${1:-dev}

if [[ "$DJANGO_ENV" == "prod" ]]; then
    cloud_sql_proxy -instances=<CLOUD_SQL_INSTANCE>=tcp:4206 &
    sleep 5
fi

python3 manage.py migrate
python3 manage.py import_teams
python3 manage.py import_puzzles
python3 manage.py import_unlocks
python3 manage.py reset_log
python3 manage.py unlock_admin
# python3 manage.py launch

if [[ "$DJANGO_ENV" == "prod" ]]; then
    pkill cloud_sql_proxy;
fi
