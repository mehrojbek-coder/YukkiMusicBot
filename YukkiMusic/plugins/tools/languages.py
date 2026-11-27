#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

from pykeyboard import InlineKeyboard
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, Message

from config import BANNED_USERS
from strings import get_command, get_string, languages_present
from YukkiMusic.utils.langtool import gt
from YukkiMusic import app
from YukkiMusic.utils.database import get_lang, set_lang
from YukkiMusic.utils.decorators import (ActualAdminCB, language,
                                         languageCB)

# Languages Available


def lanuages_keyboard(_, ctx=None, chat_id=None):
    """ctx: musiqa posti ichidan ochilganda videoid ("None" = telegram/boshqa),
    til tanlangandan keyin ham, "Orqaga" bosilganda ham post tugmalariga qaytadi."""
    suffix = f":{ctx}" if ctx else ""
    keyboard = InlineKeyboard(row_width=3)
    keyboard.add(
        *[
            (
                InlineKeyboardButton(
                    text=languages_present[i],
                    callback_data=f"languages:{i}{suffix}",
                )
            )
            for i in languages_present
        ]
    )
    if ctx:
        keyboard.row(
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data=f"MainMarkup {ctx}|{chat_id}",
            ),
        )
    else:
        keyboard.row(
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data=f"settingsback_helper",
            ),
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"], callback_data=f"close"
            ),
        )
    return keyboard


LANGUAGE_COMMAND = get_command("LANGUAGE_COMMAND")


@app.on_message(
    filters.command(LANGUAGE_COMMAND)
    & filters.group
    & ~filters.edited
    & ~BANNED_USERS
)
@language
async def langs_command(client, message: Message, _):
    keyboard = lanuages_keyboard(_)
    await message.reply_text(
        _["setting_1"].format(gt(message.chat.title), message.chat.id),
        reply_markup=keyboard,
    )


@app.on_callback_query(filters.regex(r"^LG$") & ~BANNED_USERS)
@languageCB
async def lanuagecb(client, CallbackQuery, _):
    try:
        await CallbackQuery.answer()
    except:
        pass
    keyboard = lanuages_keyboard(_)
    return await CallbackQuery.edit_message_reply_markup(
        reply_markup=keyboard
    )


@app.on_callback_query(filters.regex(r"^PLANG ") & ~BANNED_USERS)
@languageCB
async def player_lang_cb(client, CallbackQuery, _):
    try:
        await CallbackQuery.answer()
    except Exception:
        pass
    ctx = CallbackQuery.data.split(None, 1)[1].strip()
    keyboard = lanuages_keyboard(_, ctx, CallbackQuery.message.chat.id)
    return await CallbackQuery.edit_message_reply_markup(
        reply_markup=keyboard
    )


@app.on_callback_query(
    filters.regex(r"languages:(.*?)") & ~BANNED_USERS
)
@ActualAdminCB
async def language_markup(client, CallbackQuery, _):
    parts = (CallbackQuery.data).split(":")
    langauge = parts[1]
    ctx = parts[2] if len(parts) > 2 else None
    chat = CallbackQuery.message.chat
    old = await get_lang(chat.id)
    if str(old) == str(langauge):
        return await CallbackQuery.answer(_["lang_1"], show_alert=True)
    try:
        new_ = get_string(langauge)
    except Exception:
        return await CallbackQuery.answer(_["lang_3"], show_alert=True)
    await set_lang(chat.id, langauge)
    await CallbackQuery.answer(new_["lang_2"], show_alert=True)
    # Menyu matni va tugmalari yangi tilda qayta chiziladi
    keyboard = lanuages_keyboard(new_, ctx, chat.id)
    if ctx:  # musiqa posti ichida: faqat tugmalar yangilanadi
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=keyboard
        )
    try:
        return await CallbackQuery.edit_message_text(
            new_["setting_1"].format(gt(chat.title), chat.id),
            reply_markup=keyboard,
        )
    except Exception:
        return await CallbackQuery.edit_message_reply_markup(
            reply_markup=keyboard
        )
