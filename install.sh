#!/bin/bash

echo "=== Checking and installing system prerequisites ==="
apt update && apt install -y python3-pip python3-venv python3.12-venv

echo "=== Creating virtual environment (venv) ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Installing Python libraries ==="
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    echo "=== Setting up .env configuration file ==="
    read -p "Please enter your Bot Token (BOT_TOKEN): " b_token
    read -p "Please enter your Admin ID (ADMIN_ID): " a_id
    
    echo "BOT_TOKEN=$b_token" > .env
    echo "ADMIN_ID=$a_id" >> .env
    echo ".env file created successfully."
fi

echo "=== Everything is ready! Starting the bot... ==="
python3 main.py
