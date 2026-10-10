from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import requests, re, os, uuid
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
os.makedirs("/tmp/files", exist_ok=True)
MAX_SIZE = 500 * 1024 * 1024

# Headers que evitan 403
BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def get_session_with_retries():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://', HTTPAdapter(max_retries=retry))
    session.headers.update(BASE_HEADERS)
    return session

def get_filename_from_response(r, url):
    # 1. Intenta del header Content-Disposition
    cd = r.headers.get('Content-Disposition','')
    if 'filename=' in cd:
        m = re.search(r'filename="?([^"]+)"?', cd)
        if m:
            return m.group(1)
    # 2. Del URL
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    name = re.sub(r'[^a-zA-Z0-9._-]', '', name)[:80]
    if not name or len(name) < 4:
        name = f"file_{uuid.uuid4().hex[:6]}.apk"
    if "." not in name:
        name += ".mp4"
    return name

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

    # Fix para apkcombo / aptoide - agregar referer correcto
    headers = BASE_HEADERS.copy()
    if "apkcombo" in url:
        headers['Referer'] = 'https://apkcombo.com/'
    elif "aptoide" in url:
        headers['Referer'] = 'https://zynga-poker.es.aptoide.com/'
    elif "apkmirror" in url:
        headers['Referer'] = 'https://www.apkmirror.com/'
    else:
        headers['Referer'] = url

    try:
        session = get_session_with_retries()
        r = session.get(url, stream=True, timeout=90, headers=headers, allow_redirects=True)
        r.raise_for_status()

        filename = get_filename_from_response(r, url)
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
            m = resp.message(f"Listo: {filename} - {mb:.
