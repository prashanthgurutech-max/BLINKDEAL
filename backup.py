import os, re, json, smtplib
from email.message import EmailMessage
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://blinkdeal.yourcardjourney.store/"
OUT = Path("backup.json")
prev = json.loads(OUT.read_text()) if OUT.exists() else {}

status, sample = "", ""
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        body = " ".join(page.inner_text("body").split())
        browser.close()
    sample = body[:300]
    # The first "BlinkDeal is XXX" on the page is the status badge (OFF or LIVE)
    m = re.search(r"BlinkDeal is ([A-Za-z]+)", body)
    status = m.group(1).upper() if m else ""
    print("Backup status:", status or "not found")
    print("Backup page sample:", sample)
except Exception as e:
    print("Backup check error:", str(e)[:200])
    raise SystemExit(0)  # keep the previous state, try again next run

if status not in ("OFF", "LIVE"):
    raise SystemExit(0)  # unknown or still loading: do nothing

# Email only when the status flips from OFF to LIVE (first run just records a baseline)
if status == "LIVE" and prev.get("status") == "OFF":
    msg = EmailMessage()
    msg["Subject"] = "BlinkDeal page says LIVE - possible BLINKDEAL6 active"
    msg["From"] = msg["To"] = os.environ["EMAIL_USER"]
    msg.set_content(f"The BlinkDeal page status changed to LIVE.\n\n{URL}\n\n"
                    "Check Myntra to confirm the coupon.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["EMAIL_USER"], os.environ["EMAIL_APP_PASSWORD"])
        s.send_message(msg)
    print("Backup email sent")

if prev.get("status") != status:
    OUT.write_text(json.dumps({"status": status}))
