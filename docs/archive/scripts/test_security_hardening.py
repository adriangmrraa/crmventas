import requests
import time
import os

# Configuración
BASE_URL = "http://localhost:8000"
IS_PRODUCTION = os.getenv("ENVIRONMENT", "production").lower() != "development"

def test_rate_limiting():
    print("--- Testeando Rate Limiting en /auth/login ---")
    email = "test@example.com"
    password = "wrongpassword"
    
    for i in range(10):
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
            print(f"Intento {i+1}: Status {response.status_code}")
            if response.status_code == 429:
                print("✅ Rate limit detectado (429 Too Many Requests)")
                return True
        except Exception as e:
            print(f"Error: {e}")
            break
        time.sleep(0.1)
    
    print("❌ Rate limit NO detectado tras 10 intentos.")
    return False

def test_security_headers():
    print("\n--- Testeando Security Headers ---")
    try:
        response = requests.get(BASE_URL)
        headers = response.headers
        
        required_headers = [
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Strict-Transport-Security"
        ]
        
        for h in required_headers:
            if h in headers:
                print(f"✅ Header {h} presente")
            else:
                print(f"❌ Header {h} AUSENTE")
    except Exception as e:
        print(f"Error conectando a {BASE_URL}: {e}")

def test_httponly_cookie():
    print("\n--- Testeando Cookies HttpOnly ---")
    # Notamos que esto requiere credenciales válidas o interceptar el login.
    # Simulamos chequeo de estructura si el login responde.
    pass

if __name__ == "__main__":
    test_rate_limiting()
    test_security_headers()
