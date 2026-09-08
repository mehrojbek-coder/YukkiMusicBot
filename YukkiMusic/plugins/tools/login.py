#
# Custom addition: in-bot /login panel so the owner can authorize an
# assistant account (phone -> code -> optional 2FA password) directly
# through the bot, without running any script locally.
#

import asyncio
import os

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    SessionPasswordNeeded,
)

import config
from YukkiMusic import app
from YukkiMusic.core.mongo import pymongodb
from YukkiMusic.misc import SUDOERS

sessionsdb = pymongodb.assistant_sessions

# user_id -> {"client", "stage", "slot", "phone", "phone_code_hash"}
login_sessions = {}


@app.on_message(filters.command("login") & SUDOERS)
async def login_start(client, message):
    uid = message.from_user.id
    if uid in login_sessions:
        return await message.reply_text(
            "Sizda allaqachon ochiq login jarayoni bor. Bekor qilish uchun /cancellogin yozing."
        )
    args = message.text.split()
    slot = args[1] if len(args) > 1 and args[1] in ("1", "2", "3", "4", "5") else "1"

    temp = Client(":memory:", api_id=config.API_ID, api_hash=config.API_HASH)
    await temp.connect()
    login_sessions[uid] = {"client": temp, "stage": "phone", "slot": slot}
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
    temp: Client = sess["client"]
    text = message.text.strip()

    if sess["stage"] == "phone":
        phone = text
        try:
            sent = await temp.send_code(phone)
        except FloodWait as e:
            await message.reply_text(
                f"Juda ko'p urinish qilindi, {e.value} soniyadan keyin qayta urining."
            )
            login_sessions.pop(uid, None)
            await temp.disconnect()
            return
        except Exception as e:
            await message.reply_text(f"Xatolik: {type(e).__name__}: {e}")
            login_sessions.pop(uid, None)
            await temp.disconnect()
            return
        sess["phone"] = phone
        sess["phone_code_hash"] = sent.phone_code_hash
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
            await temp.sign_in(sess["phone"], sess["phone_code_hash"], code)
        except SessionPasswordNeeded:
            sess["stage"] = "password"
            await message.reply_text(
                "Bu akkauntda 2 bosqichli tasdiqlash (2FA) yoqilgan. Parolni yuboring."
            )
            return
        except (PhoneCodeInvalid, PhoneCodeExpired) as e:
            await message.reply_text(
                f"Kod noto'g'ri yoki eskirgan ({type(e).__name__}). Qaytadan /login bilan boshlang."
            )
            login_sessions.pop(uid, None)
            await temp.disconnect()
            return
        except Exception as e:
            await message.reply_text(f"Xatolik: {type(e).__name__}: {e}")
            login_sessions.pop(uid, None)
            await temp.disconnect()
            return
        await _finish_login(message, uid, sess)
        return

    if sess["stage"] == "password":
        password = text
        try:
            await temp.check_password(password)
        except PasswordHashInvalid:
            await message.reply_text("Parol noto'g'ri. Qayta yuboring yoki /cancellogin.")
            return
        except Exception as e:
            await message.reply_text(f"Xatolik: {type(e).__name__}: {e}")
            login_sessions.pop(uid, None)
            await temp.disconnect()
            return
        await _finish_login(message, uid, sess)
        return


async def _finish_login(message, uid, sess):
    temp: Client = sess["client"]
    session_string = await temp.export_session_string()
    me = await temp.get_me()
    await temp.disconnect()
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
