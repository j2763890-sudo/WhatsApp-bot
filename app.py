from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import requests
import re
import os
import uuid
from urllib.parse import urlparse

app = Flask(__name__)

# Carpeta donde se guardan temporalmente
os.makedirs("/tmp/files", exist_ok=True)

# Limite WhatsApp: 15 MB
MAX_SIZE = 15 * 1024 * 1024

@app.route("/", methods=["GET", "POST"])
def bot():
    if request.method == "GET":
        return "Downloader Activo", 200

    msg = request.values.get('Body','').strip()
    resp = MessagingResponse()

    if not msg or "hola" in msg.lower():
        resp.message("Hola Soy Downloader\nMandame un LINK DIRECTO de archivo (pdf, jpg, apk, zip, mp3) y te lo regreso por aqui.\nEj: https://ejemplo.com/archivo.pdf")
        return str(resp), 200, {'Content-Type':'text/xml'}

    urls = re.findall(r'(https?://[^\s]+)', msg)
    if not urls:
        resp.message("Mandame un link que empiece con https://")
        return str(resp), 200, {'Content-Type':'text/xml'}

    url = urls[0]
    # Bloqueo YouTube/TikTok por ToS
    if "youtube.com" in url or "youtu.be" in url or "tiktok.com" in url:
        resp.message("YouTube/TikTok no se pueden bajar directo por politicas, pero mandame el link DIRECTO del archivo.mp4 y si te lo bajo.")
        return str(resp), 200, {'Content-Type':'text/xml'}

    try:
        # Descarga con limite
        r = requests.get(url, stream=True, timeout=20, headers={'User-Agent':'Mozilla/5.0'})
        r.raise_for_status()

        # Detecta nombre
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or f"archivo_{uuid.uuid4().hex[:6]}.bin"
        # Limpia nombre
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)[:40]
        filepath = f"/tmp/files/{filename}"

        size = 0
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(1024*10):
                size += len(chunk)
                if size > MAX_SIZE:
                    f.close()
                    os.remove(filepath)
                    resp.message(f"Archivo muy grande >15MB, WhatsApp no lo permite. Busca un link mas ligero.")
                    return str(resp), 200, {'Content-Type':'text/xml'}
                f.write(chunk)

        # URL publica para que Twilio la mande
        # Tienes que poner tu dominio de render aqui
        base_url = request.url_root.rstrip('/')
        file_url = f"{base_url}/files/{filename}"

        msg_obj = resp.message(f"Listo, aqui esta tu archivo: {filename} ({size//1024} KB)")
        msg_obj.media(file_url)
        return str(resp), 200, {'Content-Type':'text/xml'}

    except Exception as e:
        print(f"Error descarga: {e}")
        resp.message(f"No pude bajarlo: {str(e)[:100]}\nAsegurate que sea link DIRECTO a archivo, no pagina web.")
        return str(resp), 200, {'Content-Type':'text/xml'}

@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory("/tmp/files", filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
