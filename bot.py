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

# ---------------- EXPAND SHORT LINK ----------------
def expand_url(url):
    try:
        r=requests.get(url,headers=HEADERS,allow_redirects=True,timeout=10)
        return r.url
    except:
        return url

# ---------------- PRICE UTILITY ----------------
def extract_price_number(price_text):
    nums=re.sub(r"[^\d]","",price_text or "")
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

    except Exception as e:
        print("SCRAPE ERROR:", e)

    return title,price,mrp,image

# ---------------- POST DEAL ----------------
async def post_deal(bot,url):
    print("POST DEAL CALLED:", url)

    if url in posted_links:
        return

    real_url=expand_url(url)
    title,price,mrp,image=get_product_data(real_url)

    if not price:
        print("No price found")
        return

    posted_links.add(url)

    caption=f"🔥 {title}\n\n"
    caption+=f"💰 Deal Price: {price}\n"

    if mrp:
        caption+=f"🏷 MRP: {mrp}\n"

    caption+=f"\n👉 Buy Now:\n{url}"

    if image:
        await bot.send_photo(chat_id=CHANNEL,photo=image,caption=caption)
    else:
        await bot.send_message(chat_id=CHANNEL,text=caption)

# ---------------- USER LINKS ----------------
async def handle_message(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text.strip()
    print("MESSAGE RECEIVED:", text)

    if text.startswith("http") and ("amazon" in text or "amzn" in text):
        await post_deal(context.bot,text)

# ---------------- AUTO DEALS LOOP ----------------
async def auto_deals(bot):
    await asyncio.sleep(60)
    while True:
        try:
            print("Checking Amazon deals...")

            r=requests.get("https://www.amazon.in/deals",headers=HEADERS,timeout=10)
            soup=BeautifulSoup(r.text,"lxml")
            links=soup.select("a[href*='/dp/']")

            for a in links[:3]:
                link="https://www.amazon.in"+a.get("href").split("?")[0]
                await post_deal(bot,link)

        except Exception as e:
            print("AUTO DEAL ERROR:", e)

        await asyncio.sleep(3600)

# ---------------- START BACKGROUND TASK ----------------
async def start_background(app):
    asyncio.create_task(auto_deals(app.bot))

# ---------------- BOT INIT ----------------
app = ApplicationBuilder().token(TOKEN).concurrent_updates(False).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_message))
app.post_init=start_background

app.run_polling(drop_pending_updates=True, close_loop=False)
