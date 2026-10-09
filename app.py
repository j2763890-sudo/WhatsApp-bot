from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import re
from urllib.parse import urlparse
import ipaddress

app = Flask(__name__)

# --- LISTAS POTENTES ---
SHORTENERS = ['bit.ly', 'tinyurl.com', 't.me', 'goo.gl', 'is.gd', 'cutt.ly', 'rebrand.ly', 'shorturl.at']
SUSPICIOUS_TLDS = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.work', '.click']
BRANDS = ['paypal', 'banorte', 'bbva', 'banco', 'netflix', 'amazon', 'microsoft', 'apple', 'whatsapp']

def es_ip(url):
    try:
        host = urlparse(url).netloc
        ipaddress.ip_address(host.split(':')[0])
        return True
    except:
        return False

def analizar_url(url):
    if not url.startswith('http'):
        url = 'http://' + url

    parsed = urlparse(url)
    dominio = parsed.netloc.lower()
    puntaje = 0
    razones = []

    # 1. Es IP en lugar de dominio
    if es_ip(url):
        puntaje += 3
        razones.append("🔴 Usa dirección IP en lugar de dominio (muy sospechoso)")

    # 2. Acortador
    if any(s in dominio for s in SHORTENERS):
        puntaje += 2
        razones.append("🟡 Usa acortador, oculta el destino real")

    # 3. Arroba @ en la URL
    if "@" in url:
        puntaje += 3
        razones.append("🔴 Contiene @, técnica para engañar")

    # 4. Muchos subdominios
    if dominio.count('.') > 3:
        puntaje += 2
        razones.append("🟡 Demasiados subdominios")

    # 5. TLD sospechoso
    if any(dominio.endswith(tld) for tld in SUSPICIOUS_TLDS):
        puntaje += 2
        razones.append("🟡 Dominio con extensión de alto riesgo")

    # 6. Suplantación de marca
    for brand in BRANDS:
        if brand in dominio and brand not in dominio.split('.')[0]:
            # ej: paypal-seguro-login.tk
            if f"{brand}.com" not in dominio and f"{brand}.com.mx" not in dominio:
                puntaje += 3
                razones.append(f"🔴 Posible suplantación de {brand.upper()}")
                break

    # 7. Guiones excesivos
    if dominio.count('-') >= 3:
        puntaje += 1
        razones.append("🟡 Muchos guiones en el dominio")

    # 8. No tiene HTTPS
    if parsed.scheme == 'http':
        puntaje += 1
        razones.append("🟡 No usa HTTPS")

    return puntaje, razones, dominio

@app.route("/", methods=["GET
