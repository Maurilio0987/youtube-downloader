
import shutil
import zipfile
from datetime import timedelta
import traceback

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
TEMP_FOLDER = "temp"

# Cria as pastas se não existirem
for folder in [DOWNLOAD_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)


def format_duration(seconds):
    return str(timedelta(seconds=seconds))


@app.route("/", methods=["GET", "POST"])
def index():
    videos_info = []
    url = ""
    is_playlist = False
    error = None

    if request.method == "POST":
        url = request.form["url"]
        try:
            if "playlist" in url:
                is_playlist = True
                pl = Playlist(url)
                pl._video_regex = r"\"url\":\"(/watch\?v=[\w-]*)"
                for video in pl.videos:
                    videos_info.append({
                        "title": video.title,
                        "thumbnail_url": video.thumbnail_url,
                        "duration": format_duration(video.length),
                        "video_url": video.watch_url
                    })
            else:
                yt = YouTube(url)
                videos_info.append({
                    "title": yt.title,
                    "thumbnail_url": yt.thumbnail_url,
                    "duration": format_duration(yt.length),
                    "video_url": yt.watch_url
                })
        except Exception as e:
            traceback.print_exc()
            error = str(e)

    return render_template("index.html", videos=videos_info, url=url, is_playlist=is_playlist, error=error)


@app.route("/download", methods=["POST"])
def download_audio():
    video_url = request.form["video_url"]
    try:
        yt = YouTube(video_url)
        audio = yt.streams.filter(only_audio=True).first()
        out_file = audio.download(output_path=DOWNLOAD_FOLDER)
        base, ext = os.path.splitext(out_file)
        new_file = base + ".mp3"
        os.rename(out_file, new_file)
        return send_file(new_file, as_attachment=True)
    except Exception as e:
        return f"Erro ao baixar: {e}"


@app.route("/download_zip", methods=["POST"])
def download_zip():
    playlist_url = request.form["playlist_url"]
    zip_path = os.path.join(DOWNLOAD_FOLDER, "playlist.zip")

    # Remove ZIP antigo se existir
    if os.path.exists(zip_path):
        os.remove(zip_path)

    try:
        pl = Playlist(playlist_url)
        pl._video_regex = r"\"url\":\"(/watch\?v=[\w-]*)"

        with zipfile.ZipFile(zip_path, "w") as zipf:
            for video in pl.videos:
                yt = YouTube(video.watch_url)
                audio = yt.streams.filter(only_audio=True).first()
                out_file = audio.download(output_path=TEMP_FOLDER)
                base, ext = os.path.splitext(out_file)
                new_file = base + ".mp3"
                os.rename(out_file, new_file)
                zipf.write(new_file, os.path.basename(new_file))
                os.remove(new_file)

        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return f"Erro ao baixar playlist: {e}"

    finally:
        # Limpeza da pasta temp
        shutil.rmtree(TEMP_FOLDER)
        os.makedirs(TEMP_FOLDER, exist_ok=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
