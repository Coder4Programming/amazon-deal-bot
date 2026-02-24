import os, requests, asyncio, random, re
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
CHANNEL = "@dailydeals4students"
AFF_TAG="cyberguard224-21"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.amazon.in/",
}

posted=set()

# ---------- affiliate ----------
def make_affiliate(url):
    if "tag=" in url:
        return url
    if "?" in url:
        return url+"&tag="+AFF_TAG
    return url+"?tag="+AFF_TAG

# ---------- expand ----------
def expand(url):
    try:
        r=requests.get(url,headers=HEADERS,allow_redirects=True,timeout=20)
        return r.url
    except:
        return url

# ---------- scraper ----------
def scrape(url):
    title="Amazon Deal"
    price=""
    mrp=""
    rating=""
    reviews=""
    image=None

    try:
        r=requests.get(url,headers=HEADERS,timeout=20)
        soup=BeautifulSoup(r.text,"lxml")

        # title
        t=soup.find("span",{"id":"productTitle"})
        if t: title=t.text.strip()

        # price
        p=soup.select("span.a-price span.a-offscreen")
        if p: price=p[0].text.strip()

        # ----- STRONG MRP DETECTION -----
        m=soup.select_one("span.a-price.a-text-price span.a-offscreen")
        if m: mrp=m.text.strip()

        if not mrp:
            m2=soup.find("span",{"id":"priceblock_ourprice"})
            if m2: mrp=m2.text.strip()

        if not mrp:
            m3=soup.find("span",{"id":"priceblock_dealprice"})
            if m3: mrp=m3.text.strip()

        if not mrp:
            all_prices=soup.find_all("span")
            for a in all_prices:
                txt=a.text.strip()
                if "₹" in txt and len(txt)<15 and txt!=price:
                    mrp=txt
                    break

        # rating
        r_tag=soup.find("span",{"class":"a-icon-alt"})
        if r_tag:
            rating=r_tag.text.split(" ")[0]

        # reviews
        rev=soup.find("span",{"id":"acrCustomerReviewText"})
        if rev:
            reviews=rev.text.strip()

        # image
        img=soup.find("img",{"id":"landingImage"})
        if img and img.get("src"):
            image=img["src"]

        if not image:
            meta=soup.find("meta",property="og:image")
            if meta:
                image=meta.get("content")

    except Exception as e:
        print("SCRAPE ERROR:",e)

    return title,price,mrp,rating,reviews,image

# ---------- post ----------
async def post(bot,url):

    real=expand(url)
    aff=make_affiliate(real)

    if real in posted:
        return

    title,price,mrp,rating,reviews,image=scrape(real)

    if not price:
        return

    # ----- discount calc -----
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

    posted.add(real)

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
    markup=InlineKeyboardMarkup(keyboard)

    if image:
        await bot.send_photo(chat_id=CHANNEL,photo=image,caption=caption,reply_markup=markup)
    else:
        await bot.send_message(chat_id=CHANNEL,text=caption,reply_markup=markup)

# ---------- manual ----------
async def handle(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text
    urls=re.findall(r'https?://\S+', text)

    for u in urls:
        if "amazon" in u or "amzn" in u:
            await post(context.bot,u)

# ---------- auto ----------
async def auto(bot):
    await asyncio.sleep(10)

    pages=[
        "https://www.amazon.in/gp/bestsellers",
        "https://www.amazon.in/gp/new-releases",
        "https://www.amazon.in/deals",
    ]

    while True:
        try:
            for page in pages:
                r=requests.get(page,headers=HEADERS,timeout=20)
                soup=BeautifulSoup(r.text,"lxml")
                links=soup.select("a[href*='/dp/']")

                if links:
                    pick=random.choice(links[:8])
                    link="https://www.amazon.in"+pick.get("href").split("?")[0]
                    await post(bot,link)

        except Exception as e:
            print("AUTO ERROR:",e)
            await asyncio.sleep(20)

        await asyncio.sleep(120)

# ---------- start ----------
async def start(app):
    asyncio.create_task(auto(app.bot))

app = (
    ApplicationBuilder()
    .token(TOKEN)
    .connect_timeout(30)
    .read_timeout(30)
    .write_timeout(30)
    .build()
)

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle))
app.post_init=start

print("BOT STARTING...")
app.run_polling(drop_pending_updates=True)
