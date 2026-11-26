#
# /owner paneli — assistant akkauntlarni tugmalar orqali boshqarish
# (ulash / ko'rish / o'chirish). String session yoki buyruq yodlash shart emas.
#
# Akkauntni ulash eski /login oqimidan (telefon -> kod -> 2FA) foydalanadi:
# bu yerda faqat tugmali panel va "slot" tanlash qo'shilgan.
#

import asyncio
import os

from pyrogram import filters
from pyrogram.types import (InlineKeyboardButton,
                            InlineKeyboardMarkup)
from telethon import TelegramClient
from telethon.sessions import StringSession

import config
from YukkiMusic import app
from YukkiMusic.core.mongo import pymongodb
from YukkiMusic.core.userbot import _resolve_session
from YukkiMusic.misc import SUDOERS
from YukkiMusic.plugins.tools.login import login_sessions

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

    if data == "own_addcancel":
        sess = login_sessions.pop(uid, None)
        if sess:
            try:
                await sess["client"].disconnect()
            except Exception:
                pass
        await cq.answer("Bekor qilindi")
        return await cq.message.edit_text(MAIN_TEXT, reply_markup=_main_kb())
