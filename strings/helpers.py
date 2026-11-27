#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

HELP_RU_1 = """✅**<u>Команды админов:</u>**

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


HELP_RU_2 = """✅<u>**Команды плеера:</u>**

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


HELP_RU_3 = """✅<u>**Команды бота:</u>**

/stats - Глобальный топ 10 треков, пользователей и чатов бота, топ 10 в чате и т.д.

/sudolist - Владелец и sudo-пользователи Melodiya Music

/lyrics [название] - Найти текст песни в интернете.

/song [название трека] или [ссылка YT] - Скачать трек с YouTube в mp3 или mp4.

/player - Интерактивная панель воспроизведения.

**c** означает режим канала.

/queue или /cqueue - Очередь музыки."""

HELP_RU_4 = """✅<u>**Дополнительные команды:</u>**
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

HELP_EN_1 = """✅**<u>Admin Commands:</u>**

**c** stands for channel play.

/pause or /cpause - Pause the playing music.
/resume or /cresume- Resume the paused music.
/mute or /cmute- Mute the playing music.
/unmute or /cunmute- Unmute the muted music.
/skip or /cskip- Skip the current playing music.
/stop or /cstop- Stop the playing music.
/shuffle or /cshuffle- Randomly shuffles the queued playlist.
/seek or /cseek - Forward Seek the music to your duration
/seekback or /cseekback - Backward Seek the music to your duration
/restart - Restart bot for your chat .


✅<u>**Specific Skip:**</u>
/skip or /cskip [Number(example: 3)] 
    - Skips music to a the specified queued number. Example: /skip 3 will skip music to third queued music and will ignore 1 and 2 music in queue.

✅<u>**Loop Play:**</u>
/loop or /cloop [enable/disable] or [Numbers between 1-10] 
    - When activated, bot loops the current playing music to 1-10 times on voice chat. Default to 10 times.

✅<u>**Auth Users:**</u>
Auth Users can use admin commands without admin rights in your chat.

/auth [Username] - Add a user to AUTH LIST of the group.
/unauth [Username] - Remove a user from AUTH LIST of the group.
/authusers - Check AUTH LIST of the group."""


HELP_EN_2 = """✅<u>**Play Commands:**</u>

Available Commands = play , vplay , cplay

ForcePlay Commands = playforce , vplayforce , cplayforce

**c** stands for channel play.
**v** stands for video play.
**force** stands for force play.

/play or /vplay or /cplay  - Bot will start playing your given query on voice chat or Stream live links on voice chats.

/playforce or /vplayforce or /cplayforce -  **Force Play** stops the current playing track on voice chat and starts playing the searched track instantly without disturbing/clearing queue.

/channelplay [Chat username or id] or [Disable] - Connect channel to a group and stream music on channel's voice chat from your group.


✅**<u>Bot's Server Playlists:</u>**
/playlist  - Check Your Saved Playlist On Servers.
/deleteplaylist - Delete any saved music in your playlist
/play  - Start playing Your Saved Playlist from Servers."""


HELP_EN_3 = """✅<u>**Bot Commands:**</u>

/stats - Get Top 10 Tracks Global Stats, Top 10 Users of bot, Top 10 Chats on bot, Top 10 Played in a chat etc etc.

/sudolist - Check Sudo Users of Melodiya Music

/lyrics [Music Name] - Searches Lyrics for the particular Music on web.

/song [Track Name] or [YT Link] - Download any track from youtube in mp3 or mp4 formats.

/player -  Get a interactive Playing Panel.

**c** stands for channel play.

/queue or /cqueue- Check Queue List of Music."""

HELP_EN_4 = """✅<u>**Extra  Commands:**</u>
/start - Start the Music Bot.
/help  - Get Commands Helper Menu with detailed explanations of commands.
/ping- Ping the Bot and check Ram, Cpu etc stats of Bot.

✅<u>**Group Settings:**</u>
/settings - Get a complete group's settings with inline buttons

🔗 **Options in Settings:**

1️⃣ You can set **Audio Quality** you want to stream on voice chat.

2️⃣ You can set **Video Quality** you want to stream on voice chat.

3️⃣ **Auth Users**:- You can change admin commands mode from here to everyone or admins only. If everyone, anyone present in you group will be able to use admin commands(like /skip, /stop etc)

4️⃣ **Clean Mode:** When enabled deletes the bot's messages after 5 mins from your group to make sure your chat remains clean and good.

5️⃣ **Command Clean** : When activated, Bot will delete its executed commands (/play, /pause, /shuffle, /stop etc) immediately.

6️⃣ **Play Settings:**

/playmode - Get a complete play settings panel with buttons where you can set your group's play settings. 

<u>Options in playmode:</u>

1️⃣ **Search Mode** [Direct or Inline] - Changes your search mode while you give /play mode. 

2️⃣ **Admin Commands** [Everyone or Admins] - If everyone, anyone present in you group will be able to use admin commands(like /skip, /stop etc)

3️⃣ **Play Type** [Everyone or Admins] - If admins, only admins present in group can play music on voice chat."""

HELP_UZ_1 = """✅**<u>Admin buyruqlari:</u>**

**c** kanal rejimini bildiradi.

