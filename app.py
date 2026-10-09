from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import requests, re, os, uuid
from urllib.parse import urlparse

app = Flask(__name__)
os.makedirs("/tmp/files", exist_ok=True)
MAX_SIZE = 500 * 1024 * 1024 # 500MB para Render

@app.route("/", methods=["GET","POST"])
def bot():
    if request.method == "GET":
        return "Downloader 500MB ON", 200

    msg = request.values.get('Body','').strip()
    resp = MessagingResponse()

    if not msg or "hola" in msg.lower():
        resp.message("Downloader listo. Mandame el link directo https://")
        return str(resp), 200, {'Content-Type':'text/xml'}

    urls = re.findall(r'(https?://[^\s]+)', msg)
    if not urls:
        resp.message("Mandame un https://")
        return str(resp), 200, {'Content-Type':'text/xml'}

    url = urls[0].strip()

    try:
        r = requests.get(url, stream=True, timeout=60, headers={'User-Agent':'Mozilla/5.0'}, allow_redirects=True)
        r.raise_for_status()

        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or f"file_{uuid.uuid4().hex[:6]}.mp4"
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)[:80]
        if "." not in filename:
            filename += ".mp4"

        filepath = f"/tmp/files/{filename}"
        size = 0
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(1024*1024):
                if not chunk: continue
                size += len(chunk)
                if size > MAX_SIZE:
                    break
                f.write(chunk)

        base_url = request.url_root.rstrip('/')
        file_url = f"{base_url}/files/{filename}"
        mb = size / (1024*1024)

        if size > 15 * 1024 * 1024:
            resp.message(f"Listo: {filename} - {mb:.1f}MB\nPesa mucho para WhatsApp, bajalo aqui:\n{file_url}")
        else:
            m = resp.message(f"Listo: {filename} - {mb:.1f}MB")
            m.media(file_url)

        return str(resp), 200, {'Content-Type':'text/xml'}

    except Exception as e:
        resp.message(f"Error: {str(e)[:200]}")
        return str(resp), 200, {'Content-Type':'text/xml'}

@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory("/tmp/files", filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
