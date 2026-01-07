#!/bin/bash
set -x
set -e

SHOW_DIR="/var/www/html/show"
PHONE_NUMBER="+972509966168"
API_URL="http://dev.maifocus.com:5500/send_sms"
AUTH_HEADER="Authorization: Basic YWRtaW46QXVndV8yMDIz"
CAMERA_FILE="/home/ubuntu/livestream/cameras.json"

echo "Checking ffmpeg stream folders under: $SHOW_DIR"

# Extract stream keys from RTMP URLs in ffmpeg processes
STREAM_KEYS=$(ps -ef | grep ffmpeg | grep -v grep | grep -oE 'rtmp://[^ ]+/[^ ]+' | awk -F/ '{print $NF}' | sort | uniq)

for key in $STREAM_KEYS; do
    folder="$SHOW_DIR/$key"

    if [ -d "$folder" ]; then
        echo "[OK] Folder exists for key: $key"
    else
        echo "[ALERT] No folder found for key: $key — killing related ffmpeg processes and sending SMS"

        # Get all matching ffmpeg process PIDs
        PIDS=$(ps -ef | grep ffmpeg | grep "$key" | grep -v grep | awk '{print $2}')

        for pid in $PIDS; do
            echo "Killing ffmpeg PID: $pid for key: $key"
            sudo kill -9 "$pid"
        done
        CAMERA_DATA=$(jq -r ".[] | select(.rtmpCode == \"$key\") | \"\(.mission_ids),\(.camera_id)\"" "$CAMERA_FILE")

        if [ -n "$CAMERA_DATA" ]; then
                MISSION_ID=$(echo "$CAMERA_DATA" | cut -d',' -f1)
                CAMERA_ID=$(echo "$CAMERA_DATA" | cut -d',' -f2)

                if [ -n "$MISSION_ID" ] && [ -n "$CAMERA_ID" ]; then
                        curl --silent --location --request POST "http://localhost:5500/api/system_messagelog" \
                        --header "Content-Type: application/json-patch+json" \
                        --header "$AUTH_HEADER" \
                        --data-raw "{ \"mission_id\": \"$MISSION_ID\", \"camera_id\": \"$CAMERA_ID\", \"source\": \"check_ffmpeg\", \"message\": \"ffmpeg process for $key was killed\" }"
                else
                        echo "[WARN] Missing mission_id or camera_id for key: $key"
                fi
        else
                echo "[WARN] No camera data found for key: $key — skipping system log"
        fi

        CAMERA_DATA=$(jq -r ".[] | select(.rtmpCode == \"$key\") | \"\(.mission_ids),\(.camera_id)\"" "$CAMERA_FILE")
        MISSION_ID=$(echo "$CAMERA_DATA" | cut -d',' -f1)
        CAMERA_ID=$(echo "$CAMERA_DATA" | cut -d',' -f2)
    fi
done
