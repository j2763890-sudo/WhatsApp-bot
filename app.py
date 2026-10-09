import os, re, uuid, requests
from flask import Flask, request, send_from_directory, Response
import yt_dlp

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return "Bot universal OK"

@app.route("/webhook", methods=['POST','GET'])
def webhook():
    body = request.values.get('Body', '').strip()
    if not body:
        return "ok", 200
    urls = re.findall(r'https?://\S+', body)
    if not urls:
        twiml = '''<?xml version="1.0" encoding="UTF-8"?><Response><Message>❌ Mandame un link. Soporto Terabox, GDrive, Mediafire, Mega, directo, Youtube, TikTok.</Message></Response>'''
        return Response(twiml, mimetype='text/xml')
    file_url = urls[0].strip()
    try:
        # Intento directo
        direct_exts = ('.mp4','.mkv','.zip','.rar','.pdf','.apk','.mp3','.avi','.mov','.7z')
        if file_url.lower().endswith(direct_exts):
            filename = f"{uuid.uuid4().hex[:8]}_{os.path.basename(file_url).split('?')[0][:40]}"
            if not os.path.splitext(filename)[1]:
                filename += ".mp4"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            r = requests.get(file_url, stream=True, timeout=120, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200 and 'text/html' not in r.headers.get('Content-Type',''):
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(1024*1024):
                        if chunk: f.write(chunk)
                size_mb = os.path.getsize(filepath) / (1024*1024)
                base_url = request.host_url.rstrip('/')
                public_link = f"{base_url}/files/{filename}"
                twiml = f'''<?xml version="1.0" encoding="UTF-8"?><Response><Message>✅ Bajado ({size_mb:.2f} MB) {filename}\n\nTu link:\n{public_link}</Message></Response>'''
                return Response(twiml, mimetype='text/xml')

        # yt-dlp para todo lo demas
        ydl_opts = {'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s','noplaylist': True,'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(file_url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                files = [os.path.join(DOWNLOAD_FOLDER, f) for f in os.listdir(DOWNLOAD_FOLDER)]
                filename = max(files, key=os.path.getctime) if files else filename
            base = os.path.basename(filename)
            size_mb = os.path.getsize(filename) / (1024*1024) if os.path.exists(filename) else 0
            base_url = request.host_url.rstrip('/')
            public_link = f"{base_url}/files/{base}"
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?><Response><Message>✅ Bajado ({size_mb:.2f} MB) {base}\n\nTu link:\n{public_link}</Message></Response>'''
            return Response(twiml, mimetype='text/xml')
    except Exception as e:
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?><Response><Message>❌ Error: {str(e)[:300]}</Message></Response>'''
        return Response(twiml, mimetype='text/xml')

@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
