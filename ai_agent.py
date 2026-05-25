import os

from dotenv import load_dotenv
from openai import OpenAI

from spot_smoke_test import run_test
from telegram_notifier import send_telegram_message

load_dotenv()

client = OpenAI()

AI_MODEL = os.getenv("AI_MODEL", "gpt-4.1-mini")


def analyze_result(result):
    prompt = f"""
You are a senior QA monitoring AI agent for a crypto exchange.

Your task is NOT to write long explanations.
Your task is to produce a SHORT operational verdict.

Be concise.
Be technical.
Avoid generic QA wording.
Avoid unnecessary explanations.

Test result:
{result}

Return EXACTLY in this format:

===== AI QA VERDICT =====

OVERALL STATUS:
HEALTHY / DEGRADED / CRITICAL

STREAM STATUS:
ALIVE / PARTIAL / DEAD

CRITICAL ISSUES:
- ...

WARNINGS:
- ...

LIKELY EXPLANATION:
...

QA ACTION REQUIRED:
YES / NO

RECOMMENDED ACTION:
- ...

SHOULD CREATE BUG:
YES / NO

IF BUG SHOULD BE CREATED:
BUG TITLE:
...

CONFIDENCE:
LOW / MEDIUM / HIGH

Rules:
- If websocket works and market events are received -> STREAM STATUS = ALIVE
- If some pairs have warnings but stream works -> OVERALL STATUS = DEGRADED
- If no websocket or no market updates -> OVERALL STATUS = CRITICAL
- If warnings are minor or likely flaky -> SHOULD CREATE BUG = NO
- QA ACTION REQUIRED must explain WHAT exactly should be done
- RECOMMENDED ACTION must contain practical next steps
- If issue is likely flaky -> recommend rerun
- If stream is dead -> recommend immediate investigation
- If warnings are minor on dev env -> recommend monitoring only
- Keep output short and structured
"""

    response = client.responses.create(
        model=AI_MODEL,
        input=prompt
    )

    return response.output_text


def main():
    result = run_test()

    status = result.get("status")
    warnings = result.get("warnings", [])
    report_path = result.get("report_path")

    print("")
    print("===== LOCAL TEST RESULT =====")
    print(f"Status: {status}")
    print(f"Report file: {report_path}")
    print(f"Warnings count: {len(warnings)}")

    if status == "passed":
        print("")
        print("✅ Test passed. AI analysis skipped to save API credits.")
        return

    if status == "passed_with_warnings" and len(warnings) <= 2:
        print("")
        print("⚠️ Test passed with minor warnings.")
        print("AI analysis skipped to save API credits.")
        print("")
        print("Warnings:")

        for warning in warnings:
            print(f"- {warning}")

        telegram_message = f"""
⚠️ XBO QA Monitor

Status: {status}
Warnings: {len(warnings)}
Report: {report_path}

Warnings:
{chr(10).join(f"- {warning}" for warning in warnings)}
"""

        send_telegram_message(telegram_message)

        return

    print("")
    print(f"🤖 AI Agent is analyzing test result using {AI_MODEL}...")
    print("")

    ai_report = analyze_result(result)

    print(ai_report)

    telegram_message = f"""
🤖 XBO QA Monitor

Status: {status}
Warnings: {len(warnings)}
Report: {report_path}

AI Verdict:
{ai_report}
"""

    send_telegram_message(telegram_message)

    print("")
    print(f"Raw report file: {report_path}")


if __name__ == "__main__":
    main()