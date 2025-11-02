from flask import Flask, render_template, Response, request
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

def is_mobile_device():
    """Detect if the request is from a mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_indicators = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
    return any(indicator in user_agent for indicator in mobile_indicators)

@app.route('/')
def list_s3_files():
    """List available videos from S3 with responsive design"""
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
                    'size': f"{size / (1024*1024):.2f} MB",
                    'extension': key.lower().split('.')[-1].upper()
                })

        # Different templates for mobile vs desktop
        if is_mobile_device():
            # Mobile-friendly template
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>🎥 Media Files</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                        background: #f5f5f5;
                        padding: 10px;
                    }
                    .header {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 12px;
                        margin-bottom: 20px;
                        text-align: center;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    }
                    .file-grid {
                        display: grid;
                        grid-template-columns: 1fr;
                        gap: 12px;
                    }
                    .file-card {
                        background: white;
                        border-radius: 12px;
                        padding: 16px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        border-left: 4px solid #667eea;
                        transition: transform 0.2s, box-shadow 0.2s;
                    }
                    .file-card:active {
                        transform: scale(0.98);
                        box-shadow: 0 1px 4px rgba(0,0,0,0.2);
                    }
                    .file-name {
                        font-weight: 600;
                        color: #333;
                        font-size: 14px;
                        line-height: 1.4;
                        margin-bottom: 8px;
                        display: -webkit-box;
                        -webkit-line-clamp: 2;
                        -webkit-box-orient: vertical;
                        overflow: hidden;
                    }
                    .file-info {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        font-size: 12px;
                    }
                    .file-size {
                        color: #666;
                        background: #f0f0f0;
                        padding: 4px 8px;
                        border-radius: 10px;
                    }
                    .file-type {
                        color: #667eea;
                        font-weight: 600;
                    }
                    .empty-state {
                        text-align: center;
                        padding: 40px 20px;
                        color: #666;
                    }
                    .empty-state i {
                        font-size: 48px;
                        margin-bottom: 16px;
                        display: block;
                    }
                    a { 
                        text-decoration: none;
                        color: inherit;
                        display: block;
                    }
                    .search-box {
                        background: white;
                        padding: 15px;
                        border-radius: 12px;
                        margin-bottom: 15px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }
                    .search-input {
                        width: 100%;
                        padding: 12px;
                        border: 2px solid #e0e0e0;
                        border-radius: 8px;
                        font-size: 16px;
                        outline: none;
                        transition: border-color 0.2s;
                    }
                    .search-input:focus {
                        border-color: #667eea;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎬 Media Library</h1>
                    <p>{{ files|length }} files available</p>
                </div>
                
                <div class="search-box">
                    <input type="text" class="search-input" placeholder="🔍 Search videos..." onkeyup="filterFiles()">
                </div>
                
                <div class="file-grid" id="file-grid">
                    {% if files %}
                        {% for f in files %}
                        <a href="/watch/{{ f.name | urlencode }}">
                            <div class="file-card">
                                <div class="file-name">{{ f.name }}</div>
                                <div class="file-info">
                                    <span class="file-type">{{ f.extension }}</span>
                                    <span class="file-size">{{ f.size }}</span>
                                </div>
                            </div>
                        </a>
                        {% endfor %}
                    {% else %}
                        <div class="empty-state">
                            <i>📁</i>
                            <h3>No media files found</h3>
                            <p>Upload some videos to get started</p>
                        </div>
                    {% endif %}
                </div>

                <script>
                    function filterFiles() {
                        const search = document.querySelector('.search-input').value.toLowerCase();
                        const fileCards = document.querySelectorAll('.file-card');
                        
                        fileCards.forEach(card => {
                            const fileName = card.querySelector('.file-name').textContent.toLowerCase();
                            if (fileName.includes(search)) {
                                card.parentElement.style.display = 'block';
                            } else {
                                card.parentElement.style.display = 'none';
                            }
                        });
                    }
                    
                    // Pull to refresh simulation
                    let startY;
                    document.addEventListener('touchstart', e => {
                        startY = e.touches[0].clientY;
                    });
                    
                    document.addEventListener('touchmove', e => {
                        if (!startY) return;
                        const currentY = e.touches[0].clientY;
                        if (currentY - startY > 100) {
                            window.location.reload();
                        }
                    });
                </script>
            </body>
            </html>
            """
        else:
            # Desktop template
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>🎥 S3 Media Files</title>
                <style>
                    * { box-sizing: border-box; }
                    body { 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        margin: 0;
                        padding: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .header {
                        background: rgba(255,255,255,0.95);
                        backdrop-filter: blur(10px);
                        padding: 30px;
                        border-radius: 15px;
                        margin-bottom: 30px;
                        text-align: center;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    }
                    .header h1 {
                        margin: 0;
                        color: #333;
                        font-size: 2.5em;
                    }
                    .header p {
                        color: #666;
                        margin: 10px 0 0 0;
                        font-size: 1.1em;
                    }
                    .file-table {
                        background: rgba(255,255,255,0.95);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        overflow: hidden;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                    }
                    .table-header {
                        background: #2c3e50;
                        color: white;
                        padding: 20px;
                        display: grid;
                        grid-template-columns: 3fr 1fr 1fr;
                        gap: 20px;
                        font-weight: 600;
                    }
                    .table-row {
                        display: grid;
                        grid-template-columns: 3fr 1fr 1fr;
                        gap: 20px;
                        padding: 15px 20px;
                        border-bottom: 1px solid #eee;
                        transition: background-color 0.2s;
                        align-items: center;
                    }
                    .table-row:hover {
                        background: #f8f9fa;
                    }
                    .table-row:last-child {
                        border-bottom: none;
                    }
                    .file-name {
                        font-weight: 500;
                        color: #2c3e50;
                    }
                    .file-size, .file-type {
                        color: #666;
                        text-align: center;
                    }
                    .file-type {
                        background: #e3f2fd;
                        color: #1976d2;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 0.9em;
                        font-weight: 600;
                    }
                    a { 
                        text-decoration: none;
                        color: inherit;
                        display: block;
                    }
                    a:hover .file-name {
                        color: #667eea;
                    }
                    .search-container {
                        background: rgba(255,255,255,0.95);
                        backdrop-filter: blur(10px);
                        padding: 20px;
                        border-radius: 15px;
                        margin-bottom: 20px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    }
                    .search-input {
                        width: 100%;
                        padding: 15px;
                        border: 2px solid #e0e0e0;
                        border-radius: 8px;
                        font-size: 16px;
                        outline: none;
                        transition: border-color 0.2s;
                    }
                    .search-input:focus {
                        border-color: #667eea;
                    }
                    .empty-state {
                        text-align: center;
                        padding: 60px 20px;
                        color: #666;
                    }
                    .empty-state i {
                        font-size: 64px;
                        margin-bottom: 20px;
                        display: block;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎬 Media Library</h1>
                        <p>{{ files|length }} media files available for streaming</p>
                    </div>
                    
                    <div class="search-container">
                        <input type="text" class="search-input" placeholder="🔍 Search videos by name..." onkeyup="filterFiles()">
                    </div>
                    
                    <div class="file-table">
                        <div class="table-header">
                            <div>File Name</div>
                            <div>Size</div>
                            <div>Type</div>
                        </div>
                        
                        {% if files %}
                            {% for f in files %}
                            <a href="/watch/{{ f.name | urlencode }}">
                                <div class="table-row">
                                    <div class="file-name">{{ f.name }}</div>
                                    <div class="file-size">{{ f.size }}</div>
                                    <div class="file-type">{{ f.extension }}</div>
                                </div>
                            </a>
                            {% endfor %}
                        {% else %}
                            <div class="empty-state">
                                <i>📁</i>
                                <h3>No media files found</h3>
                                <p>Upload some videos to get started</p>
                            </div>
                        {% endif %}
                    </div>
                </div>

                <script>
                    function filterFiles() {
                        const search = document.querySelector('.search-input').value.toLowerCase();
                        const tableRows = document.querySelectorAll('.table-row');
                        
                        tableRows.forEach(row => {
                            if (row.classList.contains('table-header')) return;
                            const fileName = row.querySelector('.file-name').textContent.toLowerCase();
                            if (fileName.includes(search)) {
                                row.parentElement.style.display = 'block';
                            } else {
                                row.parentElement.style.display = 'none';
                            }
                        });
                    }
                </script>
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
    """Stream video directly from S3 - FIXED VERSION"""
    internal_url = f"{VIDEO_SERVER_HOST}{video_name}"
    
    try:
        req = requests.get(internal_url, stream=True, timeout=30)
        
        # REMOVE the problematic Content-Disposition header with Unicode
        return Response(
            req.iter_content(chunk_size=8192),
            content_type=req.headers.get('Content-Type', 'video/mp4'),
            headers={
                'Cache-Control': 'no-cache',
                'Accept-Ranges': 'bytes'
            }
        )
    except Exception as e:
        return f"Error streaming video: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)