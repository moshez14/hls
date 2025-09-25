import datetime
import json
import os
import re
import subprocess
import requests
from urllib.parse import quote

from flask import Flask, jsonify, render_template

app = Flask(__name__)

CAMERAS_FILE = "/home/ubuntu/livestream/cameras.json"

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

def parse_cameras():
    cameras = []
    try:
        with open(CAMERAS_FILE, "r") as file:
            cameras_list = json.load(file)
            for camera in cameras_list:
                frame_count = get_frame_count(camera["mission_ids"], camera["rtmpCode"])
                print(frame_count)
                cameras.append({
                    "rtmp_url": camera["streamUrl"],
                    "port": camera["port"],
                    "camera_name": camera["camera_name"],
                    "mission_name": camera["name1"],
                    "stream_name": f"livestream{camera['livestream_port']}",
                    "object_ids": camera["object_ids"],
                    "mission_status": camera["mission_status"],
                    "email": camera["email"],
                    "rtmp_code": camera["rtmpCode"],
                    "mission_code": camera["rtmpCode"],
                    "mission_id": camera["mission_ids"],
                    "frame_count": get_frame_count(camera["mission_ids"], camera["rtmpCode"]),
                    "status": "Warning" if frame_count == "Err" or int(frame_count) < 1 else "Running"
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

def get_system_message_logs():
    url = f"http://localhost:5500/api/system_messagelog"
    payload = ""
    headers = {
        'Content-Type': 'application/json-patch+json',
        'Authorization': 'Basic YWRtaW46QXVndV8yMDIz'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    return json.loads(response.text)["messages"]

@app.route("/")
def index():
    cameras = parse_cameras()
    services = [get_service_status(s) for s in SERVICES]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_message_logs = get_system_message_logs()
    return render_template("index.html", cameras=cameras, services=services, timestamp=timestamp, system_message_logs=system_message_logs)

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


@app.route("/api/system_messagelog/<message_id>", methods=["DELETE"])
def delete_system_message(message_id):
    try:
        url = f"http://localhost:5500/api/system_messagelog/{quote(message_id)}"
        headers = {
            'Content-Type': 'application/json-patch+json',
            'Authorization': 'Basic YWRtaW46QXVndV8yMDIz'
        }
        response = requests.delete(url, headers=headers)

        if response.status_code == 200:
            return jsonify({"success": True, "message": "Message deleted successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to delete message"}), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)

