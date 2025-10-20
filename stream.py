import os
import time

input_url = "https://tv.mahar.live/esports/mahar.stream/esports/mahar2/chunks.m3u8"
output_url = "rtmps://dc5-1.rtmp.t.me/s/2065711576:U7L8KKAk7myy49oVRXuhww"  # ✅ correct format

while True:
    print("🔴 Starting Telegram stream...")
    os.system(f'ffmpeg -re -i "{input_url}" -c:v copy -c:a copy -f flv "{output_url}"')
    print("⚠️ Stream stopped. Reconnecting in 10 seconds...")
    time.sleep(10)