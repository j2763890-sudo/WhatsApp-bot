 from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
import requests, re, os, uuid
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
os.makedirs("/tmp/files", exist_ok=True)
MAX_SIZE = 500 * 1024 * 1024 # 500MB

BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

def get_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://', HTTPAdapter(max_retries=retry))
    session.headers.update(BASE_HEADERS)
    return session

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
        # intenta adivinar por content-type
        ct = r.headers.get('Content-Type','')
        if 'apk' in ct:
            name += ".apk"
        else:
            name += ".mp4"
    return name

@app.route("/", methods=["GET","POST"])
def bot():
    if request.method == "GET":
        return "Downloader 500MB ON", 200

    msg = request.values
