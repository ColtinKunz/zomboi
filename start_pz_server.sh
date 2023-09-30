#!/bin/bash

# Check if there is at least one argument passed
if [ "$#" -ne 1 ]; then
    echo "You need to specify the command to start the server as an argument."
    exit 1
fi

SERVER_START_COMMAND="$1"

pkill -f ProjectZomboid6

# Wait for a few seconds to ensure the process is completely stopped
sleep 5

# Start the server again
$SERVER_START_COMMAND

echo "Server started successfully."
