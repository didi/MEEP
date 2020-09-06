#!/usr/bin/env bash

# Config arguments will be picked up from (in order of preference):
# 1. Command line arguments: (./run.sh 1234). This is for backward compatibility
# 2. Environment variables: (SERVER_PORT=1234 PORT=3456 ./run.sh)
# 3. .env file
# 4. .env.example file (will be copied into .env.example if using this script)

if [[ "$#" -ge 1 ]]; then
    export SERVER_PORT=$1
fi

if [[ "$#" -ge 2 ]]; then
    export PORT=$2
fi

cp -n /home/shared/keys/destination_dialog.env .env 2> /dev/null # convenience thing for people on a shared machine: copy the env from a shared location
cp -n .env.example .env # create env iff it doesn't exist

npm start
