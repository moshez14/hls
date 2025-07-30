import subprocess
from flask import Flask, render_template_string, jsonify
import datetime
import re
import os

app = Flask(__name__)

CAMERAS_FILE = "/home/ubuntu/livestream/cameras.dat"

SERVICES = [
    "readDB.service",
    "MAI.service",
    "mai-front.service",
    "jpg_video_watcher.service",
    "chat.service",
    "mongod.service",
    "stream_chunker.service",
]

LOG_FILES = {
    "jpg_video_watcher": "/var/log/jpg_video_watcher.log",
    "jpg_watcher": "/var/log/jpg_watcher.log"
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Status Dashboard</title>
    <meta http-equiv="refresh" content="300">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f4; }
        table { width: 100%; border-collapse: collapse; background: white; margin-bottom: 40px; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #007bff; color: white; }
        h2 { margin-top: 40px; }
        .log-output { white-space: pre-wrap; background: #111; color: #0f0; padding: 10px; height: 300px; overflow-y: auto; font-family: monospace; }
        #search-box { margin-bottom: 10px; padding: 5px; width: 300px; }
        .collapsible { cursor: pointer; padding: 10px; background-color: #007bff; color: white; border: none; text-align: left; width: 100%; outline: none; font-size: 16px; }
        .content { display: none; overflow: hidden; background-color: #f1f1f1; padding: 10px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>Camera and Service Status</h1>
    <p><strong>Page refreshed at:</strong> {{ timestamp }}</p>

    <h2>Cameras</h2>
    <table>
        <tr>
            <th>RTMP/RTSP URL</th><th>Port</th><th>Camera Name</th><th>Mission Name</th>
            <th>Stream Name</th><th>Object IDs</th><th>Mission Status</th><th>Email</th>
            <th>RTMP Code</th><th>Mission Code</th><th>Mission ID</th><th>Frame Count</th><th>Status</th>
        </tr>
        {% for camera in cameras %}
        <tr>
            <td>{{ camera.rtmp_url }}</td><td>{{ camera.port }}</td><td>{{ camera.camera_name }}</td><td>{{ camera.mission_name }}</td>
            <td>{{ camera.stream_name }}</td><td>{{ camera.object_ids }}</td><td>{{ camera.mission_status }}</td><td>{{ camera.email }}</td>
            <td>{{ camera.rtmp_code }}</td><td>{{ camera.mission_code }}</td><td>{{ camera.mission_id }}</td><td>{{ camera.frame_count }}</td><td>{{ camera.status }}</td>
        </tr>
        {% endfor %}
    </table>

    <h2>Service Status</h2>
    <table>
        <tr><th>Service Name</th><th>Status</th><th>Active Since</th></tr>
        {% for service in services %}
        <tr><td>{{ service.name }}</td><td>{{ service.status }}</td><td>{{ service.active_since }}</td></tr>
        {% endfor %}
    </table>

    <!-- Log Panels -->
    {% for log_name, title in [
        ("systemd", "Systemd Log: jpg_video_watcher.service"),
        ("jpg_video_watcher", "File Log: /var/log/jpg_video_watcher.log"),
        ("jpg_watcher", "File Log: /var/log/jpg_watcher.log")
    ] %}
    <button class="collapsible">📄 {{ title }}</button>
    <div class="content">
        <input type="text" class="search-box" data-log="{{ log_name }}" placeholder="Search logs...">
        <div id="log-{{ log_name }}" class="log-output">Loading log...</div>
    </div>
    {% endfor %}

    <script>
        const logTargets = ["systemd", "jpg_video_watcher", "jpg_watcher"];

        document.querySelectorAll(".collapsible").forEach(button => {
            button.addEventListener("click", () => {
                const content = button.nextElementSibling;
                content.style.display = content.style.display === "block" ? "none" : "block";
            });
        });

        async function fetchLog(name) {
            try {
                const res = await fetch(`/log/${name}`);
                const data = await res.json();
                const searchBox = document.querySelector(`.search-box[data-log='${name}']`);
                const filter = searchBox.value.toLowerCase();
                const lines = data.log.split("\\n").filter(l => l.toLowerCase().includes(filter)).join("\\n");
                document.getElementById("log-" + name).textContent = lines;
            } catch {
                document.getElementById("log-" + name).textContent = "Error loading log.";
            }
        }

        function updateAllLogs() {
            for (const name of logTargets) fetchLog(name);
        }

        updateAllLogs();
        setInterval(updateAllLogs, 10000);

        document.querySelectorAll(".search-box").forEach(input => {
            input.addEventListener("input", () => {
                const name = input.dataset.log;
                fetchLog(name);
            });
        });
    </script>
</body>
</html>
"""

def parse_cameras():
    cameras = []
    try:
        with open(CAMERAS_FILE, "r") as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) < 14:
                    continue
                cameras.append({
                    "rtmp_url": parts[0],
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
                })
    except FileNotFoundError:
        pass
    return cameras

def get_frame_count(mission_id, rtmp_code):
    try:
        result = subprocess.run(
            ["/home/ubuntu/hls/frame.sh", mission_id, rtmp_code],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return "Err"

def get_service_status(service_name):
    try:
        result = subprocess.run(["systemctl", "status", service_name], capture_output=True, text=True)
        output = result.stdout
        active_line = next((line.strip() for line in output.splitlines() if line.strip().startswith("Active:")), None)

        status = "Unknown"
        active_since = "Unknown"
        if active_line:
            status_match = re.search(r"Active:\s+(\w+)", active_line)
            since_match = re.search(r"since\s+(.+?);", active_line)
            if status_match: status = status_match.group(1)
            if since_match: active_since = since_match.group(1)
        return {"name": service_name, "status": status, "active_since": active_since}
    except Exception:
        return {"name": service_name, "status": "Error", "active_since": "N/A"}

@app.route("/")
def index():
    cameras = parse_cameras()
    services = [get_service_status(s) for s in SERVICES]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template_string(HTML_TEMPLATE, cameras=cameras, services=services, timestamp=timestamp)

@app.route("/log/<name>")
def log(name):
    if name == "systemd":
        try:
            result = subprocess.run(
                ["journalctl", "-u", "jpg_video_watcher", "-n", "150", "--no-pager"],
                capture_output=True, text=True, check=True
            )
            return jsonify({"log": result.stdout})
        except subprocess.CalledProcessError as e:
            return jsonify({"log": f"Error: {str(e)}"})
    elif name in LOG_FILES:
        try:
            if os.path.exists(LOG_FILES[name]):
                with open(LOG_FILES[name], "r") as f:
                    lines = f.readlines()[-100:]
                    return jsonify({"log": "".join(lines)})
            else:
                return jsonify({"log": f"{LOG_FILES[name]} not found"})
        except Exception as e:
            return jsonify({"log": f"Error reading file: {str(e)}"})
    else:
        return jsonify({"log": "Invalid log name"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)

