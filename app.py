from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import re
from urllib.parse import urlparse
import ipaddress

app = Flask(__name__)

SHORTENERS = ['bit.ly','tinyurl.com','t.me','goo.gl','is.gd']
SUSPICIOUS_TLDS = ['.tk','.ml','.ga','.cf','.gq','.xyz','.top']
BRANDS = ['paypal','banorte','bbva','banco','netflix','amazon']

def es_ip(url):
    try:
        host = urlparse(url).netloc
        ipaddress.ip_address(host.split(':')[0])
        return True
    except:
        return False

def analizar(url):
    if not url.startswith('http'):
        url = 'http://' + url
    p = urlparse(url)
    d = p.netloc.lower()
    pts = 0
    rz = []
    if es_ip(url):
        pts += 3
        rz.append("Usa IP, no dominio")
    if any(s in d for s in SHORTENERS):
        pts += 2
        rz.append("Acortador")
    if "@" in url:
        pts += 3
        rz.append("Contiene @")
    if d.count('.') > 3:
        pts += 2
        rz.append("Muchos subdominios")
    if any(d.endswith(t) for t in SUSPICIOUS_TLDS):
        pts += 2
        rz.append("TLD riesgo")
    for b in BRANDS:
        if b in d and f"{b}.com" not in d:
            pts += 3
            rz.append(f"Suplanta {b}")
            break
    if d.count('-') >= 3:
        pts += 1
        rz.append("Muchos guiones")
    if p.scheme == 'http':
        pts += 1
        rz.append("Sin HTTPS")
    return pts, rz, d

@app.route("/", methods=["GET", "POST"])
def bot():
    try:
        if request.method == "GET":
            return "PhishGuard Activo", 200
        msg = request.values.get('Body', '').strip()
        urls = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', msg)
        resp = MessagingResponse()
        if not msg or "hola" in msg.lower():
            resp.message("Hola Soy PhishGuard Pro Mandame un link sospechoso.")
            return str(resp), 200, {'Content-Type': 'text/xml'}
        if not urls:
            resp.message("Mandame un link para analizar")
            return str(resp), 200, {'Content-Type': 'text/xml'}
        pts, rz, d = analizar(urls[0])
        if pts >= 5:
            lvl = "ALTO RIESGO - PHISHING"
            cons = "NO entres"
        elif pts >= 3:
            lvl = "RIESGO MEDIO"
            cons = "Cuidado"
        elif pts >= 1:
            lvl = "RIESGO BAJO"
            cons = "Revisa dominio"
        else:
            lvl = "SEGURO"
            cons = "Sin trucos"
        det = "\n".join(rz) if rz else "Limpio"
        txt = f"PhishGuard\nDominio:{d}\n{lvl}\nPuntaje:{pts}/10\n\nPor que:\n{det}\n\n{cons}"
        resp.message(txt)
        return str(resp), 200, {'Content-Type': 'text/xml'}
    except Exception as e:
        print(e)
        r = MessagingResponse()
        r.message("Error pero sigo vivo, reintenta")
        return str(r), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
