from flask import Flask, render_template, Response
import requests
from bs4 import BeautifulSoup
import os
from try2 import stream_video

app = Flask(__name__)
NGINX_URL = os.getenv('NGINX_URL', 'http://nginx-server:80/')
@app.route("/")
def index():
    try:
        response = requests.get(NGINX_URL)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Error fetching videos: {e}", 500

    soup = BeautifulSoup(response.text, "html.parser")
    video_files = [
        link.get("href")
        for link in soup.find_all("a")
        if link.get("href") and link.get("href").lower().endswith((".mp4", ".webm", ".mkv", ".avi", ".mov"))
    ]
    return render_template("index.html", video_files=video_files)

@app.route("/watch/<video_name>")
def watch(video_name):
    # Use the streaming endpoint URL
    #return render_template("watch.html", video_url=f"/stream/{video_name}")
    return stream_video(video_name)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)