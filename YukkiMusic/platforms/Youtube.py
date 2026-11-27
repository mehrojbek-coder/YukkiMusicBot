#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

import asyncio
import time
import os
import re
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

import config

# ── YouTube cookies (ixtiyoriy, lekin 2024+dan beri KO'P VIDEO uchun SHART) ──
# YouTube endi ko'p so'rovlarni (hatto mashhur, haqiqiy videolarni ham) cookies'siz
# "Video unavailable" deb rad etadi (bot/scraping ekanligini aniqlashi sababli).
# Railway'da YT_COOKIES environment variable'iga Netscape formatidagi cookies.txt
# MATNINI (butun faylni) qo'ysangiz, bot uni shu yerda /app/cookies.txt qilib yozadi
# va yt-dlp'ning har bir chaqiruviga avtomatik ulaydi. Qo'yilmasa — avvalgidek ishlaydi
# (cookiesiz), ya'ni bu o'zgarish orqaga mos (backward compatible).
COOKIES_PATH = os.path.join(os.getcwd(), "cookies.txt")
COOKIES_FILE = None


def apply_cookies(content: str) -> bool:
    """Cookie matnini faylga yozib, yt-dlp'ga ulaydi (restart shart emas).
    Bo'sh matn berilsa cookie o'chiriladi."""
    global COOKIES_FILE
    content = (content or "").strip()
    if not content:
        COOKIES_FILE = None
        try:
            os.remove(COOKIES_PATH)
        except OSError:
            pass
        return True
    try:
        with open(COOKIES_PATH, "w", encoding="utf-8") as _f:
            _f.write(content + "\n")
    except OSError:
        return False
    COOKIES_FILE = COOKIES_PATH
    return True


def _load_cookies_on_start():
    # 1) env (YT_COOKIES), 2) /owner panel orqali Mongo'ga saqlangan cookie
    env_content = os.environ.get("YT_COOKIES", "").strip()
    if env_content:
        apply_cookies(env_content)
        return
    try:
        from YukkiMusic.core.mongo import pymongodb

        doc = pymongodb.settings.find_one({"_id": "yt_cookies"})
        if doc and doc.get("content"):
            apply_cookies(doc["content"])
    except Exception:
        pass


_load_cookies_on_start()


def _cookie_opts() -> dict:
    return {"cookiefile": COOKIES_FILE} if COOKIES_FILE else {}


def _extra_opts() -> dict:
    """cookie sozlamasi + 'The page needs to be reloaded' / signature xatolariga qarshi
    keng tarqalgan yechim: YouTube'ning android klientini simulyatsiya qilish — bu klient
    veb-sahifa JS imzosini talab qilmaydi, shu sabab ko'p hollarda bu xatoni chetlab o'tadi."""
    # remote_components: YouTube JS imzo yechuvchi skripti (Deno bilan) — busiz faqat rasmlar chiqadi
    opts = {"remote_components": ["ejs:github"]}
    opts.update(_cookie_opts())
    return opts
