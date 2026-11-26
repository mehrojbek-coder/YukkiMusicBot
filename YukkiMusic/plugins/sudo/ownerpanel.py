#
# /owner paneli — assistant akkauntlarni tugmalar orqali boshqarish
# (ulash / ko'rish / o'chirish). String session yoki buyruq yodlash shart emas.
#
# Akkauntni ulash eski /login oqimidan (telefon -> kod -> 2FA) foydalanadi:
# bu yerda faqat tugmali panel va "slot" tanlash qo'shilgan.
#

import asyncio
import os
import time

from pyrogram import filters
from pyrogram.types import (InlineKeyboardButton,
                            InlineKeyboardMarkup)
from telethon import TelegramClient
from telethon.sessions import StringSession

import yt_dlp

import config
from YukkiMusic import app
from YukkiMusic.core.mongo import pymongodb
from YukkiMusic.core.userbot import _resolve_session
from YukkiMusic.misc import SUDOERS
from YukkiMusic.platforms import Youtube as _yt_module
from YukkiMusic.plugins.tools.login import (CODE_KB, code_type_text,
                                            login_sessions)

sessionsdb = pymongodb.assistant_sessions
SLOTS = ("1", "2", "3", "4", "5")


def _slot_info(slot):
    """(ulanganmi, ko'rsatiladigan nom)"""
    env_value = getattr(config, f"STRING{slot}", None)
    doc = sessionsdb.find_one({"_id": f"string{slot}"})
    if _resolve_session(env_value, slot):
        name = (doc or {}).get("name")
        return True, name or ("(env orqali)" if env_value else "(session)")
    return False, None


def _main_kb():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👤 Assistantlar", callback_data="own_list")],
            [InlineKeyboardButton("➕ Assistant qo'shish", callback_data="own_add")],
            [InlineKeyboardButton("🍪 YouTube cookies", callback_data="own_ck")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="own_close")],
        ]
    )


MAIN_TEXT = (
    "👑 **Owner paneli**\n\n"
    "Musiqa chaladigan assistant akkauntlarni shu yerdan boshqarasiz."
)


def _list_view():
    rows = []
    lines = ["👤 **Assistantlar**\n"]
    for s in SLOTS:
        ok, name = _slot_info(s)
        if ok:
            lines.append(f"{s}. ✅ {name}")
            rows.append(
                [InlineKeyboardButton(f"{s}. ✅ {name}", callback_data=f"own_slot_{s}")]
            )
        else:
            lines.append(f"{s}. ▫️ bo'sh")
    rows.append([InlineKeyboardButton("◀️ Orqaga", callback_data="own_back")])
    return "\n".join(lines), InlineKeyboardMarkup(rows)


# ── YouTube cookies ──────────────────────────────────────────────────────────
cookie_wait = set()  # cookies.txt faylini kutayotgan owner id'lari
TEST_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
ck_db = pymongodb.settings


def _ck_status():
    doc = ck_db.find_one({"_id": "yt_cookies"})
    if _yt_module.COOKIES_FILE:
        when = ""
        if doc and doc.get("ts"):
            when = " (yuklangan: " + time.strftime(
                "%Y-%m-%d %H:%M", time.gmtime(doc["ts"])
            ) + " UTC)"
        return f"✅ Cookie yuklangan{when}"
    return "▫️ Cookie yo'q — YouTube serverni bot deb to'sishi mumkin"


def _ck_view():
    rows = [[InlineKeyboardButton("📤 cookies.txt yuklash", callback_data="own_ckup")]]
    if _yt_module.COOKIES_FILE:
        rows.append([InlineKeyboardButton("🧪 Tekshirish", callback_data="own_ckt")])
        rows.append([InlineKeyboardButton("🗑 O'chirish", callback_data="own_ckdel")])
    rows.append([InlineKeyboardButton("◀️ Orqaga", callback_data="own_back")])
    text = (
        "🍪 **YouTube cookies**\n\n"
        f"{_ck_status()}\n\n"
        "YouTube server IP'larini bot deb to'sadi. Zaxira Google akkaunt cookie'si "
        "bilan musiqa yuklanadi."
    )
    return text, InlineKeyboardMarkup(rows)


