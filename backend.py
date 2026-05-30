from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os, json, shutil, subprocess
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ─── Rutas universales (funciona en Android, PC, servidor en la nube) ───
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
THUMB_DIR    = os.path.join(DOWNLOAD_DIR, '.thumbnails')
HISTORY_FILE = os.path.join(DOWNLOAD_DIR, 'history.json')
STATS_FILE   = os.path.join(DOWNLOAD_DIR, 'stats.json')

for d in [DOWNLOAD_DIR, THUMB_DIR]:
    os.makedirs(d, exist_ok=True)

download_progress = {'percent': 0, 'speed': '0 MB/s', 'eta': '0s'}

# ─── Stats ───────────────────────────────────────────────────────────────
def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f: return json.load(f)
        except: pass
    return {'total_downloads':0,'total_mb':0,
            'platforms':{'YouTube':0,'TikTok':0,'Facebook':0,'Instagram':0},
            'audio_only':0}

def save_stats(s):
    with open(STATS_FILE,'w') as f: json.dump(s, f, indent=2)

def update_stats(platform, size_mb, is_audio=False):
    s = load_stats()
    s['total_downloads'] += 1
    s['total_mb'] += size_mb
    if platform not in s['platforms']: s['platforms'][platform] = 0
    s['platforms'][platform] += 1
    if is_audio: s['audio_only'] += 1
    save_stats(s)

# ─── Historial ───────────────────────────────────────────────────────────
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f: return json.load(f)
        except: return []
    return []

def save_history(item):
    h = load_history()
    h.insert(0, item)
    h = h[:100]
    with open(HISTORY_FILE,'w') as f: json.dump(h, f, indent=2)

# ─── Thumbnail ───────────────────────────────────────────────────────────
def generate_thumbnail(video_path, filename):
    try:
        tp = os.path.join(THUMB_DIR, filename + '.jpg')
        subprocess.run(
            ['ffmpeg','-i',video_path,'-ss','00:00:01','-vframes','1',
             '-vf','scale=120:90', tp, '-y'],
            capture_output=True, timeout=10)
        return tp if os.path.exists(tp) else None
    except: return None

# ─── Hook de progreso ────────────────────────────────────────────────────
def progress_hook(d):
    global download_progress
    if d['status'] == 'downloading':
        dl  = d.get('downloaded_bytes', 0)
        tot = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        if tot > 0:
            download_progress['percent'] = round((dl/tot)*100, 1)
            spd = d.get('speed', 0)
            download_progress['speed'] = f"{spd/1024/1024:.2f} MB/s" if spd else "calculando..."
            eta = d.get('eta', 0)
            download_progress['eta'] = f"{eta}s" if eta else "..."
    elif d['status'] == 'finished':
        download_progress.update({'percent':100,'speed':'¡Listo!','eta':'0s'})

