#
# Custom addition: in-bot panel to connect an assistant session string,
# without needing to redeploy with a new STRING env var.
#

import asyncio
import os

from pyrogram import Client, filters
from pyrogram.errors import RPCError

import config
from YukkiMusic import app
from YukkiMusic.core.mongo import pymongodb
from YukkiMusic.misc import SUDOERS

sessionsdb = pymongodb.assistant_sessions


@app.on_message(filters.command("addsession") & SUDOERS)
async def add_session(client, message):
    args = message.text.split(None, 2)
    if len(args) < 3 or args[1].strip() not in ("1", "2", "3", "4", "5"):
        return await message.reply_text(
            "**Foydalanish:** `/addsession <slot 1-5> <session_string>`\n"
            "Misol: `/addsession 1 BQC9...`\n\n"
            "Slot — bir nechta assistant akkaunt bo'lsa, ularni ajratish uchun (1 dan 5 gacha)."
        )

    slot = args[1].strip()
    session_string = args[2].strip()

    mystic = await message.reply_text("Sessiya tekshirilmoqda...")

    test_client = Client(
        session_name=session_string,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        no_updates=True,
    )
    try:
        await test_client.start()
        me = await test_client.get_me()
        await test_client.stop()
    except RPCError as e:
        return await mystic.edit_text(f"❌ Sessiya yaroqsiz: `{e}`")
    except Exception as e:
        return await mystic.edit_text(f"❌ Xatolik: `{e}`")

    sessionsdb.update_one(
        {"_id": f"string{slot}"},
        {"$set": {"session": session_string, "name": me.first_name}},
        upsert=True,
    )
    await mystic.edit_text(
        f"✅ Sessiya saqlandi (Slot {slot}) — akkaunt: **{me.first_name}**.\n"
        f"O'zgarish kuchga kirishi uchun bot 2 soniyadan so'ng qayta ishga tushadi..."
    )
    await asyncio.sleep(2)
    os._exit(1)


@app.on_message(filters.command("delsession") & SUDOERS)
async def del_session(client, message):
    args = message.text.split(None, 1)
    if len(args) < 2 or args[1].strip() not in ("1", "2", "3", "4", "5"):
        return await message.reply_text(
            "**Foydalanish:** `/delsession <slot 1-5>`"
        )
    slot = args[1].strip()
    sessionsdb.delete_one({"_id": f"string{slot}"})
    mystic = await message.reply_text(
        f"🗑 Slot {slot} tozalandi. Bot 2 soniyadan so'ng qayta ishga tushadi..."
    )
    await asyncio.sleep(2)
    os._exit(1)
