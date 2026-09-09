#
# Custom addition: in-bot /login panel so the owner can authorize an
# assistant account directly through the bot.
#
# Old Pyrogram (1.4.16, used elsewhere in this codebase) gets rejected by
# Telegram with UPDATE_APP_TO_LOGIN when starting a *fresh* login (its
# protocol layer is too old). Telethon is actively maintained and is not
# blocked, so we do the phone/code/2FA dance with Telethon, then repack
# the resulting raw MTProto auth key into the exact string format
# Pyrogram 1.4.16's Storage.export_session_string() produces, so the
# rest of the (old-Pyrogram-based) bot can load it unmodified via
# session_name=<string>.
#

import asyncio
import base64
import os
import struct

from pyrogram import filters
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

import config
from YukkiMusic import app
from YukkiMusic.core.mongo import pymongodb
from YukkiMusic.misc import SUDOERS

sessionsdb = pymongodb.assistant_sessions

# user_id -> {"client", "stage", "slot"}
login_sessions = {}

MAX_USER_ID_OLD = 2147483647


def _pack_pyrogram_session(dc_id, auth_key, user_id, is_bot):
    """Recreate Pyrogram 1.4.16's Storage.export_session_string() output
    from a raw MTProto auth key obtained via Telethon."""
    fmt = ">B?256sI?" if user_id < MAX_USER_ID_OLD else ">B?256sQ?"
    packed = struct.pack(fmt, dc_id, False, auth_key, user_id, is_bot)
    return base64.urlsafe_b64encode(packed).decode().rstrip("=")


@app.on_message(filters.command("login") & SUDOERS)
async def login_start(client, message):
    uid = message.from_user.id
    if uid in login_sessions:
        return await message.reply_text(
            "Sizda allaqachon ochiq login jarayoni bor. Bekor qilish uchun /cancellogin yozing."
        )
    args = message.text.split()
    slot = args[1] if len(args) > 1 and args[1] in ("1", "2", "3", "4", "5") else "1"

    tclient = TelegramClient(
        StringSession(), config.API_ID, config.API_HASH
    )
    await tclient.connect()
    login_sessions[uid] = {"client": tclient, "stage": "phone", "slot": slot}
    await message.reply_text(
        f"**Assistant login (Slot {slot})**\n\n"
        "Ulanmoqchi bo'lgan akkauntning telefon raqamini xalqaro formatda yuboring.\n"
        "Masalan: `+998901234567`\n\n"
        "Bekor qilish uchun: /cancellogin"
    )


@app.on_message(filters.command("cancellogin") & SUDOERS)
async def login_cancel(client, message):
    uid = message.from_user.id
    sess = login_sessions.pop(uid, None)
    if not sess:
        return await message.reply_text("Ochiq login jarayoni yo'q.")
    try:
        await sess["client"].disconnect()
    except Exception:
        pass
    await message.reply_text("Bekor qilindi.")


@app.on_message(
    filters.text
    & filters.private
    & SUDOERS
    & ~filters.command(
        ["login", "cancellogin", "addsession", "delsession", "start", "help"]
    )
)
async def login_flow(client, message):
    uid = message.from_user.id
    if uid not in login_sessions:
        return
    sess = login_sessions[uid]
    tclient: TelegramClient = sess["client"]
    text = message.text.strip()

    if sess["stage"] == "phone":
        phone = text
        try:
            await tclient.send_code_request(phone)
        except FloodWaitError as e:
            await message.reply_text(
                f"Juda ko'p urinish qilindi, {e.seconds} soniyadan keyin qayta urining."
            )
            login_sessions.pop(uid, None)
            await tclient.disconnect()
            return
        except Exception as e:
            await message.reply_text(f"Xatolik: {type(e).__name__}: {e}")
            login_sessions.pop(uid, None)
            await tclient.disconnect()
            return
        sess["phone"] = phone
        sess["stage"] = "code"
        await message.reply_text(
            "Telegram'dan kelgan tasdiqlash kodini yuboring.\n\n"
            "⚠️ **Muhim:** Telegram ba'zan kodni boshqa chatga (shu jumladan botga) "
            "yozganingizda avtomatik bekor qilib qo'yadi. Agar «kod noto'g'ri» xatosi "
            "chiqsa, raqamlar orasiga bo'shliq qo'yib qayta yuboring, masalan: `1 2 3 4 5`."
        )
        return

    if sess["stage"] == "code":
        code = text.replace(" ", "")
        try:
            await tclient.sign_in(sess["phone"], code)
        except SessionPasswordNeededError:
            sess["stage"] = "password"
            await message.reply_text(
                "Bu akkauntda 2 bosqichli tasdiqlash (2FA) yoqilgan. Parolni yuboring."
            )
            return
        except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
            await message.reply_text(
                f"Kod noto'g'ri yoki eskirgan ({type(e).__name__}). Qaytadan /login bilan boshlang."
            )
            login_sessions.pop(uid, None)
            await tclient.disconnect()
            return
        except Exception as e:
            await message.reply_text(f"Xatolik: {type(e).__name__}: {e}")
            login_sessions.pop(uid, None)
            await tclient.disconnect()
            return
        await _finish_login(message, uid, sess)
        return

    if sess["stage"] == "password":
        password = text
        try:
            await tclient.sign_in(password=password)
        except Exception as e:
            await message.reply_text(f"Xatolik: {type(e).__name__}: {e}")
            login_sessions.pop(uid, None)
            await tclient.disconnect()
            return
        await _finish_login(message, uid, sess)
        return


async def _finish_login(message, uid, sess):
    tclient: TelegramClient = sess["client"]
    me = await tclient.get_me()
    dc_id = tclient.session.dc_id
    auth_key = tclient.session.auth_key.key
    session_string = _pack_pyrogram_session(
        dc_id, auth_key, me.id, bool(me.bot)
    )
    await tclient.disconnect()

    slot = sess["slot"]
    sessionsdb.update_one(
        {"_id": f"string{slot}"},
        {"$set": {"session": session_string, "name": me.first_name}},
        upsert=True,
    )
    login_sessions.pop(uid, None)
    await message.reply_text(
        f"✅ Ulandi — akkaunt: **{me.first_name}** (Slot {slot}).\n"
        f"Bot 2 soniyadan so'ng qayta ishga tushadi..."
    )
    await asyncio.sleep(2)
    os._exit(1)
