import secrets
import string
from cryptography.fernet import Fernet

def generate_secret(length=64):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    print("\n--- NEXUS SECURITY v7.7 ENVIRONMENT VARIABLES GENERATOR ---")
    print("Keep these values safe. Do NOT share them publicly.\n")
    
    jwt_secret = secrets.token_hex(64)
    admin_token = generate_secret(32)
    fernet_key = Fernet.generate_key().decode()
    
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"ADMIN_TOKEN={admin_token}")
    print(f"CREDENTIALS_FERNET_KEY={fernet_key}")
    print(f"\n# Recommended for .env in e:\\Antigravity Projects\\estabilizacion\\CRM VENTAS\\.env")
    print("\n-----------------------------------------------------------\n")

if __name__ == "__main__":
    main()
