import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'subject_bank.settings')
django.setup()

from django.contrib.auth import get_user_model


def configure_admin():
    """
    Provision the single administrator profile from environment variables.

    Only one staff account is allowed to exist. Any other staff/superuser
    account is demoted to a regular user so regular accounts can never gain
    administrative control.
    """
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
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        print(f"Updated password for superuser: '{username}'")

    # Keep exactly one administrator: demote every other staff account.
    demoted = User.objects.filter(is_staff=True).exclude(pk=user.pk)
    for extra in demoted:
        extra.is_staff = False
        extra.is_superuser = False
        extra.save()
        print(f"Demoted extra staff account to regular user: '{extra.username}'")

    print(f"\nSUCCESS: You can now log in at /login/ or /admin/ with:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"\nCreate regular user accounts from the admin console: 'Users' button on the home page.")
    print(f"Regular users sign in at /user-login/ and get no administrative controls.\n")


if __name__ == '__main__':
    configure_admin()
