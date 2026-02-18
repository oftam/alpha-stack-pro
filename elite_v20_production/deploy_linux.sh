#!/bin/bash
# ELITE v20 - One-Click Deployment (Linux/Mac)
# This script will install dependencies and launch the dashboard

echo "========================================"
echo " ELITE v20 - PRODUCTION DEPLOYMENT"
echo "========================================"
echo ""

echo "[1/3] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.10+"
    exit 1
fi
python3 --version

echo ""
echo "[2/3] Installing dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "[3/3] Launching ELITE v20 Dashboard..."
echo ""
echo "Dashboard will open at: http://localhost:8501"
echo ""
echo "Press CTRL+C to stop the dashboard"
echo ""

streamlit run elite_v20_dashboard.py
