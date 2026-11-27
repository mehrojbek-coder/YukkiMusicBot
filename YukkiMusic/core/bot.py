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

import os

from pyrogram import Client
from pyrogram.types import (BotCommand, BotCommandScopeAllGroupChats,
                            BotCommandScopeAllPrivateChats)

import config

from ..logging import LOGGER
from .fancy import install as _fancy_install

# Barcha matn va tugmalar chiroyli shriftga o'giriladi
_fancy_install()


class YukkiBot(Client):
    def __init__(self):
        LOGGER(__name__).info(f"Starting Bot")
        # Sessiya fayli (guruhlarni "eslab qolish" xotirasi) docker volume'da saqlanadi,
        # shunda bot yangilansa ham log guruhi "Peer id invalid" bo'lib qolmaydi.
        session_dir = os.environ.get("SESSION_DIR", "/app/sessions")
        try:
            os.makedirs(session_dir, exist_ok=True)
        except OSError:
            session_dir = "."
        super().__init__(
            "YukkiMusicBot",
            workdir=session_dir,
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
        await self._set_command_menu()
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


    async def _set_command_menu(self):
        """Shaxsiy chatda faqat u yerda ishlaydigan, guruhda esa guruhdagi buyruqlar."""
        private = {
            "ru": [
                ("start", "Запустить бота"),
                ("help", "Помощь и список команд"),
                ("song", "Скачать трек или видео"),
                ("playlist", "Мои плейлисты"),
                ("deleteplaylist", "Удалить плейлист"),
            ],
            "uz": [
                ("start", "Botni ishga tushirish"),
                ("help", "Yordam va buyruqlar ro'yxati"),
                ("song", "Trek yoki videoni yuklab olish"),
                ("playlist", "Mening pleylistlarim"),
                ("deleteplaylist", "Pleylistni o'chirish"),
            ],
        }
        group = {
            "ru": [
                ("play", "Включить трек (название или ссылка)"),
                ("vplay", "Включить видео"),
                ("pause", "Пауза"),
                ("resume", "Продолжить"),
                ("skip", "Следующий трек"),
                ("stop", "Остановить и выйти из чата"),
                ("shuffle", "Перемешать очередь"),
                ("loop", "Повтор трека"),
                ("seek", "Перемотать вперёд"),
                ("mute", "Выключить звук"),
                ("unmute", "Включить звук"),
                ("playlist", "Мои плейлисты"),
                ("song", "Скачать трек или видео"),
                ("lang", "Сменить язык"),
                ("settings", "Настройки бота в группе"),
                ("playmode", "Режим воспроизведения"),
                ("auth", "Выдать доступ участнику"),
                ("unauth", "Забрать доступ"),
                ("authusers", "Список с доступом"),
                ("stats", "Статистика"),
                ("ping", "Проверить бота"),
                ("help", "Помощь"),
            ],
            "uz": [
                ("play", "Musiqa qo'yish (nom yoki havola)"),
                ("vplay", "Video qo'yish"),
                ("pause", "Pauza"),
                ("resume", "Davom ettirish"),
                ("skip", "Keyingi trek"),
                ("stop", "To'xtatish va chatdan chiqish"),
                ("shuffle", "Navbatni aralashtirish"),
                ("loop", "Trekni takrorlash"),
                ("seek", "Oldinga o'tkazish"),
                ("mute", "Ovozni o'chirish"),
                ("unmute", "Ovozni yoqish"),
                ("playlist", "Mening pleylistlarim"),
                ("song", "Trek yoki videoni yuklash"),
                ("lang", "Tilni o'zgartirish"),
                ("settings", "Guruh sozlamalari"),
                ("playmode", "Ijro rejimi"),
                ("auth", "Ishtirokchiga ruxsat berish"),
                ("unauth", "Ruxsatni olib tashlash"),
                ("authusers", "Ruxsat berilganlar ro'yxati"),
                ("stats", "Statistika"),
                ("ping", "Botni tekshirish"),
                ("help", "Yordam"),
            ],
        }
        for scope, table in (
            (BotCommandScopeAllPrivateChats(), private),
            (BotCommandScopeAllGroupChats(), group),
        ):
            for lang, items in table.items():
                cmds = [BotCommand(c, d) for c, d in items]
                try:
                    # ru -- asosiy (barcha tillar uchun), uz -- o'zbek tili foydalanuvchilariga
                    await self.set_bot_commands(
                        cmds,
                        scope=scope,
                        language_code="" if lang == "ru" else lang,
                    )
                except Exception as e:
                    LOGGER(__name__).warning(f"set_bot_commands failed: {e}")
