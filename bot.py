import os, requests, re, json, asyncio
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
CHANNEL = "@dailydeals4students"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-IN,en;q=0.9",
}

posted_links = set()

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
    title="Amazon Deal"
    price=""
    mrp=""
    image=None

    try:
        r=requests.get(url,headers=HEADERS,timeout=10)
        soup=BeautifulSoup(r.text,"lxml")

        # TITLE
        t=soup.find("span",{"id":"productTitle"})
        if t: title=t.text.strip()

        if title=="Amazon Deal":
            meta=soup.find("meta",property="og:title")
            if meta: title=meta.get("content",title)

        # PRICE
        prices=soup.select("span.a-price span.a-offscreen")
        if prices: price=prices[0].text.strip()

        # MRP
        mrp_tag=soup.select_one("span.a-price.a-text-price span.a-offscreen")
        if mrp_tag: mrp=mrp_tag.text.strip()

        # IMAGE method 1
        img=soup.find("img",{"id":"landingImage"})
        if img and img.get("src"): image=img["src"]

        # IMAGE method 2
        if not image:
            meta_img=soup.find("meta",property="og:image")
            if meta_img: image=meta_img.get("content")

        # IMAGE method 3 JSON scrape
        if not image:
            scripts=soup.find_all("script",type="application/ld+json")
            for s in scripts:
                try:
                    data=json.loads(s.string)
                    if isinstance(data,dict):
                        if "image" in data:
                            image=data["image"]
                            break
                except: pass

    except:
        pass

    return title,price,mrp,image

async def post_deal(bot,url):
    if url in posted_links:
        return
    posted_links.add(url)

    real=expand_url(url)
    title,price,mrp,image=get_product_data(real)

    caption=f"🔥 {title}\n\n"
    if price: caption+=f"💰 Deal Price: {price}\n"
    if mrp: caption+=f"🏷 MRP: {mrp}\n"

    try:
        if price and mrp:
            p=extract_price_number(price)
            m=extract_price_number(mrp)
            if p and m and m>p:
                caption+=f"🔥 Save: {int((m-p)/m*100)}% OFF\n"
    except: pass

    caption+=f"\n👉 Buy Now:\n{url}"

    if image:
        await bot.send_photo(chat_id=CHANNEL,photo=image,caption=caption)
    else:
        await bot.send_message(chat_id=CHANNEL,text=caption)

async def handle_message(update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text.strip()
    if text.startswith("http") and ("amazon" in text or "amzn" in text):
        await post_deal(context.bot,text)

# AUTO DAILY DEALS SCRAPER
async def auto_deals(bot):
    while True:
        try:
            url="https://www.amazon.in/deals"
            r=requests.get(url,headers=HEADERS,timeout=10)
            soup=BeautifulSoup(r.text,"lxml")

            links=soup.select("a[href*='/dp/']")
            count=0

            for a in links:
                link="https://www.amazon.in"+a.get("href").split("?")[0]
                if link not in posted_links:
                    await post_deal(bot,link)
                    count+=1
                if count>=3:
                    break

        except:
            pass

        await asyncio.sleep(3600)  # check every 1 hour

async def on_start(app):
    app.create_task(auto_deals(app.bot))

app=ApplicationBuilder().token(TOKEN).post_init(on_start).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_message))
app.run_polling()
