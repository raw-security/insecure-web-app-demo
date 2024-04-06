#!/bin/bash

cat schema.sql | sqlite3 /tmp/shop.db
gunicorn -b 0.0.0.0:8080 app:app