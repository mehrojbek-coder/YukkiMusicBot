#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import sys

from pyrogram import Client
from pyrogram.types import BotCommand

import config

from ..logging import LOGGER


class YukkiBot(Client):
    def __init__(self):
        LOGGER(__name__).info(f"Starting Bot")
        super().__init__(
            "YukkiMusicBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
        )

    async def start(self):
        await super().start()
        get_me = await self.get_me()
        self.username = get_me.username
        self.id = get_me.id

        log_ok = False
        for attempt in range(3):
            try:
                await self.send_message(
                    config.LOG_GROUP_ID, "Bot Started"
                )
                log_ok = True
                break
            except Exception as e:
                LOGGER(__name__).warning(
                    f"Could not reach log group yet (attempt {attempt + 1}/3): "
                    f"{type(e).__name__}: {e}. Send any message in that group "
                    f"now — waiting 8s before retrying."
                )
                await asyncio.sleep(8)
        if not log_ok:
            LOGGER(__name__).warning(
                "Log group still unreachable — starting anyway without it. "
                "Send a message in the log group, then use /reload or restart "
                "the service to pick it up."
            )
        if config.SET_CMDS == str(True):
            try:
                await self.set_bot_commands(
                    [
                        BotCommand("ping", "Check that bot is alive or dead"),
                        BotCommand("play", "Starts playing the requested song"),
                        BotCommand("skip", "Moves to the next track in queue"),
                        BotCommand("pause", "Pause the current playing song"),
                        BotCommand("resume", "Resume the paused song"),
                        BotCommand("end", "Clear the queue and leave voice chat"),
                        BotCommand("shuffle", "Randomly shuffles the queued playlist."),
                        BotCommand("playmode", "Allows you to change the default playmode for your chat"),
                        BotCommand("settings", "Open the settings of the music bot for your chat.")
                        ]
                    )
            except:
                pass
        else:
            pass
        if log_ok:
            try:
                a = await self.get_chat_member(config.LOG_GROUP_ID, self.id)
                if a.status != "administrator":
                    LOGGER(__name__).warning(
                        "Please promote Bot as Admin in Logger Group"
                    )
            except Exception:
                pass
        if get_me.last_name:
            self.name = get_me.first_name + " " + get_me.last_name
        else:
            self.name = get_me.first_name
        LOGGER(__name__).info(f"MusicBot Started as {self.name}")
