#!/bin/sh
# Railway test deploy only: there is no handouts/dist bind mount, so build the
# evidence files from this service's FLAG_* variables at start, then run the app.
set -e
python /gen/generate.py >/dev/null
exec python /app/app.py
