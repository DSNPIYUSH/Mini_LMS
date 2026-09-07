#!/usr/bin/env bash
# Render Build Script for Subject Bank
set -o errexit

echo "--- Installing Dependencies ---"
pip install -r requirements.txt

echo "--- Collecting Static Files ---"
python manage.py collectstatic --noinput

echo "--- Applying Database Migrations ---"
python manage.py migrate

echo "--- Ensuring Admin Superuser Exists ---"
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser admin created successfully!')
else:
    print('Superuser admin already exists.')
"

echo "--- Build Completed Successfully! ---"
