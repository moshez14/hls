import subprocess
from flask import Flask, render_template_string

app = Flask(__name__)

CAMERAS_FILE = "/home/ubuntu/livestream/cameras.dat"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Camera Data</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f4; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #007bff; color: white; }
    </style>
</head>
<body>
    <h1>Camera Data</h1>
    <table>
        <tr>
            <th>RTMP URL</th>
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
            print(f"{parts}")
            if len(parts) < 11:
                continue  # Skip invalid lines

            camera = {
                "rtmp_url": parts[0],
                "port": parts[1],
                "camera_name": parts[2],
                "mission_name": parts[3],
                "stream_name": parts[4],
                "object_ids": parts[6],  # Assuming list format needs parsing
                "mission_status": parts[8],
                "email": parts[10],
                "rtmp_code": parts[-2],
                "mission_code": parts[13],
                "mission_id": parts[-1],  # Using mission_code as mission_id
                "frame_count": get_frame_count(parts[-2], parts[-1])
            }
            cameras.append(camera)

    except FileNotFoundError:
        print(f"Error: {CAMERAS_FILE} not found.")
    return cameras

def get_frame_count(camera, mission_id):
    try:
        print(f"{camera}, {mission_id}")
        command = f"/home/ubuntu/hls/frame.sh {camera} {mission_id}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/")
def index():
    cameras = parse_cameras()
    return render_template_string(HTML_TEMPLATE, cameras=cameras)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)

