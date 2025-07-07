import subprocess
from flask import Flask, render_template_string
import datetime
import re

app = Flask(__name__)

CAMERAS_FILE = "/home/ubuntu/livestream/cameras.dat"

# Services to check status for
SERVICES = [
    "readDB.service",
    "MAI.service",
    "mai-front.service",
    "jpg_watcher.service",
    "inotify.service",
    "chat.service",
    "mongod.service",
    "stream_chunker.service",
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Camera and Service Status</title>
    <meta http-equiv="refresh" content="10">  <!-- Auto refresh every 10 seconds -->
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f4; }
        table { width: 100%; border-collapse: collapse; background: white; margin-bottom: 40px; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #007bff; color: white; }
        h2 { margin-top: 40px; }
    </style>
</head>
<body>
    <h1>Camera Data</h1>
    <p><strong>Page refreshed at:</strong> {{ timestamp }}</p>
    <table>
        <tr>
            <th>RTMP/RTSP URL</th>
            <th>Port</th>
            <th>Camera Name</th>
            <th>Mission Name</th>
            <th>Stream Name</th>
            <th>Object IDs</th>
            <th>Mission Status</th>
            <th>Email</th>
            <th>RTMP Code</th>
            <th>Mission Code</th>
            <th>Mission ID</th>
            <th>Frame Count</th>
            <th>Status</th>
        </tr>
        {% for camera in cameras %}
        <tr>
            <td>{{ camera.rtmp_url }}</td>
            <td>{{ camera.port }}</td>
            <td>{{ camera.camera_name }}</td>
            <td>{{ camera.mission_name }}</td>
            <td>{{ camera.stream_name }}</td>
            <td>{{ camera.object_ids }}</td>
            <td>{{ camera.mission_status }}</td>
            <td>{{ camera.email }}</td>
            <td>{{ camera.rtmp_code }}</td>
            <td>{{ camera.mission_code }}</td>
            <td>{{ camera.mission_id }}</td>
            <td>{{ camera.frame_count }}</td>
            <td>{{ camera.status }}</td>
        </tr>
        {% endfor %}
    </table>

    <h2>Service Status</h2>
    <table>
        <tr>
            <th>Service Name</th>
            <th>Status</th>
            <th>Active Since</th>
        </tr>
        {% for service in services %}
        <tr>
            <td>{{ service.name }}</td>
            <td>{{ service.status }}</td>
            <td>{{ service.active_since }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

def parse_cameras():
    cameras = []
    try:
        with open(CAMERAS_FILE, "r") as file:
            lines = file.readlines()

        for line in lines:
            parts = line.strip().split()
            if len(parts) < 14:
                continue  # Skip invalid lines

            # Detect whether it's an RTSP or RTMP line
            url = parts[0]
            is_rtsp = url.startswith("rtsp://")

            camera = {
                "rtmp_url": url,
                "port": parts[1],
                "camera_name": parts[2],
                "mission_name": parts[3],
                "stream_name": parts[4],
                "object_ids": parts[6],
                "mission_status": parts[8],
                "email": parts[10],
                "rtmp_code": parts[-2],
                "mission_code": parts[13],
                "mission_id": parts[-1],
                "frame_count": get_frame_count(parts[-1], parts[-2]),
                "status": "Running"
            }
            cameras.append(camera)

    except FileNotFoundError:
        print(f"Error: {CAMERAS_FILE} not found.")
    return cameras

def get_frame_count(mission_id, rtmp_code):
    try:
        command = f"/home/ubuntu/hls/frame.sh {mission_id} {rtmp_code}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def get_service_status(service_name):
    try:
        result = subprocess.run(["systemctl", "status", service_name], capture_output=True, text=True)
        output = result.stdout

        active_line = None
        for line in output.splitlines():
            if line.strip().startswith("Active:"):
                active_line = line.strip()
                break

        status = "Unknown"
        active_since = "Unknown"
        if active_line:
            status_match = re.search(r"Active:\s+(\w+)", active_line)
            since_match = re.search(r"since\s+(.+?);", active_line)
            if status_match:
                status = status_match.group(1)
            if since_match:
                active_since = since_match.group(1)

        return {
            "name": service_name,
            "status": status,
            "active_since": active_since
        }

    except Exception as e:
        return {
            "name": service_name,
            "status": f"Error: {str(e)}",
            "active_since": "N/A"
        }

@app.route("/")
def index():
    cameras = parse_cameras()
    services = [get_service_status(s) for s in SERVICES]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template_string(HTML_TEMPLATE, cameras=cameras, services=services, timestamp=timestamp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)