/pause yoki /cpause - Musiqani pauzaga qo'yish.
/resume yoki /cresume - Musiqani davom ettirish.
/mute yoki /cmute - Ovozni o'chirish.
/unmute yoki /cunmute - Ovozni yoqish.
/skip yoki /cskip - Joriy trekni o'tkazib yuborish.
/stop yoki /cstop - Musiqani to'xtatish.
/shuffle yoki /cshuffle - Navbatni aralashtirish.
/seek yoki /cseek - Musiqani belgilangan vaqtga oldinga surish
/seekback yoki /cseekback - Musiqani belgilangan vaqtga orqaga surish
/restart - Botni chatingiz uchun qayta ishga tushirish.


✅<u>**Aniq trekka o'tish:**</u>
/skip yoki /cskip [raqam (misol: 3)]
    - Navbatdagi ko'rsatilgan raqamli trekka o'tadi. Misol: /skip 3 uchinchi trekka o'tadi, 1 va 2 ni o'tkazib yuboradi.

✅<u>**Takrorlash:**</u>
/loop yoki /cloop [enable/disable] yoki [1 dan 10 gacha son]
    - Joriy trekni 1-10 marta takrorlaydi. Standart: 10.

✅<u>**Ruxsat berilganlar:**</u>
Ruxsat berilgan foydalanuvchilar admin huquqisiz ham admin buyruqlarini ishlata oladi.

/auth [username] - Foydalanuvchini ruxsat berilganlar ro'yxatiga qo'shish.
/unauth [username] - Foydalanuvchini ro'yxatdan olib tashlash.
/authusers - Ruxsat berilganlar ro'yxatini ko'rish."""


HELP_UZ_2 = """✅<u>**Ijro buyruqlari:</u>**

Mavjud: play , vplay , cplay

Majburiy ijro: playforce , vplayforce , cplayforce

**c** kanal rejimini bildiradi.
**v** videoni bildiradi.
**force** majburiy ijroni bildiradi.

/play yoki /vplay yoki /cplay - Bot so'rovingizni ovozli chatda ijro etadi yoki havola bo'yicha jonli efirni yoqadi.

/playforce yoki /vplayforce yoki /cplayforce - **Force Play** joriy trekni to'xtatib, topilganini darhol boshlaydi, navbatga tegmaydi.

/channelplay [chat username yoki id] yoki [Disable] - Kanalni guruhga ulab, kanalning ovozli chatida musiqa qo'yish.


✅**<u>Bot serveridagi pleylistlar:</u>**
/playlist  - Saqlangan pleylistingiz.
/deleteplaylist - Pleylistdagi trekni o'chirish
/play  - Saqlangan pleylistni ijro etish."""


HELP_UZ_3 = """✅<u>**Bot buyruqlari:</u>**

/stats - Global top 10 treklar, foydalanuvchilar va chatlar, chatdagi top 10 va h.k.

/sudolist - Melodiya Music egasi va sudo foydalanuvchilari

/lyrics [nomi] - Qo'shiq matnini internetdan qidirish.

/song [trek nomi] yoki [YT havolasi] - YouTube'dan trekni mp3 yoki mp4 qilib yuklab olish.

/player - Interaktiv ijro paneli.

**c** kanal rejimini bildiradi.

/queue yoki /cqueue - Musiqa navbati."""

HELP_UZ_4 = """✅<u>**Qo'shimcha buyruqlar:</u>**
/start - Botni ishga tushirish.
/help  - Buyruqlar menyusi va batafsil tushuntirishlar.
/ping - Bot pingi, xotira va protsessor yuklamasi.

✅<u>**Guruh sozlamalari:</u>**
/settings - Guruhning barcha sozlamalari tugmalar bilan

🔗 **Sozlamalarda nima bor:**

1️⃣ Ovozli chat **audio sifati**.

2️⃣ Ovozli chat **video sifati**.

3️⃣ **Ruxsat berilganlar**:- Bu yerda admin buyruqlarini hamma yoki faqat adminlar uchun qilish mumkin. «Hamma» bo'lsa, guruhdagi istalgan kishi admin buyruqlarini (/skip, /stop va h.k.) ishlata oladi.

4️⃣ **Toza rejim:** Bot o'z xabarlarini 5 daqiqadan keyin o'chiradi, chat toza qoladi.

5️⃣ **Buyruqlarni tozalash** : Bot bajarilgan buyruqlarni (/play, /pause, /shuffle, /stop va h.k.) darhol o'chiradi.

6️⃣ **Ijro sozlamalari:**

/playmode - Guruhning ijro sozlamalari paneli.

<u>Playmode'da nima bor:</u>

1️⃣ **Qidiruv rejimi** [Direct yoki Inline] - /play bergan paytda bot qanday qidirishi.

2️⃣ **Admin buyruqlari** [hamma yoki adminlar] - «Hamma» bo'lsa, guruhdagi istalgan kishi admin buyruqlarini (/skip, /stop va h.k.) ishlata oladi.

3️⃣ **Kim qo'ya oladi** [hamma yoki adminlar] - «Adminlar» bo'lsa, ovozli chatda musiqani faqat adminlar qo'yadi."""


_HELPS = {"ru": {}, "uz": {}, "en": {}}
for _n in (1, 2, 3, 4):
    _HELPS["ru"][_n] = globals()[f"HELP_RU_{_n}"]
    _HELPS["uz"][_n] = globals()[f"HELP_UZ_{_n}"]
    _HELPS["en"][_n] = globals()[f"HELP_EN_{_n}"]


def get_help(lang, n):
    """Yordam matni tanlangan tilda (ru/uz), boshqa tillarda inglizcha."""
    return _HELPS.get(lang, _HELPS["en"])[n]

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
