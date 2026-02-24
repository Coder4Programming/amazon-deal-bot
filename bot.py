import os, requests, re, asyncio
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
CHANNEL = "@dailydeals4students"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-IN,en;q=0.9",
}

posted_links=set()

# ---------------- PRICE UTILITY ----------------
def extract_price_number(price_text):
    nums=re.sub(r"[^\d]","",price_text)
    return int(nums) if nums else None

# ---------------- SCRAPER ----------------
def get_product_data(url):
    title="Amazon Deal"
    price=""
    mrp=""
    image=None

    try:
        r=requests.get(url,headers=HEADERS,timeout=10)
        soup=BeautifulSoup(r.text,"lxml")

        t=soup.find("span",{"id":"productTitle"})
        if t: title=t.text.strip()

        if title=="Amazon Deal":
            meta=soup.find("meta",property="og:title")
            if meta: title=meta.get("content",title)

        prices=soup.select("span.a-price span.a-offscreen")
        if prices: price=prices[0].text.strip()

        mrp_tag=soup.select_one("span.a-price.a-text-price span.a-offscreen")
        if mrp_tag: mrp=mrp_tag.text.strip()

        img=soup.find("img",{"id":"landingImage"})
        if img and img.get("src"): image=img["src"]

        if not image:
            meta_img=soup.find("meta",property="og:image")
            if meta_img: image=meta_img.get("content")

    except:
        pass

    return title,price,mrp,image

# ---------------- POST DEAL ----------------
async def post_deal(bot,url):
    if url in posted_links:
        return
    posted_links.add(url)

    title,price,mrp,image=get_product_data(url)

    caption=f"🔥 {title}\n\n"
    if price: caption+=f"💰 Deal Price: {price}\n"
    if mrp: caption+=f"🏷 MRP: {mrp}\n"

    try:
        if price and mrp:
            p=extract_price_number(price)
            m=extract_price_number(mrp)
            if p and m and m>p:
                caption+=f"🔥 Save: {int((m-p)/m*100)}% OFF\n"
    except:
        pass

    caption+=f"\n👉 Buy Now:\n{url}"

    if image:
        await bot.send_photo(chat_id=CHANNEL,photo=image,caption=caption)
    else:
        await bot.send_message(chat_id=CHANNEL,text=caption)

# ---------------- USER LINKS ----------------
async def handle_message(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text.strip()
    if text.startswith("http") and ("amazon" in text or "amzn" in text):
        await post_deal(context.bot,text)

# ---------------- AUTO DEALS LOOP ----------------
async def auto_deals(bot):
    await asyncio.sleep(60)  # wait 1 min after start
    while True:
        try:
            r=requests.get("https://www.amazon.in/deals",headers=HEADERS,timeout=10)
            soup=BeautifulSoup(r.text,"lxml")
            links=soup.select("a[href*='/dp/']")

            for a in links[:2]:
                link="https://www.amazon.in"+a.get("href").split("?")[0]
                await post_deal(bot,link)
        except:
            pass

        await asyncio.sleep(3600)  # every hour

# ---------------- START BACKGROUND TASK ----------------
async def start_background(app):
    asyncio.create_task(auto_deals(app.bot))

# ---------------- BOT INIT ----------------
app = ApplicationBuilder().token(TOKEN).concurrent_updates(False).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_message))
app.post_init=start_background

app.run_polling(
    drop_pending_updates=True,
    close_loop=False
)
