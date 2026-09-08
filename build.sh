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
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.getenv('ADMIN_USERNAME', 'admin').strip()
password = os.getenv('ADMIN_PASSWORD', 'admin123').strip()
email = os.getenv('ADMIN_EMAIL', 'admin@example.com').strip()

user = User.objects.filter(username=username).first()
if not user:
    user = User.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created successfully!')
else:
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f'Superuser {username} updated successfully!')
"

echo "--- Build Completed Successfully! ---"
