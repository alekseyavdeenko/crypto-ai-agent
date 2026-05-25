import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

DEV_URL = os.getenv("DEV_URL")
LOGIN_URL = os.getenv("LOGIN_URL")

QA_EMAIL = os.getenv("QA_EMAIL")
QA_PASSWORD = os.getenv("QA_PASSWORD")

HEADLESS = os.getenv(
    "HEADLESS",
    "true"
).lower() == "true"

LISTEN_SECONDS = int(
    os.getenv("LISTEN_SECONDS", "60")
)

RETRY_LISTEN_SECONDS = int(
    os.getenv("RETRY_LISTEN_SECONDS", "30")
)

MIN_TRACKED_PAIRS_WITH_UPDATES = int(
    os.getenv(
        "MIN_TRACKED_PAIRS_WITH_UPDATES",
        "2"
    )
)

TARGET_SYMBOLS = [
    symbol.strip()
    for symbol in os.getenv(
        "TARGET_SYMBOLS",
        "BTC/USDT,ETH/USDT"
    ).split(",")
]

TARGET_WS_EVENT = (
    "trading-pair-price-receive-lastprice"
)

REPORTS_DIR = "reports"


def log(message=""):

    now = datetime.now().strftime("%H:%M:%S")

    print(f"[{now}] {message}")


def format_price(price):

    try:
        return format(float(price), ".8f")

    except (ValueError, TypeError):
        return str(price)


def parse_json_frames(payload):

    payload = payload.strip()

    if not payload:
        return []

    frames = []

    try:
        frames.append(json.loads(payload))
        return frames

    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()

    index = 0

    while index < len(payload):

        try:
            obj, end = decoder.raw_decode(
                payload[index:]
            )

            frames.append(obj)

            index += end

        except json.JSONDecodeError:
            break

    return frames


