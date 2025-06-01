from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import shutil
import zipfile
from datetime import timedelta
import uuid

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
TEMP_FOLDER = "temp"

for folder in [DOWNLOAD_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'skip_download': True,
        'format': 'bestaudio/best'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info

def format_duration(seconds):
    return str(timedelta(seconds=int(seconds)))

@app.route("/", methods=["GET", "POST"])
def index():
    videos_info = []
    url = ""
    is_playlist = False
    error = ""

    if request.method == "POST":
        url = request.form["url"]
        try:
            info = get_video_info(url)
            if 'entries' in info:
                is_playlist = True
                for entry in info['entries']:
                    videos_info.append({
                        "title": entry.get("title"),
                        "thumbnail_url": entry.get("thumbnail"),
                        "duration": format_duration(entry.get("duration", 0)),
                        "video_url": entry.get("url")
                    })
            else:
                videos_info.append({
                    "title": info.get("title"),
                    "thumbnail_url": info.get("thumbnail"),
                    "duration": format_duration(info.get("duration", 0)),
                    "video_url": info.get("webpage_url")
                })
        except Exception as e:
            error = str(e)

    return render_template("index.html", videos=videos_info, url=url, is_playlist=is_playlist, error=error)

@app.route("/download", methods=["POST"])
def download_audio():
    video_url = request.form["video_url"]
    filename = str(uuid.uuid4()) + ".mp3"
    output_path = os.path.join(DOWNLOAD_FOLDER, filename)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return send_file(output_path, as_attachment=True)

@app.route("/download_zip", methods=["POST"])
def download_zip():
    playlist_url = request.form["playlist_url"]
    zip_name = f"playlist_{uuid.uuid4().hex[:8]}.zip"
    zip_path = os.path.join(DOWNLOAD_FOLDER, zip_name)

    temp_dir = os.path.join(TEMP_FOLDER, uuid.uuid4().hex)
    os.makedirs(temp_dir)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            zipf.write(file_path, arcname=file)
            os.remove(file_path)

    shutil.rmtree(temp_dir)
    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
