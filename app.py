from flask import Flask, render_template, Response
import requests
import xml.etree.ElementTree as ET
import os
from try2 import stream_video

REDIS_HOST = os.environ['REDIS_HOST']
REDIS_PORT = int(os.environ['REDIS_PORT'])
REDIS_USER = os.environ['REDIS_USER']
REDIS_PASSWORD = os.environ['REDIS_PASSWORD']
VIDEO_SERVER_HOST = os.environ['VIDEO_SERVER_HOST']

app = Flask(__name__)

@app.route('/')
def list_s3_files():
    """List available videos from S3"""
    s3_api = VIDEO_SERVER_HOST
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

        html = """
        <html>
        <head>
            <title>S3 Media</title>
            <style>
                body { font-family: Arial; margin: 20px; }
                ul { list-style-type: none; padding: 0; }
                li { margin: 8px 0; }
                a { color: #007BFF; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h2>🎥 S3 Media Files</h2>
            <ul>
            {% for f in files %}
                <li><a href="/watch/{{ f.name | urlencode }}">{{ f.name }}</a> — {{ f.size }}</li>
            {% endfor %}
            </ul>
        </body>
        </html>
        """
        from flask import render_template_string
        return render_template_string(html, files=files)
    except Exception as e:
        return f"<h3>❌ Error parsing XML: {e}</h3>"

@app.route("/watch/<path:video_name>")
def watch(video_name):
    """Watch video - tries Redis first, falls back to direct stream"""
    # Try to get video from Redis
    redis_response = stream_video(video_name)
    
    if redis_response:
        # Video found in Redis, return it directly
        return redis_response
    else:
        # Video not in Redis, show HTML that will stream from S3
        return render_template("watch.html", video_url=f"/stream/{video_name}")

@app.route("/stream/<path:video_name>")
def stream(video_name):
    """Stream video directly from S3"""
    internal_url = f"{VIDEO_SERVER_HOST}{video_name}"
    
    try:
        req = requests.get(internal_url, stream=True, timeout=30)
        return Response(
            req.iter_content(chunk_size=8192),
            content_type=req.headers.get('Content-Type', 'video/mp4'),
            headers={
                'Content-Disposition': f'inline; filename="{video_name}"',
                'Cache-Control': 'no-cache'
            }
        )
    except Exception as e:
        return f"Error streaming video: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)