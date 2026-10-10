from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import requests
import re
import os
import uuid
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
os.makedirs("/tmp/files", exist_ok=True)
MAX_SIZE = 500 * 1024 * 1024

BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Connection': 'keep-alive',
}

def get_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504])
    s.mount('https://', HTTPAdapter(max_retries=retry))
    s.mount('http://', HTTPAdapter(max_retries=retry))
    s.headers.update(BASE_HEADERS)
    return s

def get_filename(r, url):
    cd = r.headers.get('Content-Disposition','')
    if 'filename=' in cd:
        m = re.search(r'filename="?([^"]+)"?', cd)
        if m:
            return re.sub(r'[^a-zA-Z0-9._-]', '', m.group(1))[:80]
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    name = re.sub(r'[^a-zA-Z0-9._-]', '', name)[:80]
    if not name or len(name) < 5:
        name = f"file_{uuid.uuid4().hex[:6]}.apk"
    if "." not in name:
        if 'apk' in r.headers.get('Content-Type',''):
            name += ".apk"
        else:
            name += ".mp4"
    return name

@app.route("/", methods=["GET","POST","HEAD"])
def bot():
    if request.method == "HEAD":
        return "", 200
    if request.method == "GET":
        return "Downloader 500MB ON", 200

    msg = request.values.get('Body','').strip()
    resp = MessagingResponse()

    if not msg or "hola" in msg.lower():
        resp.message("Downloader listo. Mandame el link https://")
        return str(resp), 200, {'Content-Type':'text/xml'}

    urls = re.findall(r'(https?://[^\s]+)', msg)
    if not urls:
        resp.message("Mandame un https://")
        return str(resp), 200, {'Content-Type':'text/xml'}

    url = urls[0].strip()
    headers = BASE_HEADERS.copy()
    if "apkcombo" in url:
        headers['Referer'] = 'https://apkcombo.com/'
    elif "aptoide" in url:
        headers['Referer'] = 'https://zynga-poker.es.aptoide.com/'
    elif "apkmirror" in url:
        headers['Referer'] = 'https://www.apkmirror.com/'
    elif "apkpure" in url:
        headers['Referer'] = 'https://apkpure.com/'
    else:
        headers['Referer'] = url

    try:
        session = get_session()
        r = session.get(url, stream=True, timeout=90, headers=headers, allow_redirects=True)
        r.raise_for_status()
        filename = get_filename(r, url)
        filepath = f"/tmp/files/{filename}"
        size = 0
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(1024*1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_SIZE:
                    break
                f.write(chunk)

        base_url = request.url_root.rstrip('/')
        file_url = f"{base_url}/files/{filename}"
        mb = size / (1024*1024)

        if size > 15 * 1024 * 1024:
            resp.message(f"Listo: {filename} - {mb:.1f}MB\nBajalo aqui:\n{file_url}")
        else:
            m = resp.message(f"Listo: {filename} - {mb:.1f}MB")
            m.media(file_url)

        return str(resp), 200, {'Content-Type':'text/xml'}

    except Exception as e:
        err = str(e)[:400]
        if "NameResolutionError" in err or "Failed to resolve" in err:
            resp.message(f"No se pudo resolver el dominio de:\n{url}\n\nRender no resuelve apkcombo.com en plan gratis.\nPrueba con el mismo juego pero de apkpure.com o apkmirror.com y si jala.")
        else:
            resp.message(f"Error: {err}")
        return str(resp), 200, {'Content-Type':'text/xml'}

@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory("/tmp/files", filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