def _ck_test_sync():
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    # botning haqiqiy yuklashi bilan bir xil sozlamalar (cookie + JS imzo yechuvchi)
    opts.update(_yt_module._extra_opts())
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(TEST_URL, download=False)
    return bool(info and info.get("id"))


async def _ck_test():
    loop = asyncio.get_event_loop()
    try:
        ok = await asyncio.wait_for(
            loop.run_in_executor(None, _ck_test_sync), timeout=90
        )
        return ok, ""
    except Exception as e:
        return False, str(e)[:200]


@app.on_message(filters.private & filters.document & SUDOERS, group=-2)
async def owner_cookie_file(client, message):
    uid = message.from_user.id
    if uid not in cookie_wait:
        return
    doc = message.document
    if doc.file_size and doc.file_size > 2 * 1024 * 1024:
        return await message.reply_text(
            "Fayl juda katta (2 MB dan oshmasligi kerak). `cookies.txt` yuboring."
        )
    path = await message.download(file_name=f"/tmp/ck_{uid}.txt")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ Orqaga", callback_data="own_ck")]]
    )
    if "youtube.com" not in content or "\t" not in content:
        return await message.reply_text(
            "❌ Bu Netscape formatidagi `youtube.com` cookies.txt emas. "
            "Qayta eksport qilib yuboring.",
            reply_markup=kb,
        )
    cookie_wait.discard(uid)
    ck_db.update_one(
        {"_id": "yt_cookies"},
        {"$set": {"content": content, "ts": int(time.time())}},
        upsert=True,
    )
    _yt_module.apply_cookies(content)
    wait = await message.reply_text("✅ Cookie saqlandi. Tekshirilmoqda...")
    ok, err = await _ck_test()
    if ok:
        text = "✅ Cookie ishlayapti! Endi guruhda `/play` ni sinab ko'ring."
    else:
        text = (
            "⚠️ Cookie saqlandi, lekin tekshiruv o'tmadi:\n"
            f"`{err or 'nomalum xato'}`\n\n"
            "Inkognito oynada qayta eksport qilib ko'ring."
        )
    await wait.edit_text(text, reply_markup=kb)


@app.on_message(filters.command("owner") & SUDOERS)
async def owner_cmd(client, message):
    if message.chat.type != "private":
        return await message.reply_text(
            "Owner paneli faqat shaxsiy chatda ishlaydi. Menga shaxsiyda /owner yozing."
        )
    await message.reply_text(MAIN_TEXT, reply_markup=_main_kb())


