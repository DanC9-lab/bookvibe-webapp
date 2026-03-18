#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # exit on error

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_demo_data
