#
# Melodiya Music: "Apple Music" uslubidagi hozir ijro etilayotgan karta.
# (Yukki'ning asl thumbnails.py o'rniga; gen_thumb(videoid) imzosi o'zgarmagan.)

import asyncio
import io
import os
import re

import aiohttp
from PIL import (Image, ImageDraw, ImageEnhance, ImageFilter,
                 ImageFont)
from youtubesearchpython.__future__ import VideosSearch

from config import MUSIC_BOT_NAME, YOUTUBE_IMG_URL

W, H = 1280, 720
FONT_B = "assets/Inter-Bold.otf"
FONT_SB = "assets/Inter-SemiBold.otf"
FONT_M = "assets/Inter-Medium.otf"
SS = 4  # yumaloq shakllar uchun supersampling

os.makedirs("cache", exist_ok=True)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _rounded(size, radius):
    """Silliq (antialiasli) yumaloq to'rtburchak maskasi."""
    w, h = size
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        (0, 0, w * SS - 1, h * SS - 1), radius=radius * SS, fill=255
    )
    return m.resize((w, h), Image.LANCZOS)


def _clean_title(t):
    t = re.sub(
        r"[\(\[][^\)\]]*(official|lyric|video|audio|hd|4k|clip|mv|m/v|"
        r"visualizer)[^\)\]]*[\)\]]",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)  # emoji (shriftda yo'q)
    return re.sub(r"\s+", " ", t).strip(" -|") or "Unknown title"


def _clean_artist(a):
    a = re.sub(r"\s*-\s*Topic$", "", a or "", flags=re.I)
    a = re.sub(r"VEVO$", "", a, flags=re.I)
    a = re.sub(r"[\U00010000-\U0010ffff]", "", a)
    return a.strip() or MUSIC_BOT_NAME or ""


def _fit(draw, text, font, max_w, lines=2):
    """Matnni max_w ga sig'diradigan qatorlarga bo'ladi (oxirida ... bilan)."""
    words, out, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                out.append(cur)
            cur = w
            if len(out) == lines:
                break
    if cur and len(out) < lines:
        out.append(cur)
    consumed = " ".join(out)
    if consumed != text and out:
        last = out[-1]
        while last and draw.textlength(last + "...", font=font) > max_w:
            last = last[:-1]
        out[-1] = last.rstrip() + "..."
    return out


def _cover_bg(img):
    """Rasmni 1280x720 ga to'ldirib, xira va qoraytirilgan fon qiladi."""
    r = max(W / img.width, H / img.height)
    bg = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H))
    bg = bg.filter(ImageFilter.GaussianBlur(48))
    bg = ImageEnhance.Color(bg).enhance(1.25)
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    return bg