from YukkiMusic.utils.database import is_on_off
from YukkiMusic.utils.formatters import time_to_seconds


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if (
            "unavailable videos are hidden"
            in (errorz.decode("utf-8")).lower()
        ):
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
        )

    async def exists(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == "url":
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == "text_link":
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        _cookie_args = ["--cookies", COOKIES_FILE] if COOKIES_FILE else []
        _cookie_args += ["--remote-components", "ejs:github"]
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            *_cookie_args,
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(
        self, link, limit, user_id, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        title = duration_min = vidid = yturl = thumbnail = None
        try:
            results = VideosSearch(link, limit=1)
            search = await results.next()
            result_list = search["result"]
        except Exception as e:
            print(f"[search] VideosSearch failed ({type(e).__name__}: {e}); yt-dlp bilan urinaman")
            result_list = []
        for result in result_list:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        if not result_list:
            # youtube-search-python ishlamasa (YouTube o'zgarsa tez-tez bo'ladi) yt-dlp qidiruviga o'tamiz
            def _search():
                opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "extract_flat": "in_playlist",
                    "noplaylist": True,
                }
                opts.update(_extra_opts())
                q = link if link.startswith("http") else f"ytsearch1:{link}"
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(q, download=False)
                if info and info.get("entries"):
                    info = next((e for e in info["entries"] if e), None)
                return info

            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(None, _search)
            if not info or not info.get("id"):
                raise ValueError(f"No YouTube results found for query: {link!r}")
            sec = int(info.get("duration") or 0)
            h, rem = divmod(sec, 3600)
            m, sc = divmod(rem, 60)
            duration_min = (
                f"{h}:{m:02d}:{sc:02d}" if h else f"{m}:{sc:02d}"
            ) if sec else None
            title = info.get("title") or "Unknown"
            vidid = info["id"]
            yturl = f"https://www.youtube.com/watch?v={vidid}"
            thumbnail = f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg"
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ytdl_opts.update(_extra_opts())
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if not "dash" in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split(
            "?"
        )[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        def _cached(link_):
            # Fayl allaqachon yuklangan bo'lsa, hech narsa so'ramaymiz (bir zumda)
            vid = link_.split("v=")[-1].split("&")[0] if "v=" in link_ else ""
            if vid:
                for ext in ("m4a", "webm", "mp4", "opus", "mp3"):
                    f = os.path.join("downloads", f"{vid}.{ext}")
                    if os.path.exists(f) and os.path.getsize(f) > 0:
                        return f
            return None

        def _sweep_downloads(max_age=12 * 3600):
            # Eskirgan (12 soatdan oshgan) yuklangan fayllar o'chiriladi: disk to'lmaydi
            try:
                now = time.time()
                for f in os.listdir("downloads"):
                    fp = os.path.join("downloads", f)
                    if os.path.isfile(fp) and now - os.path.getmtime(fp) > max_age:
                        os.remove(fp)
            except Exception:
                pass

        def audio_dl():
            _sweep_downloads()
            _t0 = time.time()
            hit = _cached(link)
            if hit:
                print(f"[speed] audio cache hit: {time.time() - _t0:.2f}s")
                return hit
            ydl_optssx = {
                "format": "bestaudio[ext=m4a]/bestaudio/best[ext=mp4]/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "concurrent_fragment_downloads": 4,
                "noprogress": True,
            }
            ydl_optssx.update(_extra_opts())
            x = yt_dlp.YoutubeDL(ydl_optssx)
            # Avval extract_info + keyin download() ikki marta ekstraksiya qilardi; endi bitta
            info = x.extract_info(link, download=True)
            print(f"[speed] audio extract+download: {time.time() - _t0:.1f}s")
            return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        def video_dl():
            hit = _cached(link)
            if hit and hit.endswith(".mp4"):
                return hit
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "concurrent_fragment_downloads": 4,
                "noprogress": True,
            }
            ydl_optssx.update(_extra_opts())
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, download=True)
            return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            ydl_optssx.update(_extra_opts())
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            ydl_optssx.update(_extra_opts())
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            fpath = f"downloads/{title}.mp4"
            return fpath
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            fpath = f"downloads/{title}.mp3"
            return fpath
        elif video:
            if await is_on_off(config.YTDOWNLOADER):
                direct = True
                downloaded_file = await loop.run_in_executor(
                    None, video_dl
                )
            else:
                _cookie_args = ["--cookies", COOKIES_FILE] if COOKIES_FILE else []
                _cookie_args += ["--remote-components", "ejs:github"]
                proc = await asyncio.create_subprocess_exec(
                    "yt-dlp",
                    "-g",
                    "-f",
                    "best[height<=?720][width<=?1280]",
                    *_cookie_args,
                    f"{link}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = None
                else:
                    return
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(
                None, audio_dl
            )
        return downloaded_file, direct
