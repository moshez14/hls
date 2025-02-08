#!/bin/bash
CAMERA=$1
MISSION_ID=$2
LOG_FILE="/home/ubuntu/hls/frame_count_log.txt"

# Function to extract the number from the string
# Execute tail command to monitor syslog and grep for the string pattern
number=$(tail -4500 /var/log/syslog | grep "$CAMERA" | grep "$MISSION_ID" | grep "FRAME COUNT=[0-9]\{1,\}" | tail -1 | awk 'BEGIN { FS="=" } { print $3 }')
#sed -i '1,5d' $LOG_FILE

# Get the current timestamp
timestamp=$(date "+%Y-%m-%d %H:%M:%S")

# Check if number is less than 10 or does not exist
if [ -z "$number" ] ; then
    echo "-1"
    # Write to log file with timestamp
#    echo "$timestamp CAMERA_ID=$CAMERA -1" >> $LOG_FILE
    exit 1
fi

if [ "$number" -lt 150 ]; then
    echo "$number"
    # Write to log file with timestamp
#    echo "$timestamp CAMERA_ID=$CAMERA $number" >> $LOG_FILE
    exit 1  # Return false
else
    echo "$number"
    # Write to log file with timestamp
#    echo "$timestamp CAMERA_ID=$CAMERA $number" >> $LOG_FILE
    exit 0  # Return true
fi

