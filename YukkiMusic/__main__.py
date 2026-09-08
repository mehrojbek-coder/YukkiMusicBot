#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import importlib
import sys

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from config import BANNED_USERS
from YukkiMusic import LOGGER, app, userbot
from YukkiMusic.core.call import Yukki
from YukkiMusic.core.userbot import _resolve_session
from YukkiMusic.plugins import ALL_MODULES
from YukkiMusic.utils.database import get_banned_users, get_gbanned

loop = asyncio.get_event_loop()


async def init():
    has_assistant = any(
        _resolve_session(getattr(config, f"STRING{n}"), str(n))
        for n in (1, 2, 3, 4, 5)
    )
    if not has_assistant:
        LOGGER("YukkiMusic").warning(
            "No Assistant session configured yet. Bot is starting anyway "
            "so you can connect one via /addsession <slot> <session_string>."
        )
    if (
        not config.SPOTIFY_CLIENT_ID
        and not config.SPOTIFY_CLIENT_SECRET
    ):
        LOGGER("YukkiMusic").warning(
            "No Spotify Vars defined. Your bot won't be able to play spotify queries."
        )
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    for attempt in range(5):
        try:
            await app.start()
            break
        except Exception as e:
            LOGGER("YukkiMusic").warning(
                f"app.start() failed (attempt {attempt + 1}/5): {e}"
            )
            if attempt == 4:
                raise
            await asyncio.sleep(3)
    for all_module in ALL_MODULES:
        importlib.import_module("YukkiMusic.plugins" + all_module)
    LOGGER("Yukkimusic.plugins").info(
        "Successfully Imported Modules "
    )
    if has_assistant:
        await userbot.start()
        await Yukki.start()
        try:
            await Yukki.stream_call(
                "http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4"
            )
        except NoActiveGroupCall:
            LOGGER("YukkiMusic").error(
                "[ERROR] - \n\nPlease turn on your Logger Group's Voice Call. Make sure you never close/end voice call in your log group"
            )
            sys.exit()
        except:
            pass
        await Yukki.decorators()
    LOGGER("YukkiMusic").info("Yukki Music Bot Started Successfully")
    await idle()


if __name__ == "__main__":
    loop.run_until_complete(init())
    LOGGER("YukkiMusic").info("Stopping Yukki Music Bot! GoodBye")
