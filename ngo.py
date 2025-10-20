import os
import time

# --- Configuration ---
input_url = "https://aly.fbcdntv247.cfd/memfs/5cd05983-0661-4da6-98ff-b31f6e411620_output_0.m3u8"
output_url = "rtmps://dc5-1.rtmp.t.me/s/2837937081:iyZxR5B2iuwYQ_JvJfcVgw"

# Desired output resolution (16:9) for Telegram
output_width = 1280
output_height = 720

# --- Streaming Loop ---
while True:
    print("🔴 Starting Telegram stream...")
    
    # FFmpeg command with scaling and padding for full screen
    cmd = (
        f'ffmpeg -re -i "{input_url}" '
        f'-vf "scale={output_width}:{output_height}:force_original_aspect_ratio=decrease,'
        f'pad={output_width}:{output_height}:(ow-iw)/2:(oh-ih)/2" '
        '-c:v libx264 -preset veryfast -c:a aac -b:a 128k -f flv '
        f'"{output_url}"'
    )
    
    os.system(cmd)
    
    print("⚠️ Stream stopped. Reconnecting in 10 seconds...")
    time.sleep(10)