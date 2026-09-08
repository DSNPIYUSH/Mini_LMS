#!/usr/bin/env bash
# Render Build Script for Subject Bank
set -o errexit

echo "--- Installing Dependencies ---"
pip install -r requirements.txt

echo "--- Collecting Static Files ---"
python manage.py collectstatic --noinput

echo "--- Applying Database Migrations ---"
python manage.py migrate

echo "--- Configuring Admin Superuser ---"
python set_admin.py

echo "--- Build Completed Successfully! ---"
