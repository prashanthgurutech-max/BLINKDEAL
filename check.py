import os, re, json, smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.myntra.com/gold-bar-24k?rawQuery=Gold%20Bar%2024k"
CODE = "blinkdeal6"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
OUT = Path("data.json")
prev = json.loads(OUT.read_text()) if OUT.exists() else {}
data = {"live": False, "items": [], "error": ""}


def txt(card, sel):
    el = card.query_selector(sel)
    return el.inner_text().strip() if el else ""


try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA)
        page.goto(URL, wait_until="networkidle", timeout=60000)
        body = page.inner_text("body")
        print("Page text length:", len(body))
        if len(body) < 500:
            data["error"] = "Myntra returned an empty or blocked page"
        coupon_live = CODE in body.lower()
        for card in page.query_selector_all("li.product-base")[:60]:
            name = f"{txt(card, '.product-brand')} {txt(card, '.product-product')}".strip()
            price = re.search(r"(\d[\d,]*)", txt(card, ".product-discountedPrice")
                              or txt(card, ".product-price"))
            weight = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|gm|gram)", name, re.I)
            purity = re.search(r"(24|22|18)\s*k", name, re.I)
            link = card.query_selector("a")
            card_text = card.inner_text()
            cp = re.search(r"Best Price\D{0,6}([\d,]+)\s*with coupon", card_text, re.I)
            coupon = int(cp.group(1).replace(",", "")) if cp else None
            listed = int(price.group(1).replace(",", "")) if price else None
            if coupon and not listed:
                amounts = [int(a.replace(",", "")) for a in re.findall(r"\d[\d,]{3,}", card_text)]
                listed = min((a for a in amounts if a > coupon), default=None)
            # The coupon line only appears while the offer is active; also
            # require it to be about 6% below the listed price.
            if coupon and listed and 0.055 <= 1 - coupon / listed <= 0.065:
                coupon_live = True
            if listed and weight:
                data["items"].append({
                    "name": name,
                    "price": listed,
                    "coupon": coupon,
                    "weight": float(weight.group(1)),
                    "purity": int(purity.group(1)) if purity else 24,
                    "url": "https://www.myntra.com/" + (link.get_attribute("href") or "").lstrip("/"),
                })
        data["live"] = coupon_live
        browser.close()
except Exception as e:
    data["error"] = str(e)[:200]
    data["items"] = prev.get("items", [])
    data["live"] = prev.get("live", False)

# Manual fallback: put 1 inside a file named force_live.txt to force LIVE
force = Path("force_live.txt")
if force.exists() and force.read_text().strip() == "1":
    data["live"] = True

if data["live"] and not prev.get("live"):
    msg = EmailMessage()
    msg["Subject"] = "BLINKDEAL6 looks LIVE on Myntra"
    msg["From"] = msg["To"] = os.environ["EMAIL_USER"]
    msg.set_content(f"BLINKDEAL6 detected.\n\nMyntra: {URL}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["EMAIL_USER"], os.environ["EMAIL_APP_PASSWORD"])
        s.send_message(msg)
    print("Email sent")

# Only rewrite the file when something changed, so the repo stays quiet
if {k: v for k, v in prev.items() if k != "checked"} != data:
    data["checked"] = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(data, indent=1))