# ─── Rutas API ───────────────────────────────────────────────────────────
@app.route('/download', methods=['POST'])
def download():
    global download_progress
    data       = request.json
    url        = data.get('url')
    quality    = data.get('quality', 'best')
    audio_only = data.get('audio_only', False)
    mode       = data.get('mode', 'turbo')
    if not url: return jsonify({'error':'No URL'}), 400

    u = url.lower()
    if   'youtube.com' in u or 'youtu.be' in u: platform = 'YouTube'
    elif 'tiktok'      in u:                     platform = 'TikTok'
    elif 'facebook'    in u or 'fb.watch' in u:  platform = 'Facebook'
    elif 'instagram'   in u:                     platform = 'Instagram'
    else:                                         platform = 'Unknown'

    download_progress = {'percent':0, 'speed':'0 MB/s', 'eta':'...'}
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    fragments  = 32 if mode == 'pro' else 16
    chunk_size = 20971520 if mode == 'pro' else 10485760
    retries    = 20 if mode == 'pro' else 10

    opts = {
        'outtmpl'  : os.path.join(DOWNLOAD_DIR, f'%(title)s_{timestamp}.%(ext)s'),
        'progress_hooks': [progress_hook],
        'quiet'    : True,
        'no_warnings': True,
        'concurrent_fragment_downloads': fragments,
        'http_chunk_size': chunk_size,
        'retries'  : retries,
        'fragment_retries': retries,
        'socket_timeout': 30,
        'force_ipv4': True,
        'cachedir' : os.path.join(DOWNLOAD_DIR, '.cache'),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        }
    }

    if platform == 'YouTube':
        fm = {
            'best' : 'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '720p' : 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]',
            '480p' : 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]'
        }
        opts['format'] = fm.get(quality, fm['best'])
    elif platform == 'TikTok':
        opts['format'] = 'best[ext=mp4]/best'
        opts['http_headers'] = {'User-Agent':'Mozilla/5.0','Referer':'https://www.tiktok.com/'}
    elif platform == 'Instagram':
        opts['format'] = 'best[ext=mp4]/best'
        opts['http_headers'] = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) '
                          'AppleWebKit/605.1.15'
        }
    else:
        opts['format'] = 'best[ext=mp4]/best'

    if audio_only:
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320'
        }]

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info  = ydl.extract_info(url, download=True)
            title = info.get('title', 'Video')
            ext   = 'mp3' if audio_only else 'mp4'
            fname = f"{title}_{timestamp}.{ext}"
            fpath = os.path.join(DOWNLOAD_DIR, fname)

            # Buscar el archivo si no tiene el nombre exacto
            if not os.path.exists(fpath):
                for e in ['mp4','webm','mkv','mp3','m4a']:
                    tp = os.path.join(DOWNLOAD_DIR, f"{title}_{timestamp}.{e}")
                    if os.path.exists(tp):
                        fpath = tp; fname = os.path.basename(tp); break

            if not os.path.exists(fpath):
                all_f = [f for f in os.listdir(DOWNLOAD_DIR)
                         if os.path.isfile(os.path.join(DOWNLOAD_DIR,f))
                         and not f.endswith('.json')]
                if all_f:
                    latest = max(all_f, key=lambda f: os.path.getmtime(
                        os.path.join(DOWNLOAD_DIR,f)))
                    fpath = os.path.join(DOWNLOAD_DIR, latest); fname = latest

            if not os.path.exists(fpath):
                return jsonify({'error':'Archivo no encontrado después de descargar'}), 500

            if not audio_only:
                generate_thumbnail(fpath, fname)

            sz = os.path.getsize(fpath)
            update_stats(platform, sz/(1024*1024), audio_only)
            save_history({
                'title'     : title,
                'filename'  : fname,
                'url'       : url,
                'size'      : f"{sz/(1024*1024):.2f} MB",
                'date'      : datetime.now().strftime('%Y-%m-%d %H:%M'),
                'platform'  : platform,
                'type'      : 'Audio MP3' if audio_only else 'Video MP4',
                'mode'      : mode.upper()
            })
            return jsonify({
                'success' : True,
                'title'   : title,
                'filename': fname,
                'size'    : f"{sz/(1024*1024):.2f} MB"
            })
    except Exception as e:
        return jsonify({'error': str(e)[:300], 'success': False}), 500

@app.route('/progress')
def get_progress(): return jsonify(download_progress)

@app.route('/thumbnail/<path:filename>')
def get_thumbnail(filename):
    tp = os.path.join(THUMB_DIR, filename + '.jpg')
    return send_file(tp, mimetype='image/jpeg') if os.path.exists(tp) else ('', 404)

@app.route('/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        fp = os.path.join(DOWNLOAD_DIR, filename)
        if os.path.exists(fp):
            os.remove(fp)
            tp = os.path.join(THUMB_DIR, filename + '.jpg')
            if os.path.exists(tp): os.remove(tp)
            return jsonify({'success': True})
        return jsonify({'error': 'No encontrado'}), 404
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/history')
def get_history(): return jsonify(load_history())

@app.route('/stats')
def get_stats(): return jsonify(load_stats())

@app.route('/files')
def get_files():
    try:
        ft = request.args.get('type','all')
        files = []
        history = load_history()
        if os.path.exists(DOWNLOAD_DIR):
            for fn in os.listdir(DOWNLOAD_DIR):
                if fn.startswith('.') or fn.endswith('.json'): continue
                is_v = fn.endswith(('.mp4','.webm','.mkv'))
                is_a = fn.endswith(('.mp3','.m4a'))
                if ft == 'video' and not is_v: continue
                if ft == 'audio' and not is_a: continue
                if ft == 'all'   and not (is_v or is_a): continue
                fp = os.path.join(DOWNLOAD_DIR, fn)
                if os.path.isfile(fp):
                    st = os.stat(fp)
                    platform = 'Unknown'
                    for item in history:
                        if item.get('filename') == fn:
                            platform = item.get('platform','Unknown'); break
                    files.append({
                        'name'    : fn,
                        'size'    : f"{st.st_size/(1024*1024):.2f} MB",
                        'date'    : datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'type'    : 'Audio' if is_a else 'Video',
                        'platform': platform
                    })
        files.sort(key=lambda x: x['date'], reverse=True)
        return jsonify(files)
    except: return jsonify([])

@app.route('/open/<path:filename>')
def open_file(filename):
    fp = os.path.join(DOWNLOAD_DIR, filename)
    return send_file(fp) if os.path.exists(fp) else (jsonify({'error':'No encontrado'}), 404)

@app.route('/test')
def test(): return jsonify({'status':'OK','version':'3.0-cloud'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 RICK PRO V3 - CLOUD EDITION")
    print(f"📁 Descargas en: {DOWNLOAD_DIR}")
    print(f"🌐 Puerto: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
