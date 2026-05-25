import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

DEV_URL = os.getenv("DEV_URL")
LOGIN_URL = os.getenv("LOGIN_URL")
QA_EMAIL = os.getenv("QA_EMAIL")
QA_PASSWORD = os.getenv("QA_PASSWORD")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto(LOGIN_URL, wait_until="networkidle")

    page.fill("input[type='email']", QA_EMAIL)
    page.fill("input[type='password']", QA_PASSWORD)
    page.click("button[type='submit']")

    page.wait_for_timeout(5000)

    print("After login URL:", page.url)

    page.goto(f"{DEV_URL}/platform/home", wait_until="networkidle")

    print("\nCURRENT URL:")
    print(page.url)

    print("\nLINKS:")
    links = page.locator("a").all()

    for i, link in enumerate(links):
        try:
            text = link.inner_text()
            href = link.get_attribute("href")

            if text or href:
                print(f"{i}: TEXT='{text}' HREF='{href}'")
        except:
            pass

    print("\nBUTTONS:")
    buttons = page.locator("button").all()

    for i, btn in enumerate(buttons):
        try:
            text = btn.inner_text()

            if text:
                print(f"{i}: TEXT='{text}'")
        except:
            pass

    page.screenshot(path="after_login_home.png", full_page=True)

    input("\nPress Enter to close browser...")
    browser.close()