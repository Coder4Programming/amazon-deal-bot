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

# ---------- SCRAPER ----------
def scrape(url):
    title="Amazon Deal"
    price=""
    original=""
    rating=""
    reviews=""
    image=None

    try:
        r=requests.get(url,headers=HEADERS,timeout=20)
        soup=BeautifulSoup(r.text,"lxml")

        # title
        t=soup.find("span",{"id":"productTitle"})
        if t: title=t.text.strip()

        # deal price
        p=soup.select("span.a-price span.a-offscreen")
        if p: price=p[0].text.strip()

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

        # -------- ORIGINAL PRICE FROM SEARCH --------
        if title!="Amazon Deal":
            search="https://www.amazon.in/s?k="+requests.utils.quote(title[:40])
            r2=requests.get(search,headers=HEADERS,timeout=20)
            soup2=BeautifulSoup(r2.text,"lxml")

            prices=soup2.select("span.a-price span.a-offscreen")
            if prices:
                original=prices[0].text.strip()

        if original==price:
            original=""

    except Exception as e:
        print("SCRAPE ERROR:",e)

    return title,price,original,rating,reviews,image

# ---------- POST ----------
async def post(bot,url):

    real=expand(url)
    aff=make_affiliate(real)

    if real in posted:
        return

    title,price,original,rating,reviews,image=scrape(real)

    if not price:
        return

    posted.add(real)

    caption=f"🔥 {title}\n\n"
    caption+=f"💰 Deal Price: {price}\n"

    if original:
        caption+=f"🏷 Original Price: {original}\n"

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

# ---------- MANUAL ----------
async def handle(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text
    urls=re.findall(r'https?://\S+', text)

    for u in urls:
        if "amazon" in u or "amzn" in u:
            await post(context.bot,u)

# ---------- AUTO ----------
async def auto(bot):
    await asyncio.sleep(10)

    pages=[
        "https://www.amazon.in/gp/bestsellers",
        "https://www.amazon.in/gp/new-releases",
        "https://www.amazon.in/deals",
        "https://www.amazon.in/gp/movers-and-shakers",
        "https://www.amazon.in/s?k=deal+of+the+day",
    ]

    while True:
        try:
            for page in pages:

                r=requests.get(page,headers=HEADERS,timeout=20)
                soup=BeautifulSoup(r.text,"lxml")
                links=soup.select("a[href*='/dp/']")

                # each page se 2-3 deals
                picks=random.sample(links[:15], min(3,len(links)))

                for pick in picks:
                    link="https://www.amazon.in"+pick.get("href").split("?")[0]
                    await post(bot,link)
                    await asyncio.sleep(3)   # spam safe delay

        except Exception as e:
            print("AUTO ERROR:",e)
            await asyncio.sleep(20)

        # full cycle delay
        await asyncio.sleep(90)

# ---------- START ----------
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

