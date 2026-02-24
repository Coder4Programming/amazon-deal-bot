import os, requests, asyncio, random, re
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
CHANNEL = "@dailydeals4students"
AFF_TAG="cyberguard224-21"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.amazon.in/",
}

posted_links=set()

# ---------- affiliate link ----------
def make_affiliate_link(url):
    if "tag=" in url:
        return url
    if "?" in url:
        return url+"&tag="+AFF_TAG
    return url+"?tag="+AFF_TAG

# ---------- short link ----------
def shorten(url):
    try:
        r=requests.get("https://tinyurl.com/api-create.php?url="+url,timeout=10)
        return r.text
    except:
        return url

# ---------- expand short link ----------
def expand_url(url):
    try:
        r=requests.get(url,headers=HEADERS,allow_redirects=True,timeout=10)
        return r.url
    except:
        return url

# ---------- scraper ----------
def get_product_data(url):
    title="Amazon Deal"
    price=""
    mrp=""
    image=None
    rating=""
    reviews=""

    try:
        r=requests.get(url,headers=HEADERS,timeout=10)
        soup=BeautifulSoup(r.text,"lxml")

        t=soup.find("span",{"id":"productTitle"})
        if t: title=t.text.strip()

        p=soup.select("span.a-price span.a-offscreen")
        if p: price=p[0].text.strip()

        m=soup.select_one("span.a-price.a-text-price span.a-offscreen")
        if m: mrp=m.text.strip()

        img=soup.find("img",{"id":"landingImage"})
        if img and img.get("src"): image=img["src"]

        r_tag=soup.find("span",{"class":"a-icon-alt"})
        if r_tag:
            rating=r_tag.text.split(" ")[0]

        rev=soup.find("span",{"id":"acrCustomerReviewText"})
        if rev:
            reviews=rev.text.strip()

    except:
        pass

    return title,price,mrp,image,rating,reviews

# ---------- post deal ----------
async def post_deal(bot,url):
    if url in posted_links:
        return

    real=expand_url(url)
    aff=make_affiliate_link(real)
    aff=shorten(aff)

    title,price,mrp,image,rating,reviews=get_product_data(real)

    if not price:
        return

    discount=""
    try:
        if price and mrp:
            p=int(re.sub(r"\D","",price))
            m=int(re.sub(r"\D","",mrp))
            if m>p and m>p*1.1:
                discount=str(int((m-p)/m*100))+"% OFF"
            else:
                mrp=""
    except:
        mrp=""

    posted_links.add(url)

    caption=f"🔥 {title}\n\n"
    caption+=f"💰 Deal Price: {price}\n"

    if mrp:
        caption+=f"🏷 MRP: {mrp}\n"

    if discount:
        caption+=f"🔥 Save: {discount}\n"

    if rating:
        caption+=f"⭐ Rating: {rating}"
        if reviews:
            caption+=f" ({reviews})"
        caption+="\n"

    keyboard=[[InlineKeyboardButton("🛒 Buy Now",url=aff)]]
    reply_markup=InlineKeyboardMarkup(keyboard)

    if image:
        await bot.send_photo(chat_id=CHANNEL,photo=image,caption=caption,reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id=CHANNEL,text=caption,reply_markup=reply_markup)

# ---------- manual links ----------
async def handle_message(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    urls = re.findall(r'https?://\S+', text)

    for url in urls:
        if "amazon" in url or "amzn" in url:
            await post_deal(context.bot,url)

# ---------- auto amazon scan ----------
async def auto_deals(bot):
    await asyncio.sleep(10)

    search_urls=[
        "https://www.amazon.in/s?k=",
        "https://www.amazon.in/gp/bestsellers",
        "https://www.amazon.in/gp/new-releases",
        "https://www.amazon.in/deals",
    ]

    while True:
        try:
            for url in search_urls:
                r=requests.get(url,headers=HEADERS,timeout=10)
                soup=BeautifulSoup(r.text,"lxml")
                links=soup.select("a[href*='/dp/']")

                if links:
                    chosen=random.choice(links)
                    link="https://www.amazon.in"+chosen.get("href").split("?")[0]
                    await post_deal(bot,link)

        except:
            pass

        await asyncio.sleep(120)

# ---------- start ----------
async def start_background(app):
    asyncio.create_task(auto_deals(app.bot))

app = ApplicationBuilder().token(TOKEN).concurrent_updates(False).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_message))
app.post_init=start_background

app.run_polling(drop_pending_updates=True, close_loop=False)
