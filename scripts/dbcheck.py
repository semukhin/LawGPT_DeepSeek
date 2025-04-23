#!/usr/bin/env python3
import os
import sys

db_host = os.environ.get('DB_HOST', 'не задан')
db_port = os.environ.get('DB_PORT', 'не задан')

print(f"DB_HOST={db_host}, DB_PORT={db_port}")
