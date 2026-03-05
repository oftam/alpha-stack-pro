#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 ELITE v20 - GCP Cloud Run Auto-Deployer
=========================================
מערכת אוטומציה לבנייה, העלאה ופריסה של הדשבורד המוסדי ל-Google Cloud.

Requirements:
- Docker installed and running
- gcloud CLI authenticated
- Project ID: deep-arch-451722-n0
"""

import os
import subprocess
import sys
import time
import json

# --- CONFIGURATION ---
PROJECT_ID = "deep-arch-451722-n0"
SERVICE_NAME = "elite-medallion"
REGION = "us-central1"
IMAGE_NAME = f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}:latest"
DOCKERFILE = "Dockerfile.medallion"

def run_command(command, description):
    print(f"\n[RUNNING] {description}...")
    print(f"Executing: {command}")
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end="")
        process.wait()
        if process.returncode != 0:
            print(f"\n❌ [ERROR] {description} failed.")
            return False
        print(f"✅ [SUCCESS] {description} complete.")
        return True
    except Exception as e:
        print(f"\n❌ [CRITICAL] {description} error: {e}")
        return False

def test_latency(url):
    print(f"\n[TESTING] Institutional Latency Test for: {url}")
    if not url.startswith("http"):
        url = "https://" + url

    import urllib.request
    times = []
    for i in range(5):
        try:
            start = time.time()
            urllib.request.urlopen(url, timeout=10)
            end = time.time()
            latency = (end - start) * 1000
            times.append(latency)
            print(f"  Ping {i+1}: {latency:.2f}ms")
            time.sleep(1)
        except Exception as e:
            print(f"  Ping {i+1}: FAILED ({e})")

    if times:
        avg = sum(times) / len(times)
        print(f"\n🏁 AVG Institutional Latency: {avg:.2f}ms")
        if avg < 300:
            print("🚀 PERFORMANCE: ELITE GRADE (ULTRA LOW LATENCY)")
        else:
            print("⚠️ PERFORMANCE: DEGRADED (Check GCP Region/Network)")
    else:
        print("\n❌ Latency test failed - service might still be warming up.")

def main():
    print("="*60)
    print("      ELITE v20 - GCP INSTITUTIONAL DEPLOYMENT")
    print("="*60)

    # 1. Docker Build
    if not run_command(f"docker build -t {IMAGE_NAME} -f {DOCKERFILE} .", "Docker Build"):
        sys.exit(1)

    # 2. Docker Push
    if not run_command(f"docker push {IMAGE_NAME}", "Docker Push to GCR"):
        sys.exit(1)

    # 3. GCloud Run Deploy
    # Resource allocation: 2 CPU, 4GB RAM for institutional stability
    deploy_cmd = (
        f"gcloud run deploy {SERVICE_NAME} "
        f"--image {IMAGE_NAME} "
        f"--platform managed "
        f"--region {REGION} "
        f"--memory 4Gi "
        f"--cpu 2 "
        f"--allow-unauthenticated "
        f"--project {PROJECT_ID}"
    )

    if not run_command(deploy_cmd, "GCP Cloud Run Deployment"):
        sys.exit(1)

    # 4. Get URL and Test
    print("\n[VERIFYING] Fetching service URL...")
    get_url_cmd = f"gcloud run services describe {SERVICE_NAME} --format='value(status.url)' --region {REGION} --project {PROJECT_ID}"
    try:
        url = subprocess.check_output(get_url_cmd, shell=True, text=True).strip()
        print(f"\n🌍 DEPLOYED URL: {url}")

        # Wait for service to warm up
        print("Waiting 10s for service warm-up...")
        time.sleep(10)

        # Latency Test
        test_latency(url)

    except Exception as e:
        print(f"Could not fetch URL: {e}")

    print("\n✅ DEPLOYMENT PROCESS FINISHED.")

if __name__ == "__main__":
    main()
