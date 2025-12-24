
import random

def send_otp(destination: str) -> str:
    otp = str(random.randint(100000, 999999))
    print(f"OTP for {destination}: {otp}")
    return otp

def verify_otp(sent: str, received: str) -> bool:
    return sent == received
