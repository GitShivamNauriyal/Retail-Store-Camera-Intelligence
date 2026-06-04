#!/bin/bash
# Script to process all CCTV video clips and pipe output to Redis stream
echo "Processing video clips..."
python pipeline/detect.py