def create_report_file(result):

    Path(REPORTS_DIR).mkdir(
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    report_path = (
        f"{REPORTS_DIR}/"
        f"spot_ws_report_{timestamp}.txt"
    )

    lines = []

    lines.append(
        "===== SPOT WEBSOCKET "
        "MARKET DATA REPORT ====="
    )

    lines.append("")

    lines.append(
        f"Run time: "
        f"{datetime.now().isoformat()}"
    )

    lines.append(
        f"Status: {result.get('status')}"
    )

    lines.append(
        f"Environment: {DEV_URL}"
    )

    lines.append("")

    lines.append("Tracked pairs:")

    for symbol in result.get(
        "tracked_pairs",
        []
    ):

        lines.append(f"- {symbol}")

    lines.append("")

    lines.append(
        f"Total WS connections: "
        f"{result.get('total_ws_connections')}"
    )

    lines.append(
        f"Total market events: "
        f"{result.get('total_market_updates')}"
    )

    lines.append(
        f"Tracked pairs with updates: "
        f"{result.get('tracked_pairs_with_updates')}/"
        f"{len(result.get('tracked_pairs', []))}"
    )

    lines.append("")
    lines.append("Pair details:")

    pair_summary = result.get(
        "pair_summary",
        {}
    )

    for symbol, data in pair_summary.items():

        lines.append("")
        lines.append(symbol)

        lines.append(
            f"updates received: "
            f"{data.get('updates_received')}"
        )

        lines.append(
            f"first price: "
            f"{data.get('first_price')}"
        )

        lines.append(
            f"last price: "
            f"{data.get('last_price')}"
        )

        lines.append(
            f"unique prices: "
            f"{data.get('unique_prices')}"
        )

        lines.append(
            f"unique price values: "
            f"{data.get('unique_price_values')}"
        )

    lines.append("")
    lines.append("Warnings:")

    warnings = result.get(
        "warnings",
        []
    )

    if warnings:

        for warning in warnings:
            lines.append(f"- {warning}")

    else:
        lines.append("No warnings")

    lines.append("")
    lines.append("Console errors:")

    console_errors = result.get(
        "console_errors",
        []
    )

    if console_errors:

        for error in console_errors:
            lines.append(f"- {error}")

    else:
        lines.append("No console errors")

    if result.get("error"):

        lines.append("")
        lines.append("Error:")

        lines.append(
            result.get("error")
        )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write("\n".join(lines))

    return report_path


def run_test():

    ws_connections = []

    console_errors = []

    warnings = []

    pair_updates = defaultdict(list)

    total_market_updates = 0

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=HEADLESS
        )

        page = browser.new_page()

        def handle_ws_frame(frame):

            nonlocal total_market_updates

            payload = frame

            if isinstance(payload, bytes):

                payload = payload.decode(
                    "utf-8",
                    errors="ignore"
                )

            parsed_frames = parse_json_frames(
                payload
            )

            for data in parsed_frames:

                target = data.get("target")

                if (
                    target
                    != TARGET_WS_EVENT
                ):
                    continue

                args = data.get(
                    "arguments",
                    []
                )

                if not args:
                    continue

                update = args[0]

                symbol = update.get(
                    "symbol"
                )

                price = update.get(
                    "price"
                )

                if not symbol:
                    continue

                total_market_updates += 1

                pair_updates[symbol].append(
                    price
                )

        def handle_websocket(ws):

            ws_connections.append(
                ws.url
            )

            log(
                f"WS CONNECTED: "
                f"{ws.url}"
            )

            ws.on(
                "framereceived",
                handle_ws_frame
            )

        page.on(
            "websocket",
            handle_websocket
        )

        page.on(
            "console",
            lambda msg:
            console_errors.append(
                msg.text
            )
            if msg.type == "error"
            else None
        )

        try:

            log("OPEN LOGIN PAGE")

            page.goto(
                LOGIN_URL,
                wait_until="networkidle"
            )

            log("FILL EMAIL")

            page.fill(
                "input[type='email']",
                QA_EMAIL
            )

            log("FILL PASSWORD")

            page.fill(
                "input[type='password']",
                QA_PASSWORD
            )

            log("CLICK LOGIN")

            page.click(
                "button[type='submit']"
            )

            page.wait_for_timeout(5000)

            log(
                f"LOGIN SUCCESS: "
                f"{page.url}"
            )

            log("OPEN SPOT PAGE")

            page.goto(
                f"{DEV_URL}/platform/spot",
                wait_until="networkidle"
            )

            page.wait_for_timeout(5000)

            log(
                f"SPOT PAGE OPENED: "
                f"{page.url}"
            )

            log("")
            log("TRACKED PAIRS:")

            for symbol in TARGET_SYMBOLS:
                log(f"- {symbol}")

            log("")

            log(
                f"LISTENING WS UPDATES "
                f"FOR {LISTEN_SECONDS} "
                f"SECONDS..."
            )

            time.sleep(LISTEN_SECONDS)

            log("")
            log(
                "===== MARKET DATA "
                "SUMMARY ====="
            )

            log("")

            tracked_pairs_with_updates = 0

            pair_summary = {}

            for symbol in TARGET_SYMBOLS:

                updates = pair_updates[symbol]

                updates_count = len(updates)

                log(symbol)

                log(
                    f"updates received: "
                    f"{updates_count}"
                )

                pair_summary[symbol] = {
                    "updates_received":
                    updates_count,

                    "first_price":
                    None,

                    "last_price":
                    None,

                    "unique_prices":
                    0,

                    "unique_price_values":
                    []
                }

                if updates_count > 0:

                    tracked_pairs_with_updates += 1

                    first_price = format_price(
                        updates[0]
                    )

                    last_price = format_price(
                        updates[-1]
                    )

                    log(
                        f"first price: "
                        f"{first_price}"
                    )

                    log(
                        f"last price: "
                        f"{last_price}"
                    )

                    price_counts = {}

                    for price in updates:

                        if (
                            price
                            not in price_counts
                        ):

                            price_counts[
                                price
                            ] = 0

                        price_counts[
                            price
                        ] += 1

                    unique_prices = len(
                        price_counts
                    )

                    formatted_prices = (
                        ", ".join(
                            [
                                f"{format_price(price)} "
                                f"x{count}"

                                for price, count
                                in sorted(
                                    price_counts.items()
                                )
                            ]
                        )
                    )

                    log(
                        f"unique prices: "
                        f"{unique_prices} | "
                        f"values: "
                        f"[{formatted_prices}]"
                    )

                    pair_summary[symbol] = {

                        "updates_received":
                        updates_count,

                        "first_price":
                        first_price,

                        "last_price":
                        last_price,

                        "unique_prices":
                        unique_prices,

                        "unique_price_values":
                        formatted_prices
                    }

                    if unique_prices == 1:

                        warning = (
                            f"{symbol}: "
                            f"price updates "
                            f"received, but "
                            f"price value "
                            f"did not change"
                        )

                        warnings.append(
                            warning
                        )

                        log(
                            f"WARNING: "
                            f"{warning}"
                        )

                else:

                    log(
                        f"NO UPDATES FOR "
                        f"{symbol}"
                    )

                    log(
                        f"RETRY LISTENING "
                        f"FOR "
                        f"{RETRY_LISTEN_SECONDS} "
                        f"SECONDS..."
                    )

                    retry_start_count = len(
                        pair_updates[symbol]
                    )

                    time.sleep(
                        RETRY_LISTEN_SECONDS
                    )

                    retry_end_count = len(
                        pair_updates[symbol]
                    )

                    retry_new_updates = (
                        retry_end_count
                        - retry_start_count
                    )

                    if retry_new_updates > 0:

                        tracked_pairs_with_updates += 1

                        recovered_updates = (
                            pair_updates[symbol]
                        )

                        warning = (
                            f"{symbol}: "
                            f"no updates "
                            f"during initial "
                            f"run, but "
                            f"recovered "
                            f"after retry "
                            f"(+"
                            f"{retry_new_updates} "
                            f"updates)"
                        )

                        warnings.append(
                            warning
                        )

                        log(
                            f"RECOVERED "
                            f"AFTER RETRY: "
                            f"{symbol}"
                        )

                        log(
                            f"NEW UPDATES "
                            f"AFTER RETRY: "
                            f"{retry_new_updates}"
                        )

                        first_price = format_price(
                            recovered_updates[0]
                        )

                        last_price = format_price(
                            recovered_updates[-1]
                        )

                        log(
                            f"first price: "
                            f"{first_price}"
                        )

                        log(
                            f"last price: "
                            f"{last_price}"
                        )

                    else:

                        warning = (
                            f"{symbol}: "
                            f"still no updates "
                            f"after retry "
                            f"("
                            f"{RETRY_LISTEN_SECONDS}s)"
                        )

                        warnings.append(
                            warning
                        )

                        log(
                            f"PERSISTENT "
                            f"WARNING: "
                            f"{warning}"
                        )

                log("")

            log(
                f"TRACKED PAIRS "
                f"WITH UPDATES: "
                f"{tracked_pairs_with_updates}/"
                f"{len(TARGET_SYMBOLS)}"
            )

            log(
                f"TOTAL WS "
                f"CONNECTIONS: "
                f"{len(ws_connections)}"
            )

            log(
                f"TOTAL MARKET "
                f"EVENTS: "
                f"{total_market_updates}"
            )

            log("")

            if console_errors:

                log("CONSOLE ERRORS:")

                for error in console_errors:
                    log(error)

                log("")

            if warnings:

                log("WARNINGS:")

                for warning in warnings:
                    log(f"- {warning}")

                log("")

            assert len(
                ws_connections
            ) > 0, (
                "No WebSocket "
                "connections established"
            )

            assert total_market_updates > 0, (
                "No market updates "
                "received at all"
            )

            assert (
                tracked_pairs_with_updates
                >=
                MIN_TRACKED_PAIRS_WITH_UPDATES
            ), (
                f"Only "
                f"{tracked_pairs_with_updates}/"
                f"{len(TARGET_SYMBOLS)} "
                f"tracked pairs "
                f"received updates. "
                f"Expected at least "
                f"{MIN_TRACKED_PAIRS_WITH_UPDATES}."
            )

            if warnings:

                log(
                    "TEST PASSED "
                    "WITH WARNINGS"
                )

                status = (
                    "passed_with_warnings"
                )

            else:

                log("TEST PASSED")

                status = "passed"

            page.screenshot(
                path="spot_ws_success.png",
                full_page=True
            )

            result = {

                "status":
                status,

                "tracked_pairs":
                TARGET_SYMBOLS,

                "tracked_pairs_with_updates":
                tracked_pairs_with_updates,

                "total_ws_connections":
                len(ws_connections),

                "total_market_updates":
                total_market_updates,

                "pair_summary":
                pair_summary,

                "warnings":
                warnings,

                "console_errors":
                console_errors,

                "error":
                None
            }

            report_path = create_report_file(
                result
            )

            result[
                "report_path"
            ] = report_path

            log(
                f"REPORT CREATED: "
                f"{report_path}"
            )

            browser.close()

            return result

        except Exception as e:

            log("")

            log(
                f"TEST FAILED: "
                f"{str(e)}"
            )

            page.screenshot(
                path="failure_screenshot.png",
                full_page=True
            )

            result = {

                "status":
                "failed",

                "error":
                str(e),

                "tracked_pairs":
                TARGET_SYMBOLS,

                "tracked_pairs_with_updates":
                0,

                "total_ws_connections":
                len(ws_connections),

                "total_market_updates":
                total_market_updates,

                "pair_summary":
                {},

                "warnings":
                warnings,

                "console_errors":
                console_errors
            }

            report_path = create_report_file(
                result
            )

            result[
                "report_path"
            ] = report_path

            log(
                f"REPORT CREATED: "
                f"{report_path}"
            )

            browser.close()

            return result


if __name__ == "__main__":

    result = run_test()

    print("")
    print("===== FINAL RESULT =====")

    print(result)