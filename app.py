from flask import Flask, render_template, Response
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import os
from try2 import stream_video

app = Flask(__name__)
NGINX_URL = os.getenv('NGINX_URL', 'http://storage-video-prab.s3.amazonaws.com/')

@app.route('/')
def list_s3_files():
    """List available videos from S3"""
    s3_api = "http://storage-video-prab.s3.amazonaws.com/"
    try:
        response = requests.get(s3_api)
        response.raise_for_status()
    except Exception as e:
        return f"<h3>❌ Failed to fetch S3 listing: {e}</h3>"

    try:
        root = ET.fromstring(response.content)
        ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}

        files = []
        for item in root.findall('s3:Contents', ns):
            key = item.find('s3:Key', ns).text
            size = int(item.find('s3:Size', ns).text)
            if key.lower().endswith(('.mp4', '.mkv', '.mov', '.webm', '.mp3', '.wav')):
                files.append({
                    'name': key,
                    'size': f"{size / (1024*1024):.2f} MB"
                })

        return render_template('index.html', files=files)
    except Exception as e:
        return f"<h3>❌ Error parsing XML: {e}</h3>"

@app.route("/watch/<path:video_name>")
def watch(video_name):
    result = stream_video(video_name)
    if isinstance(result, Response):
        # Video is in Redis, return the streaming response
        return result
    else:
        # Video not in Redis, show HTML page that will fetch from stream endpoint
        return render_template("watch.html", video_url=f"/stream/{video_name}")

@app.route("/stream/<path:video_name>")
def stream(video_name):
    # Internal cluster URL (never exposed to client)
    internal_url = f"http://storage-video-prab.s3.amazonaws.com/{video_name}"
    
    # Stream with chunked encoding
    req = requests.get(internal_url, stream=True)
    return Response(
        req.iter_content(chunk_size=1024*1024),  # 1MB chunks
        content_type=req.headers['Content-Type'],
        headers={
            'Content-Disposition': f'inline; filename="{video_name}"',
            'Cache-Control': 'no-cache'
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
