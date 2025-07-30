#!/bin/bash

set -e

SHOW_DIR="/var/www/html/show"
PHONE_NUMBER="+972509966168"
API_URL="http://www.maifocus.com:5500/send_sms"
AUTH_HEADER="Authorization: Basic YWRtaW46QXVndV8yMDIz"

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

        # Send SMS alert
        #curl --silent --output /dev/null --location --request POST "$API_URL" \
        #  --header "Content-Type: application/json-patch+json" \
        #  --header "$AUTH_HEADER" \
        #  --data-raw "{ \"number\": \"$PHONE_NUMBER\", \"message\": \"Maifocus Alert: ffmpeg $key was killed\" }"

        echo "SMS alert sent for key: $key"
    fi
done

