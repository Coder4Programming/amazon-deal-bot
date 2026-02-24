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
        r=requests.get(url,headers=HEADERS,allow_redirects=True,timeout=10)
        return r.url
    except:
        return url

# ---------- scraper ----------
def scrape(url):
    title="Amazon Deal"
    price=""
    image=None

    try:
        r=requests.get(url,headers=HEADERS,timeout=10)
        soup=BeautifulSoup(r.text,"lxml")

        t=soup.find("span",{"id":"productTitle"})
        if t: title=t.text.strip()

        p=soup.select("span.a-price span.a-offscreen")
        if p: price=p[0].text.strip()

        img=soup.find("img",{"id":"landingImage"})
        if img and img.get("src"):
            image=img["src"]

    except:
        pass

    return title,price,image

# ---------- post ----------
async def post(bot,url):

    real=expand(url)
    aff=make_affiliate(real)

    if real in posted:
        return

    title,price,image=scrape(real)

    if not price:
        return

    posted.add(real)

    caption=f"🔥 {title}\n\n💰 {price}"

    keyboard=[[InlineKeyboardButton("🛒 Buy Now",url=aff)]]
    markup=InlineKeyboardMarkup(keyboard)

    if image:
        await bot.send_photo(chat_id=CHANNEL,photo=image,caption=caption,reply_markup=markup)
    else:
        await bot.send_message(chat_id=CHANNEL,text=caption,reply_markup=markup)

# ---------- manual links ----------
async def handle(update:Update,context:ContextTypes.DEFAULT_TYPE):
    text=update.message.text
    urls=re.findall(r'https?://\S+', text)

    for u in urls:
        if "amazon" in u or "amzn" in u:
            await post(context.bot,u)

# ---------- auto deals ----------
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
                r=requests.get(page,headers=HEADERS,timeout=10)
                soup=BeautifulSoup(r.text,"lxml")
                links=soup.select("a[href*='/dp/']")

                if links:
                    pick=random.choice(links)
                    link="https://www.amazon.in"+pick.get("href").split("?")[0]
                    await post(bot,link)

        except Exception as e:
            print("AUTO ERROR:",e)

        await asyncio.sleep(240)

# ---------- start ----------
async def start(app):
    asyncio.create_task(auto(app.bot))

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle))
app.post_init=start

print("BOT STARTING...")
app.run_polling(drop_pending_updates=True)
