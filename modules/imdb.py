# ====================================================================
# PLACE AT: /app/modules/imdb.py
# ACTION: Replace existing file
# ====================================================================
"""
imdb.py — IMDB lookup. PTB v20 async.
Fixes:
  ✅ async handler
  ✅ await on all bot calls
  ✅ ParseMode from telegram.constants
  ✅ blocking HTTP in executor
  ✅ HTML-escaped output
"""
import asyncio
import html
import re

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_imdb_sync(movie_name: str) -> dict:
    try:
        import bs4
    except ImportError:
        return {"error": "bs4 not installed"}

    try:
        q           = "+".join(movie_name.split())
        search_url  = f"https://www.imdb.com/find?ref_=nv_sr_fn&q={q}&s=all"
        page        = requests.get(search_url, headers=HEADERS, timeout=12)
        soup        = bs4.BeautifulSoup(page.content, "lxml")

        odds = soup.findAll("tr", "odd") or soup.findAll("li", {"class": "find-result-item"})
        if not odds:
            return {}

        first    = odds[0]
        link_tag = first.find("a")
        if not link_tag:
            return {}

        mov_title = link_tag.text.strip()
        mov_link  = "https://www.imdb.com" + link_tag["href"].split("?")[0]

        page1 = requests.get(mov_link, headers=HEADERS, timeout=12)
        soup  = bs4.BeautifulSoup(page1.content, "lxml")

        poster = ""
        if soup.find("div", "poster"):
            img = soup.find("div", "poster").find("img")
            if img:
                poster = img.get("src", "")

        mov_details = ""
        if soup.find("div", "title_wrapper"):
            pg          = soup.find("div", "title_wrapper").findNext("div").text
            mov_details = re.sub(r"\s+", " ", pg).strip()

        director = writer = stars = "N/A"
        credits  = soup.findAll("div", "credit_summary_item")
        if len(credits) >= 1:
            director = credits[0].a.text if credits[0].a else "N/A"
        if len(credits) >= 3:
            writer = credits[1].a.text if credits[1].a else "N/A"
            actors = [x.text for x in credits[2].findAll("a")]
            actors = [a for a in actors if "full cast" not in a.lower()]
            stars  = ", ".join(actors[:3]) or "N/A"
        elif len(credits) == 2:
            actors = [x.text for x in credits[1].findAll("a")]
            actors = [a for a in actors if "full cast" not in a.lower()]
            stars  = ", ".join(actors[:3]) or "N/A"

        story_line = "N/A"
        if soup.find("div", "inline canwrap"):
            paras = soup.find("div", "inline canwrap").findAll("p")
            if paras:
                story_line = paras[0].text.strip()

        countries = []
        languages = []
        for node in soup.findAll("div", "txt-block"):
            for a in node.findAll("a"):
                if "country_of_origin" in a.get("href", ""):
                    countries.append(a.text)
                elif "primary_language" in a.get("href", ""):
                    languages.append(a.text)

        mov_rating = "N/A"
        for r in soup.findAll("div", "ratingValue"):
            if r.strong:
                mov_rating = r.strong.get("title", "N/A")
                break

        return {
            "title":    mov_title,
            "link":     mov_link,
            "poster":   poster,
            "details":  mov_details,
            "rating":   mov_rating,
            "country":  countries[0] if countries else "N/A",
            "language": languages[0] if languages else "N/A",
            "director": director,
            "writer":   writer,
            "stars":    stars,
            "story":    story_line,
        }
    except Exception as e:
        return {"error": str(e)}


async def imdb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message

    if not context.args:
        await message.reply_text(
            "Usage: <code>/imdb &lt;movie or anime name&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    movie_name = " ".join(context.args)
    msg = await message.reply_text(
        f"🔍 Searching IMDB for <b>{html.escape(movie_name)}</b>…",
        parse_mode=ParseMode.HTML,
    )

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_imdb_sync, movie_name)

    if not data or "error" in data:
        err = data.get("error", "Movie not found") if data else "Movie not found"
        await msg.edit_text(f"❌ {html.escape(err)}", parse_mode=ParseMode.HTML)
        return

    story   = data["story"]
    caption = (
        f"<a href='{data['poster']}'>&#8203;</a>"
        f"<b>🎬 {html.escape(data['title'])}</b>\n"
        f"<code>{html.escape(data['details'])}</code>\n\n"
        f"⭐ <b>Rating:</b> <code>{html.escape(data['rating'])}</code>\n"
        f"🌍 <b>Country:</b> <code>{html.escape(data['country'])}</code>\n"
        f"🗣 <b>Language:</b> <code>{html.escape(data['language'])}</code>\n"
        f"🎥 <b>Director:</b> <code>{html.escape(data['director'])}</code>\n"
        f"✍️ <b>Writer:</b> <code>{html.escape(data['writer'])}</code>\n"
        f"🌟 <b>Stars:</b> <code>{html.escape(data['stars'])}</code>\n\n"
        f"📖 <b>Story:</b> {html.escape(story[:500])}{'…' if len(story) > 500 else ''}"
    )
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 View on IMDB", url=data["link"])
    ]])

    try:
        await msg.delete()
    except Exception:
        pass

    try:
        await message.reply_text(
            caption, parse_mode=ParseMode.HTML,
            reply_markup=buttons, disable_web_page_preview=False,
        )
    except Exception:
        await message.reply_text(
            caption.replace(f"<a href='{data['poster']}'>&#8203;</a>", ""),
            parse_mode=ParseMode.HTML,
            reply_markup=buttons, disable_web_page_preview=True,
        )


IMDB_HANDLER = DisableAbleCommandHandler("imdb", imdb, run_async=True)
dispatcher.add_handler(IMDB_HANDLER)

__mod_name__     = "IMDb"
__command_list__ = ["imdb"]
__handlers__     = [IMDB_HANDLER]
__help__ = """
*IMDb Search:*
 • /imdb <name> — get IMDb details for any movie or anime.
"""