@app.on_callback_query(filters.regex(r"^own_") & SUDOERS)
async def owner_cb(client, cq):
    data = cq.data
    uid = cq.from_user.id

    if data == "own_close":
        await cq.answer()
        try:
            await cq.message.delete()
        except Exception:
            pass
        return

    if data == "own_back":
        await cq.answer()
        return await cq.message.edit_text(MAIN_TEXT, reply_markup=_main_kb())

    if data == "own_ck":
        cookie_wait.discard(uid)
        await cq.answer()
        text, kb = _ck_view()
        return await cq.message.edit_text(text, reply_markup=kb)

    if data == "own_ckup":
        cookie_wait.add(uid)
        await cq.answer()
        return await cq.message.edit_text(
            "📤 Endi `cookies.txt` faylini shu chatga **fayl qilib** yuboring "
            "(Netscape format, `youtube.com` cookie'lari).",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Orqaga", callback_data="own_ck")]]
            ),
        )

    if data == "own_ckt":
        await cq.answer("Tekshirilmoqda...")
        ok, err = await _ck_test()
        text, kb = _ck_view()
        res = "✅ Test o'tdi" if ok else f"❌ Test o'tmadi: `{err}`"
        return await cq.message.edit_text(f"{text}\n\n{res}", reply_markup=kb)

    if data == "own_ckdel":
        ck_db.delete_one({"_id": "yt_cookies"})
        _yt_module.apply_cookies("")
        await cq.answer("O'chirildi")
        text, kb = _ck_view()
        return await cq.message.edit_text(text, reply_markup=kb)

    if data == "own_list":
        await cq.answer()
        text, kb = _list_view()
        return await cq.message.edit_text(text, reply_markup=kb)

    if data.startswith("own_slot_"):
        slot = data.rsplit("_", 1)[1]
        ok, name = _slot_info(slot)
        await cq.answer()
        if not ok:
            text, kb = _list_view()
            return await cq.message.edit_text(text, reply_markup=kb)
        env_set = bool(getattr(config, f"STRING{slot}", None))
        rows = []
        if not env_set:
            rows.append(
                [InlineKeyboardButton("🗑 O'chirish", callback_data=f"own_del_{slot}")]
            )
        rows.append([InlineKeyboardButton("◀️ Orqaga", callback_data="own_list")])
        note = (
            "\n\n⚠️ Bu akkaunt serverdagi sozlama (env) orqali ulangan, "
            "panel orqali o'chirib bo'lmaydi."
            if env_set
            else ""
        )
        return await cq.message.edit_text(
            f"**Assistant {slot}**\n\nAkkaunt: **{name}**{note}",
            reply_markup=InlineKeyboardMarkup(rows),
        )

    if data.startswith("own_del_"):
        slot = data.rsplit("_", 1)[1]
        await cq.answer()
        return await cq.message.edit_text(
            f"Assistant {slot} o'chirilsinmi? Bot qayta ishga tushadi.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Ha, o'chirish", callback_data=f"own_delok_{slot}"
                        )
                    ],
                    [InlineKeyboardButton("◀️ Orqaga", callback_data=f"own_slot_{slot}")],
                ]
            ),
        )

    if data.startswith("own_delok_"):
        slot = data.rsplit("_", 1)[1]
        sessionsdb.delete_one({"_id": f"string{slot}"})
        await cq.answer("O'chirildi")
        await cq.message.edit_text(
            f"✅ Assistant {slot} o'chirildi. Bot 2 soniyadan so'ng qayta ishga tushadi...",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Orqaga", callback_data="own_back")]]
            ),
        )
        await asyncio.sleep(2)
        os._exit(1)

    if data == "own_add":
        await cq.answer()
        free = [s for s in SLOTS if not _slot_info(s)[0]]
        if not free:
            return await cq.message.edit_text(
                "Hamma 5 ta slot band. Avval bittasini o'chiring.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("◀️ Orqaga", callback_data="own_back")]]
                ),
            )
        if uid in login_sessions:
            try:
                await login_sessions[uid]["client"].disconnect()
            except Exception:
                pass
            login_sessions.pop(uid, None)
        slot = free[0]
        tclient = TelegramClient(StringSession(), config.API_ID, config.API_HASH)
        await tclient.connect()
        login_sessions[uid] = {"client": tclient, "stage": "phone", "slot": slot}
        return await cq.message.edit_text(
            f"➕ **Assistant qo'shish (slot {slot})**\n\n"
            "Musiqa chaladigan akkauntning telefon raqamini xalqaro formatda yuboring.\n"
            "Masalan: `+998901234567`\n\n"
            "Keyin Telegram'dan kelgan kodni yuborasiz (2 bosqichli parol bo'lsa, uni ham).",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Orqaga", callback_data="own_addcancel")]]
            ),
        )

    if data == "own_resend":
        sess = login_sessions.get(uid)
        if not sess or sess.get("stage") != "code":
            await cq.answer("Faol login jarayoni yo'q", show_alert=True)
            return
        try:
            sent = await sess["client"].send_code_request(
                sess["phone"], force_sms=True
            )
        except Exception as e:
            await cq.answer(f"Xatolik: {type(e).__name__}", show_alert=True)
            return
        await cq.answer("Qayta yuborildi")
        return await cq.message.reply_text(
            f"📨 Kod qayta yuborildi: **{code_type_text(sent)}**.\n"
            "SMS bir necha daqiqa kechikishi mumkin. Kelgach kodni (`1 2 3 4 5` ko'rinishida) yuboring.",
            reply_markup=CODE_KB,
        )

    if data == "own_addcancel":
        sess = login_sessions.pop(uid, None)
        if sess:
            try:
                await sess["client"].disconnect()
            except Exception:
                pass
        await cq.answer("Bekor qilindi")
        return await cq.message.edit_text(MAIN_TEXT, reply_markup=_main_kb())
