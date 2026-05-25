import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

DEV_URL = os.getenv("DEV_URL")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    page.goto(DEV_URL, wait_until="networkidle")

    print("\nPAGE TITLE:")
    print(page.title())

    print("\nCURRENT URL:")
    print(page.url)

    print("\nALL LINKS:")

    links = page.locator("a").all()

    for i, link in enumerate(links):
        try:
            print(f"\nLINK #{i}")

            print("TEXT:", link.inner_text())

            print("HREF:", link.get_attribute("href"))

        except:
            pass

    print("\nALL BUTTONS:")

    buttons = page.locator("button").all()

    for i, btn in enumerate(buttons):
        try:
            print(f"\nBUTTON #{i}")

            print("TEXT:", btn.inner_text())

        except:
            pass

    page.screenshot(path="page_inspection.png", full_page=True)

    input("\nPress Enter to close browser...")

    browser.close()