import os, json, smtplib
from email.message import EmailMessage
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://blinkdeal.yourcardjourney.store/"
OUT = Path("backup.json")
prev = json.loads(OUT.read_text()) if OUT.exists() else None

rows, sample = 0, ""
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        # Count real table rows (rows with at least two cells)
        rows = page.locator("table tbody tr:has(td:nth-child(2))").count()
        sample = " ".join(page.inner_text("body").split())[:300]
        browser.close()
    print("Backup page rows:", rows)
    print("Backup page sample:", sample)
except Exception as e:
    print("Backup check error:", str(e)[:200])
    raise SystemExit(0)  # keep the previous state, try again next run

live = rows > 0
state = {"live": live, "rows": rows}

# First run only records a baseline, so you are not emailed about the starting state
if prev is not None and live and not prev.get("live"):
    msg = EmailMessage()
    msg["Subject"] = "BlinkDeal page now lists coins - possible BLINKDEAL6 LIVE"
    msg["From"] = msg["To"] = os.environ["EMAIL_USER"]
    msg.set_content(f"The BlinkDeal page now shows {rows} items.\n\n{URL}\n\n"
                    "Check Myntra to confirm the coupon.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["EMAIL_USER"], os.environ["EMAIL_APP_PASSWORD"])
        s.send_message(msg)
    print("Backup email sent")

if prev != state:
    OUT.write_text(json.dumps(state))
