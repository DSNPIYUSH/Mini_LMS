import os
import json
import secrets
import urllib.request
import urllib.parse
from django.conf import settings

def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    code = secrets.randbelow(900000) + 100000
    return str(code)

def mask_phone_number(phone: str) -> str:
    """Mask phone number for privacy display, e.g. +91 98765 43210 -> +91 ******210."""
    cleaned = phone.strip()
    if len(cleaned) <= 4:
        return "******"
    prefix = cleaned[:3] if cleaned.startswith("+") else cleaned[:2]
    suffix = cleaned[-3:]
    masked_middle = "*" * max(4, len(cleaned) - len(prefix) - len(suffix))
    return f"{prefix} {masked_middle} {suffix}"

def send_otp_sms(phone_number: str, otp_code: str) -> bool:
    """
    Dispatches OTP via configured SMS Gateway (Twilio, Fast2SMS, or Console).
    Always logs clearly to server terminal / stdout for developer visibility.
    """
    masked_phone = mask_phone_number(phone_number)
    
    # Prominent server log (visible in terminal and Render logs)
    print("\n" + "=" * 60)
    print("*** [2-STEP VERIFICATION OTP DISPATCHED] ***")
    print(f"   Target Phone:  {phone_number} ({masked_phone})")
    print(f"   One-Time Code: {otp_code}")
    print("   Validity:      5 Minutes")
    print("=" * 60 + "\n")

    provider = os.getenv("SMS_PROVIDER", "").lower().strip()
    
    # 1. Fast2SMS Provider (Popular for Indian mobile numbers)
    fast2sms_key = os.getenv("FAST2SMS_API_KEY", "").strip()
    if provider == "fast2sms" or (not provider and fast2sms_key):
        return _send_fast2sms(phone_number, otp_code, fast2sms_key)
        
    # 2. Twilio Provider (Global SMS)
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio_from = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    if provider == "twilio" or (not provider and twilio_sid and twilio_token):
        return _send_twilio(phone_number, otp_code, twilio_sid, twilio_token, twilio_from)

    # 3. Default Console Provider (Always succeeds for testing)
    return True

def _send_fast2sms(phone: str, otp: str, api_key: str) -> bool:
    """Send SMS using Fast2SMS API (for Indian numbers)."""
    try:
        # Strip +91 or non-digits for Fast2SMS numbers field
        numbers = ''.join(c for c in phone if c.isdigit())
        if numbers.startswith("91") and len(numbers) == 12:
            numbers = numbers[2:]
            
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "authorization": api_key,
            "variables_values": otp,
            "route": "otp",
            "numbers": numbers
        }
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req, timeout=8) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            if resp_data.get("return"):
                print(f"[Fast2SMS] Successfully sent OTP to {phone}")
                return True
            else:
                print(f"[Fast2SMS Error] {resp_data.get('message')}")
                return False
    except Exception as e:
        print(f"[Fast2SMS Exception] {e}")
        return False

def _send_twilio(phone: str, otp: str, sid: str, token: str, from_phone: str) -> bool:
    """Send SMS using Twilio REST API without requiring external SDK."""
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        payload = {
            "To": phone,
            "From": from_phone,
            "Body": f"Your Subject Bank Admin verification code is: {otp}. Valid for 5 minutes."
        }
        data = urllib.parse.urlencode(payload).encode('utf-8')
        
        # HTTP Basic Auth
        import base64
        credentials = f"{sid}:{token}"
        auth_header = "Basic " + base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", auth_header)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status in (200, 201):
                print(f"[Twilio] Successfully sent OTP to {phone}")
                return True
            return False
    except Exception as e:
        print(f"[Twilio Exception] {e}")
        return False