def render_card(cover, title, artist, duration, bot_name):
    """Kartani chizadi va RGB PIL rasm qaytaradi."""
    cover = cover.convert("RGB")
    bg = _cover_bg(cover).convert("RGBA")

    # shisha (glass) karta
    cx0, cy0, cx1, cy1 = 70, 95, W - 70, H - 95
    cw, ch = cx1 - cx0, cy1 - cy0
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (cx0, cy0 + 14, cx1, cy1 + 14), radius=56, fill=(0, 0, 0, 80)
    )
    bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(26)))
    glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gm = Image.new("L", (W, H), 0)
    gm.paste(_rounded((cw, ch), 56), (cx0, cy0))
    glass.paste((255, 255, 255, 40), (0, 0), gm)
    bg = Image.alpha_composite(bg, glass)
    border = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        (cx0, cy0, cx1, cy1), radius=56, outline=(255, 255, 255, 70), width=2
    )
    bg = Image.alpha_composite(bg, border)

    # muqova (kvadrat, yumaloq, soyali)
    side = 380
    sq = min(cover.size)
    left, top = (cover.width - sq) // 2, (cover.height - sq) // 2
    art = cover.crop((left, top, left + sq, top + sq)).resize((side, side), Image.LANCZOS)
    ax, ay = cx0 + 60, cy0 + (ch - side) // 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        (ax, ay + 18, ax + side, ay + side + 18), radius=40, fill=(0, 0, 0, 95)
    )
    bg = Image.alpha_composite(bg, sh.filter(ImageFilter.GaussianBlur(28)))
    bg.paste(art.convert("RGBA"), (ax, ay), _rounded((side, side), 40))

    bg = bg.convert("RGB")  # RGB ustida "RGBA" rejimi shaffof chizishni yoqadi
    d = ImageDraw.Draw(bg, "RGBA")
    tx = ax + side + 64
    tw = cx1 - 60 - tx

    # yuqori qator: nom + NOW PLAYING
    f_tag = _font(FONT_SB, 24)
    d.text((tx, ay + 2), (bot_name or "").upper() + "  ·  NOW PLAYING", font=f_tag, fill=(255, 255, 255, 190))

    # nom va ijrochi
    f_title = _font(FONT_B, 50)
    f_art = _font(FONT_M, 32)
    ty = ay + 54
    for line in _fit(d, _clean_title(title), f_title, tw, 2):
        d.text((tx, ty), line, font=f_title, fill=(255, 255, 255, 255))
        ty += 60
    d.text(
        (tx, ty + 6),
        _fit(d, _clean_artist(artist), f_art, tw, 1)[0],
        font=f_art,
        fill=(255, 255, 255, 170),
    )

    # progress
    by = ay + side - 118
    d.rounded_rectangle((tx, by, tx + tw, by + 8), radius=4, fill=(255, 255, 255, 70))
    d.rounded_rectangle((tx, by, tx + 34, by + 8), radius=4, fill=(255, 255, 255, 245))
    d.ellipse((tx + 26, by - 6, tx + 46, by + 14), fill=(255, 255, 255, 255))
    f_t = _font(FONT_M, 24)
    d.text((tx, by + 22), "0:00", font=f_t, fill=(255, 255, 255, 170))
    dur = duration or "--:--"
    d.text((tx + tw - d.textlength(dur, font=f_t), by + 22), dur, font=f_t, fill=(255, 255, 255, 170))

    # boshqaruv tugmalari: oldingi, pauza (doira), keyingi
    cy = ay + side - 22
    mx = tx + tw // 2
    white = (255, 255, 255, 245)
    # oldingi |◀◀
    px = mx - 150
    d.rectangle((px - 22, cy - 15, px - 18, cy + 15), fill=white)
    d.polygon([(px - 14, cy), (px + 8, cy - 15), (px + 8, cy + 15)], fill=white)
    d.polygon([(px + 8, cy), (px + 30, cy - 15), (px + 30, cy + 15)], fill=white)
    # pauza
    r = 40
    d.ellipse((mx - r, cy - r, mx + r, cy + r), fill=white)
    d.rounded_rectangle((mx - 15, cy - 19, mx - 5, cy + 19), radius=3, fill=(40, 40, 40, 255))
    d.rounded_rectangle((mx + 5, cy - 19, mx + 15, cy + 19), radius=3, fill=(40, 40, 40, 255))
    # keyingi ▶▶|
    nx = mx + 150
    d.polygon([(nx - 30, cy - 15), (nx - 30, cy + 15), (nx - 8, cy)], fill=white)
    d.polygon([(nx - 8, cy - 15), (nx - 8, cy + 15), (nx + 14, cy)], fill=white)
    d.rectangle((nx + 18, cy - 15, nx + 22, cy + 15), fill=white)

    return bg


async def _fetch(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
            if r.status == 200:
                return await r.read()
    except Exception:
        pass
    return None


async def _cover_image(session, videoid):
    data = await _fetch(session, f"https://i.ytimg.com/vi/{videoid}/maxresdefault.jpg")
    if data:
        return Image.open(io.BytesIO(data))
    data = await _fetch(session, f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg")
    if not data:
        return None
    img = Image.open(io.BytesIO(data))
    if img.height >= 300:  # hqdefault: tepa/pastdagi qora chiziqlarni kesamiz
        bar = int(img.height * 0.125)
        img = img.crop((0, bar, img.width, img.height - bar))
    return img


async def _meta(videoid):
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    for r in (await results.next())["result"]:
        return (
            r.get("title") or "Unknown title",
            (r.get("channel") or {}).get("name") or "",
            r.get("duration") or "",
        )
    return "Unknown title", "", ""


_inflight = {}


def prefetch_thumb(videoid):
    """Muqovani yuklash (download) bilan bir vaqtda orqa fonda tayyorlaydi."""
    path = f"cache/{videoid}_v2.png"
    if not os.path.isfile(path) and videoid not in _inflight:
        _inflight[videoid] = asyncio.ensure_future(_gen_thumb(videoid))


async def gen_thumb(videoid):
    task = _inflight.get(videoid)
    if task is not None:
        try:
            return await task
        finally:
            _inflight.pop(videoid, None)
    return await _gen_thumb(videoid)


async def _gen_thumb(videoid):
    path = f"cache/{videoid}_v2.png"
    if os.path.isfile(path):
        return path
    try:
        async with aiohttp.ClientSession() as session:
            # ma'lumot va muqova rasmi bir vaqtda olinadi (tezroq)
            meta, cover = await asyncio.gather(
                _meta(videoid), _cover_image(session, videoid)
            )
        if cover is None:
            return YOUTUBE_IMG_URL
        title, artist, duration = meta
        loop = asyncio.get_running_loop()
        card = await loop.run_in_executor(
            None, render_card, cover, title, artist, duration, MUSIC_BOT_NAME
        )
        card.save(path, "PNG", optimize=False)
        return path
    except Exception:
        return YOUTUBE_IMG_URL
