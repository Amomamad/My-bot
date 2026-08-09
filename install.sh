#!/bin/bash

echo "=== Updating system and installing prerequisites ==="
apt update && apt install -y python3-pip python3-venv python3-full

echo "=== Creating virtual environment (venv) ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Installing Python libraries ==="
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install python-telegram-bot requests python-dotenv
fi

echo "=== Setting up .env configuration file ==="
if [ ! -f ".env" ]; then
    read -p "Please enter your Bot Token (BOT_TOKEN): " BOT_TOKEN
    read -p "Please enter your Admin ID (ADMIN_ID): " ADMIN_ID
    
    echo "BOT_TOKEN=$BOT_TOKEN" > .env
    echo "ADMIN_ID=$ADMIN_ID" >> .env
    echo ".env file created successfully."
else
    echo ".env file already exists, skipping..."
fi

echo "=== Everything is ready! Starting the bot... ==="
source venv/bin/activate
python3 main.py

