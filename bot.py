async def post_deal(bot,url):
    if url in posted_links:
        return

    real=expand_url(url)
    aff=make_affiliate_link(real)
    aff=shorten(aff)

    title,price,mrp,image,rating,reviews=get_product_data(real)

    if not price:
        return

    # ---- Discount calc ----
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

    # -------- BUTTON --------
    keyboard=[[InlineKeyboardButton("🛒 Buy Now",url=aff)]]
    reply_markup=InlineKeyboardMarkup(keyboard)

    if image:
        await bot.send_photo(chat_id=CHANNEL,photo=image,caption=caption,reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id=CHANNEL,text=caption,reply_markup=reply_markup)
