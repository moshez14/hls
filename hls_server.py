import subprocess
from flask import Flask, render_template, abort, jsonify
import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO

app = Flask(__name__)

HLS_ROOT = "/var/www/html/show"
BASE_URL = "http://dev.maifocus.com:8080/show/"

def get_frame_count(directory):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        command = f"/home/ubuntu/hls/frame.sh {directory}"
        frame_count = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, text=True)
        frame = frame_count.communicate()
        print(f"FRAME = {frame[0]}")
        # Append the record to the log file
        with open('frame_count_log.txt', 'a') as log_file:
            log_file.write(f"{timestamp} {directory} {frame[0]}\n")
        return frame[0]
    except subprocess.CalledProcessError:
        return "Error retrieving frame count"

def get_camera_mission_data(camera_name):
    try:
        print(f"CAMERA NAME={camera_name}")
        command = f"cat /home/ubuntu/livestream/cameras.dat | grep {camera_name} | awk '{{print $2, $3, $(NF-1)}}'"
        result = subprocess.check_output(command, shell=True)
        data = result.decode("utf-8").strip().split("\n")
        print(f"RESULT={data}")
        camera_info=[]
        command = f"/home/ubuntu/hls/frame.sh {camera_name}"
        frame_count = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, text=True)
        frame = frame_count.communicate()
        print(f"port: {data[0].split()[0]}, mission: {data[0].split()[1]}, name: {data[0].split()[2]}, frame_count: {frame[0]}")
        camera_info.append({"port": data[0].split()[0], "mission": data[0].split()[1], "name": data[0].split()[2], "frame_count": frame[0]})
        # for camera in data:
        #     command = f"/home/ubuntu/hls/frame.sh {camera[2]}"
        #     frame_count = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, text=True)
        #     frame = frame_count.communicate()
        #     camera_info.append(frame[0])  # Append frame count to camera info
        #     camera_info.append({"port": camera[0], "Mission": camera[1]})  # Append camera data
        return camera_info
    except subprocess.CalledProcessError:
        return []

def get_camera_data():
    try:
        result = subprocess.check_output("cat /home/ubuntu/livestream/cameras.dat | awk '{print $2, $3, $(NF-1)}'", shell=True)
        data = result.decode("utf-8").strip().split("\n")
        camera=[]
        camera_info = [line.split() for line in data]
        for camera in camera_info:
            command = f"/home/ubuntu/hls/frame.sh {camera[2]}"
            frame_count = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, text=True)
            frame = frame_count.communicate()
            camera.append(frame[0])  # Append frame count to camera info
            # Example additional camera data, adjust as needed
            camera.append({"port": camera[0], "Mission": camera[1]})  # Append camera data
        return camera_info
    except subprocess.CalledProcessError:
        return []


def generate_line_chart(log_data):
    # Parse the log data into a list of tuples (timestamp, camera_name, frame_count)
    parsed_data = []
    for line in log_data:
        if line.strip():
            parts = line.strip().split()
            if len(parts) == 4:
                timestamp = parts[0] + " " + parts[1]
                camera_name = parts[2]
                frame_count = int(parts[3])
                parsed_data.append((timestamp, camera_name, frame_count))

    # Convert parsed data into a DataFrame
    df = pd.DataFrame(parsed_data, columns=['Timestamp', 'Camera', 'FrameCount'])

    # Convert Timestamp column to datetime format
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    # Group by Timestamp and Camera, aggregate frame counts (assuming mean for simplicity)
    df_agg = df.groupby(['Timestamp', 'Camera']).mean().reset_index()

    # Pivot the DataFrame to get FrameCount for each camera at each timestamp
    df_pivot = df_agg.pivot(index='Timestamp', columns='Camera', values='FrameCount')

    # Plot the data
    plt.figure(figsize=(10, 6))
    for camera in df_pivot.columns:
        plt.plot(df_pivot.index, df_pivot[camera], marker='o', label=camera)

    plt.xlabel('Time')
    plt.ylabel('Frame Count')
    plt.title('Frame Count Over Time')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save plot to a BytesIO buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    # Convert image to base64 string
    base64_image = base64.b64encode(buffer.read()).decode('utf-8')

    plt.close()

    return base64_image


@app.route('/')
def index():
    directories = [d for d in os.listdir(HLS_ROOT) if os.path.isdir(os.path.join(HLS_ROOT, d))]
    camera_info = []
    for directory in directories:
        frame_count = get_frame_count(directory)
        hls_link = f"{BASE_URL}{directory}/index.m3u8"
        camera_data = get_camera_mission_data(directory)
        print(f"CAM DATA={camera_data}")
        camera_info.append({"mission": camera_data[0]['mission'], "name":camera_data[0]['name'], "frame_count": frame_count, "hls_link": hls_link, "port": camera_data[0]['port']})
        #camera_info.append(camera_data)

    camera_data = get_camera_data()
    print(f"CAMERA DATA1={camera_data} CAMERAINFO={camera_info}")
    # flat_list = [item for sublist in camera_info for item in sublist]
    # print(f"FLAT LIST={flat_list}")

    with open('frame_count_log.txt', 'r') as f:
        log_data = f.readlines()

    # Generate line chart as base64 string
    chart_data = generate_line_chart(log_data)

    return render_template('index.html', camera_info=camera_info, chart_data=chart_data)

@app.route('/frame_count/<directory>')
def frame_count(directory):
    frame_count = get_frame_count(directory)
    return jsonify({"frame_count": frame_count})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090)

