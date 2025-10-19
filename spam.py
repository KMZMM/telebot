"""
Safe Telegram message tester with debug prints.

- Respects:
  * GLOBAL_MAX_PER_SEC (default 30 req/sec)
  * PER_CHAT_MAX_PER_SEC (Telegram: ~1 msg/sec per chat)
- Handles 429 responses (respects retry_after).
- Shows debug prints for each attempt / response.

Requirements:
    pip install aiohttp

Usage:
    - Edit BOT_TOKEN, CHAT_ID, TOTAL_MESSAGES as needed.
    - python3 telegram_tester.py
"""
import asyncio
import aiohttp
import time
from typing import Optional, Dict, Any

BOT_TOKEN = "7590652744:AAHq1I5ihD1gjUGlmFsu0PGCRF3vkc6DNTM"  # replace if needed
CHAT_ID = "7892272656"  # replace if needed
TOTAL_MESSAGES = 100
GLOBAL_MAX_PER_SEC = 30          # do not exceed ~30 req/sec in total
PER_CHAT_MAX_PER_SEC = 1         # Telegram enforces ~1 msg/sec per chat (approx)

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_URL = API_BASE + "/sendMessage"

# Effective allowed send rate per second for this single-target script
EFFECTIVE_PER_SEC = min(GLOBAL_MAX_PER_SEC, PER_CHAT_MAX_PER_SEC)

async def send_single(session: aiohttp.ClientSession, i: int, text: str) -> Optional[Dict[str, Any]]:
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        async with session.post(SEND_URL, data=payload, timeout=10) as resp:
            status = resp.status
            # try to parse JSON safely
            try:
                j = await resp.json()
            except Exception:
                j = None
            # raw text preview for debugging (limit length)
            try:
                raw = await resp.text()
            except Exception:
                raw = ""
            print(f"[{time.strftime('%H:%M:%S')}] Sent #{i} -> status={status}; json={j}; raw_preview='{raw[:200]}'")
            return j
    except aiohttp.ClientResponseError as e:
        print(f"[{time.strftime('%H:%M:%S')}] HTTP error on #{i}: {e}")
    except asyncio.TimeoutError:
        print(f"[{time.strftime('%H:%M:%S')}] Timeout sending #{i}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Exception sending #{i}: {e}")
    return None

async def worker():
    total_sent = 0
    next_message_index = 1

    async with aiohttp.ClientSession() as session:
        try:
            while total_sent < TOTAL_MESSAGES:
                tick_start = time.time()
                # how many to send this tick (this second)
                to_send = min(int(EFFECTIVE_PER_SEC), TOTAL_MESSAGES - total_sent)
                if to_send <= 0:
                    break

                tasks = []
                for _ in range(to_send):
                    # example text — you had "Mingalabar" in your edit,
                    # include index and timestamp for debugging
                    text = f"Mingalabar #{next_message_index} (debug {time.strftime('%Y-%m-%d %H:%M:%S')})"
                    tasks.append(send_single(session, next_message_index, text))
                    next_message_index += 1

                # run the tasks concurrently for this tick
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # check if any result tells us to wait (429 retry_after)
                retry_after_seconds = None
                for r in results:
                    # r may be an exception or dict. We only handle dict responses here.
                    if isinstance(r, dict) and r is not None:
                        if not r.get("ok", True) and r.get("error_code") == 429:
                            params = r.get("parameters") or {}
                            ra = params.get("retry_after")
                            if ra is not None:
                                try:
                                    ra_int = int(ra)
                                    if retry_after_seconds is None or ra_int > retry_after_seconds:
                                        retry_after_seconds = ra_int
                                except Exception:
                                    pass

                if retry_after_seconds:
                    print(f"[{time.strftime('%H:%M:%S')}] Received 429; retry_after={retry_after_seconds}s -> sleeping.")
                    await asyncio.sleep(retry_after_seconds)
                else:
                    # no 429s, count successful attempts (best-effort: assume we attempted to_send)
                    total_sent += to_send
                    elapsed = time.time() - tick_start
                    sleep_for = max(0.0, 1.0 - elapsed)
                    print(f"[{time.strftime('%H:%M:%S')}] Tick done — sent {to_send} this second; total_sent={total_sent}/{TOTAL_MESSAGES}")
                    if sleep_for > 0:
                        await asyncio.sleep(sleep_for)

        except asyncio.CancelledError:
            print("Worker cancelled.")
        except KeyboardInterrupt:
            print("Interrupted by user.")
        finally:
            print(f"[{time.strftime('%H:%M:%S')}] Worker finished. total_sent={total_sent}")

def main():
    print("Telegram safe tester starting.")
    print(f"Bot token prefix: {BOT_TOKEN[:20]}... (hidden)   Chat ID: {CHAT_ID}")
    print(f"Total messages: {TOTAL_MESSAGES}, effective rate: {EFFECTIVE_PER_SEC} msg/sec")
    print("NOTE: Single-chat testing effectively limited to ~1 msg/sec by Telegram per-chat rules.")
    try:
        asyncio.run(worker())
    except KeyboardInterrupt:
        print("Terminated by user.")

if __name__ == "__main__":
    main()