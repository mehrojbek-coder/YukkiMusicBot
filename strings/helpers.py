#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

HELP_1 = """✅**<u>Команды админов:</u>**

**c** означает режим канала.

/pause или /cpause - Поставить музыку на паузу.
/resume или /cresume - Продолжить музыку.
/mute или /cmute - Выключить звук.
/unmute или /cunmute - Включить звук.
/skip или /cskip - Пропустить текущий трек.
/stop или /cstop - Остановить музыку.
/shuffle или /cshuffle - Перемешать очередь.
/seek или /cseek - Перемотать вперёд на указанное время
/seekback или /cseekback - Перемотать назад на указанное время
/restart - Перезапустить бота для вашего чата.


✅<u>**Переход к треку:**</u>
/skip или /cskip [номер (пример: 3)]
    - Переходит к указанному номеру в очереди. Пример: /skip 3 перейдёт к третьему треку, пропустив 1 и 2.

✅<u>**Повтор:**</u>
/loop или /cloop [enable/disable] или [число от 1 до 10]
    - Повторяет текущий трек 1-10 раз. По умолчанию 10.

✅<u>**Авторизованные:**</u>
Авторизованные пользователи могут использовать админ-команды без прав администратора.

/auth [username] - Добавить пользователя в список авторизованных.
/unauth [username] - Убрать пользователя из списка.
/authusers - Показать список авторизованных."""


HELP_2 = """✅<u>**Команды плеера:</u>**

Доступно: play , vplay , cplay

Принудительно: playforce , vplayforce , cplayforce

**c** означает режим канала.
**v** означает видео.
**force** означает принудительное воспроизведение.

/play или /vplay или /cplay - Бот начнёт играть ваш запрос в голосовом чате или включит прямую трансляцию по ссылке.

/playforce или /vplayforce или /cplayforce - **Force Play** останавливает текущий трек и сразу включает найденный, не трогая очередь.

/channelplay [username или id чата] или [Disable] - Подключить канал к группе и играть музыку в голосовом чате канала.


✅**<u>Плейлисты на сервере бота:</u>**
/playlist  - Ваш сохранённый плейлист.
/deleteplaylist - Удалить трек из плейлиста
/play  - Играть сохранённый плейлист."""


HELP_3 = """✅<u>**Команды бота:</u>**

/stats - Глобальный топ 10 треков, пользователей и чатов бота, топ 10 в чате и т.д.

/sudolist - Владелец и sudo-пользователи Melodiya Music

/lyrics [название] - Найти текст песни в интернете.

/song [название трека] или [ссылка YT] - Скачать трек с YouTube в mp3 или mp4.

/player - Интерактивная панель воспроизведения.

**c** означает режим канала.

/queue или /cqueue - Очередь музыки."""

HELP_4 = """✅<u>**Дополнительные команды:</u>**
/start - Запустить бота.
/help  - Меню команд с подробными объяснениями.
/ping - Пинг бота, нагрузка на ОЗУ и процессор.

✅<u>**Настройки группы:</u>**
/settings - Все настройки группы кнопками

🔗 **Что есть в настройках:**

1️⃣ **Качество аудио** голосового чата.

2️⃣ **Качество видео** голосового чата.

3️⃣ **Авторизованные**:- Здесь можно разрешить админ-команды всем или только админам. Если «все», любой участник группы сможет использовать админ-команды (/skip, /stop и т.д.)

4️⃣ **Чистый режим:** Бот удаляет свои сообщения через 5 минут, чат остаётся чистым.

5️⃣ **Очистка команд** : Бот сразу удаляет выполненные команды (/play, /pause, /shuffle, /stop и т.д.).

6️⃣ **Настройки воспроизведения:**

/playmode - Панель настроек воспроизведения группы.

<u>Что есть в playmode:</u>

1️⃣ **Режим поиска** [Direct или Inline] - как бот ищет по команде /play.

2️⃣ **Админ-команды** [все или админы] - Если «все», любой участник группы сможет использовать админ-команды (/skip, /stop и т.д.)

3️⃣ **Кто запускает** [все или админы] - Если «админы», музыку в голосовом чате запускают только администраторы."""

HELP_5 = """🔰**<u>ADD & REMOVE SUDO USERS :</u>**
/addsudo [Username or Reply to a user]
/delsudo [Username or Reply to a user]

🛃**<u>HEROKU:</u>**
/usage - Dyno Usage.

🌐**<u>CONFIG VARS:</u>**
/get_var - Get a config var from Heroku or .env.
/del_var - Delete any var on Heroku or .env.
/set_var [Var Name] [Value] - Set a Var or Update a Var on heroku or .env. Seperate Var and its Value with a space.

🤖**<u>BOT COMMANDS:</u>**
/reboot - Reboot your Bot. 
/update - Update Bot.
/speedtest - Check server speeds
/maintenance [enable / disable] 
/logger [enable / disable] - Bot logs the searched queries in logger group.
/get_log [Number of Lines] - Get log of your bot from heroku or vps. Works for both.
/autoend [enable|disable] - Enable Auto stream end after 3 mins if no one is listening.

📈**<u>STATS COMMANDS:</u>**
/activevoice - Check active voice chats on bot.
/activevideo - Check active video calls on bot.
/stats - Check Bots Stats

⚠️**<u>BLACKLIST CHAT FUNCTION:</u>**
/blacklistchat [CHAT_ID] - Blacklist any chat from using Music Bot
/whitelistchat [CHAT_ID] - Whitelist any blacklisted chat from using Music Bot
/blacklistedchat - Check all blacklisted chats.

👤**<u>BLOCKED FUNCTION:</u>**
/block [Username or Reply to a user] - Prevents a user from using bot commands.
/unblock [Username or Reply to a user] - Remove a user from Bot's Blocked List.
/blockedusers - Check blocked Users Lists

👤**<u>GBAN FUNCTION:</u>**
/gban [Username or Reply to a user] - Gban a user from bot's served chat and stop him from using your bot.
/ungban [Username or Reply to a user] - Remove a user from Bot's gbanned List and allow him for using your bot
/gbannedusers - Check Gbanned Users Lists

🎥**<u>VIDEOCALLS FUNCTION:</u>**
/set_video_limit [Number of Chats] - Set a maximum Number of Chats allowed for Video Calls at a time. Default to 3 chats.
/videomode [download|m3u8] - If download mode is enabled, Bot will download videos instead of playing them in M3u8 form. ByDefault to M3u8. You can use download mode when any query doesnt plays in m3u8 mode.

⚡️**<u>PRIVATE BOT FUNCTION:</u>**
/authorize [CHAT_ID] - Allow a chat for using your bot.
/unauthorize [CHAT_ID] - Disallow a chat from using your bot.
/authorized - Check all allowed chats of your bot.

🌐**<u>BROADCAST FUNCTION:</u>**
/broadcast [Message or Reply to a Message] - Broadcast any message to Bot's Served Chats.

<u>options for broadcast:</u>
**-pin** : This will pin your message 
**-pinloud** : This will pin your message with loud notification
**-user** : This will broadcast your message to the users who have started your bot.
**-assistant** : This will broadcast your message from assistant account of your bot.
**-nobot** : This will force your bot to not broadcast message

**Example:** `/broadcast -user -assistant -pin Hello Testing`

"""
