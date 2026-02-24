import os, requests, re, json
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

        # TITLE method 1
        t = soup.find("span", {"id": "productTitle"})
        if t:
            title = t.text.strip()

        # TITLE fallback (meta tag)
        if title == "Amazon Deal":
            meta = soup.find("meta", property="og:title")
            if meta:
                title = meta.get("content", title)

        # PRICE (first visible price)
        prices = soup.select("span.a-price span.a-offscreen")
        if prices:
            price = prices[0].text.strip()

        # MRP (strike price)
        mrp_tag = soup.select_one("span.a-price.a-text-price span.a-offscreen")
        if mrp_tag:
            mrp = mrp_tag.text.strip()

        # IMAGE method 1
        img = soup.find("img", {"id": "landingImage"})
        if img and img.get("src"):
            image = img["src"]

        # IMAGE fallback
        if not image:
            meta_img = soup.find("meta", property="og:image")
            if meta_img:
                image = meta_img.get("content")

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

        # discount safe calculation
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
