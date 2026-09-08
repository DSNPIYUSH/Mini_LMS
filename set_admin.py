import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'subject_bank.settings')
django.setup()

from django.contrib.auth import get_user_model

def configure_admin():
    User = get_user_model()
    
    username = os.getenv('ADMIN_USERNAME', '').strip()
    password = os.getenv('ADMIN_PASSWORD', '').strip()
    email = os.getenv('ADMIN_EMAIL', 'admin@example.com').strip()

    if not username or not password:
        print("Error: ADMIN_USERNAME and ADMIN_PASSWORD must be set in your .env file!")
        return

    # Delete default 'admin' if username is different
    if username != 'admin' and User.objects.filter(username='admin').exists():
        User.objects.filter(username='admin').delete()
        print("Removed default 'admin' user.")

    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.create_superuser(username, email, password)
        print(f"Created new superuser: '{username}'")
    else:
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"Updated password for superuser: '{username}'")

    print(f"\nSUCCESS: You can now log in at /login/ or /admin/ with:")
    print(f"  Username: {username}")
    print(f"  Password: {password}\n")

if __name__ == '__main__':
    configure_admin()
