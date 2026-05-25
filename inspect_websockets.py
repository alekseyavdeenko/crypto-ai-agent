import os
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

DEV_URL = os.getenv("DEV_URL")
LOGIN_URL = os.getenv("LOGIN_URL")
QA_EMAIL = os.getenv("QA_EMAIL")
QA_PASSWORD = os.getenv("QA_PASSWORD")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        ws_messages = []

        def on_websocket(ws):
            print("\nWS CONNECTED:")
            print(ws.url)

            ws.on("framereceived", lambda frame: handle_frame(frame, ws_messages))

        def handle_frame(frame, ws_messages):
            payload = frame

            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="ignore")

            ws_messages.append(payload)

            print("\nWS FRAME RECEIVED:")
            print(payload[:1000])

        page.on("websocket", on_websocket)

        page.goto(LOGIN_URL, wait_until="networkidle")

        page.fill("input[type='email']", QA_EMAIL)
        page.fill("input[type='password']", QA_PASSWORD)
        page.click("button[type='submit']")

        page.wait_for_timeout(5000)

        print("After login URL:", page.url)

        page.goto(f"{DEV_URL}/platform/spot", wait_until="networkidle")

        print("Spot page URL:", page.url)

        print("\nListening WebSocket messages for 60 seconds...")

        time.sleep(60)

        print("\nTOTAL WS MESSAGES:", len(ws_messages))

        page.screenshot(path="ws_inspection.png", full_page=True)

        input("\nPress Enter to close browser...")
        browser.close()


if __name__ == "__main__":
    main()