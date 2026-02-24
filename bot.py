import os
import requests
import re
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
CHANNEL = "@dailydeals4students"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-IN,en;q=0.9",
}

def expand_url(url):
    try:
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=10)
        return r.url
    except:
        return url

def extract_price_number(price_text):
    nums = re.sub(r"[^\d]", "", price_text)
    return int(nums) if nums else None

def get_product_data(url):
    title = "Amazon Deal"
    price = ""
    mrp = ""
    image = None

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")

        # TITLE
        t = soup.find("span", {"id": "productTitle"})
        if t:
            title = t.text.strip()

        # DEAL PRICE
        p = soup.find("span", {"class": "a-offscreen"})
        if p:
            price = p.text.strip()

        # MRP
        mrp_tag = soup.find("span", {"class": "a-price a-text-price"})
        if mrp_tag:
            mrp_span = mrp_tag.find("span", {"class": "a-offscreen"})
            if mrp_span:
                mrp = mrp_span.text.strip()

        # IMAGE
        img = soup.find("img", {"id": "landingImage"})
        if img and img.get("src"):
            image = img["src"]

    except:
        pass

    return title, price, mrp, image

async def handle_message(update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.startswith("http") and ("amazon" in text or "amzn" in text):

        real_url = expand_url(text)
        title, price, mrp, image = get_product_data(real_url)

        caption = f"🔥 {title}\n\n"

        if price:
            caption += f"💰 Deal Price: {price}\n"

        if mrp:
            caption += f"🏷 MRP: {mrp}\n"

        # Discount calculation
        try:
            if price and mrp:
                p_val = extract_price_number(price)
                m_val = extract_price_number(mrp)
                if p_val and m_val and m_val > p_val:
                    discount = int(((m_val - p_val) / m_val) * 100)
                    caption += f"🔥 Save: {discount}% OFF\n"
        except:
            pass

        caption += f"\n👉 Buy Now:\n{text}"

        if image:
            await context.bot.send_photo(chat_id=CHANNEL, photo=image, caption=caption)
        else:
            await context.bot.send_message(chat_id=CHANNEL, text=caption)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
