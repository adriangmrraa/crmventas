"""
Nexus Security Middleware — CRM Ventas
Basado en ClinicForge Nexus Security v7.6.
Implementa cabeceras proactivas para blindar el orchestrator contra XSS,
Clickjacking y degradación de protocolo.
"""
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Nexus Security Middleware v2.0: Headers HTTP de seguridad en todas las respuestas.

    Headers implementados:
    - X-Frame-Options: DENY (anti-clickjacking)
    - X-Content-Type-Options: nosniff (anti-MIME-sniffing)
    - Strict-Transport-Security: HSTS (forzar HTTPS)
    - Content-Security-Policy: CSP dinámico basado en CORS_ALLOWED_ORIGINS
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # 1. Anti-clickjacking: previene que la API sea embebida en iframes maliciosos
        response.headers["X-Frame-Options"] = "DENY"

        # 2. Anti-MIME-sniffing: forzar al navegador a respetar el Content-Type enviado
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 3. HSTS: Forzar HTTPS. max-age de 6 meses (15768000 seg) incluyendo subdominios
        response.headers["Strict-Transport-Security"] = "max-age=15768000; includeSubDomains"

        # 4. Content-Security-Policy dinámico basado en CORS_ALLOWED_ORIGINS + CSP_EXTRA_DOMAINS
        allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        extra_domains = os.getenv("CSP_EXTRA_DOMAINS", "").split(",")

        # Limpiar y normalizar dominios (quitar protocolos/rutas)
        csp_domains = set()
        for domain in allowed_origins + extra_domains:
            d = domain.strip()
            if d:
                if "://" in d:
                    d = d.split("://")[1].split("/")[0]
                csp_domains.add(d)

        # Dominios de confianza base (APIs externas) + dinámicos
        trusted_connect = [
            "*.openai.com",
            "*.facebook.com",
            "*.messenger.com",
            "*.fbcdn.net",
            "*.ycloud.com",  # YCloud WhatsApp
            "api.apify.com",  # Apify scraping
        ]
        connect_src = " ".join(["'self'"] + trusted_connect + list(csp_domains))

        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-inline'; "
            f"style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
            f"font-src 'self' fonts.gstatic.com; "
            f"img-src 'self' data: blob:; "
            f"media-src 'self' blob:; "
            f"connect-src {connect_src}; "
            f"frame-ancestors 'none'; "
            f"object-src 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        return response
