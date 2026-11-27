"""Bot yuboradigan barcha matn va tugmalarni chiroyli (qalin) shriftga o'giradi.

Ikki shrift ishlatiladi:
  * sarlavhalar (qalin ** ** / <b> / <u> ichidagi matn): serif qalin   -> 𝐌𝐞𝐱𝐫𝐨𝐣
  * oddiy matn va tugmalar:                                            -> 𝗠𝗲𝘅𝗿𝗼𝗷
Buyruqlar (/play), @username, havolalar, `kod`, HTML teglari va markdown
belgilari o'zgarmaydi. Natija Telegram chegarasidan oshib ketsa, asl matn
yuboriladi (hech narsa yo'qolmaydi).
"""
import functools
import re

SANS_UP, SANS_LO, SANS_DG = 0x1D5D4, 0x1D5EE, 0x1D7EC  # 𝗔 𝗮 𝟬
SERIF_UP, SERIF_LO, SERIF_DG = 0x1D400, 0x1D41A, 0x1D7CE  # 𝐀 𝐚 𝟎


def _table(up, lo, dg):
    t = {}
    for i in range(26):
        t[ord("A") + i] = chr(up + i)
        t[ord("a") + i] = chr(lo + i)
    for i in range(10):
        t[ord("0") + i] = chr(dg + i)
    return t


SANS = _table(SANS_UP, SANS_LO, SANS_DG)
SERIF = _table(SERIF_UP, SERIF_LO, SERIF_DG)

# O'zgarmasligi kerak bo'lgan bo'laklar
_PROTECT = re.compile(
    r"(```.*?```"  # kod bloki
    r"|`[^`\n]*`"  # inline kod
    r"|<[^>\n]+>"  # HTML teglar
    r"|&[a-zA-Z]+;|&#\d+;"  # HTML entity
    r"|\]\([^)\n]*\)"  # markdown havola manzili
    r"|https?://\S+|tg://\S+|(?<![\w/])t\.me/\S+"  # havolalar
    r"|(?<!\w)@\w+"  # @username
    r"|(?<![\w/])/[A-Za-z_][A-Za-z_0-9]*"  # /buyruq
    r"|\*\*|__|~~|\|\|)",  # markdown belgilari
    re.S,
)
_B_OPEN = re.compile(r"<(b|strong|u)(\s[^>]*)?>", re.I)
_B_CLOSE = re.compile(r"</(b|strong|u)>", re.I)


def _u16(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def stylize(text, limit=4096, heading=True):
    """Matnni chiroyli shriftga o'giradi. Xato yoki limitdan oshsa asl matn."""
    if not text or not isinstance(text, str):
        return text
    try:
        out = []
        bold = False  # qalin (** **, <b>, <u>) ichidamizmi
        for part in _PROTECT.split(text):
            if not part:
                continue
            if _PROTECT.fullmatch(part):
                if part == "**":
                    bold = not bold
                elif _B_OPEN.fullmatch(part):
                    bold = True
                elif _B_CLOSE.fullmatch(part):
                    bold = False
                out.append(part)
                continue
            table = SERIF if (heading and bold) else SANS
            out.append(part.translate(table))
        res = "".join(out)
        if _u16(res) > limit:
            return text
        return res
    except Exception:
        return text


def _wrap(method, idx, kw, limit):
    """Client metodini o'rab, `kw` nomli (yoki idx-pozitsiyadagi) matnni o'giradi."""

    @functools.wraps(method)
    async def wrapper(self, *args, **kwargs):
        if kw in kwargs:
            kwargs[kw] = stylize(kwargs[kw], limit)
        elif len(args) > idx:
            args = list(args)
            args[idx] = stylize(args[idx], limit)
            args = tuple(args)
        return await method(self, *args, **kwargs)

    return wrapper


_installed = False


def install():
    global _installed
    if _installed:
        return
    _installed = True
    from pyrogram import Client
    from pyrogram.types import InlineKeyboardButton

    # (metod, matn parametri pozitsiyasi, nomi, limit)  [self'dan keyin]
    specs = [
        ("send_message", 1, "text", 4096),
        ("edit_message_text", 2, "text", 4096),
        ("edit_message_caption", 2, "caption", 1024),
        ("send_photo", 2, "caption", 1024),
        ("send_video", 2, "caption", 1024),
        ("send_audio", 2, "caption", 1024),
        ("send_document", 2, "caption", 1024),
        ("send_animation", 2, "caption", 1024),
        ("answer_callback_query", 1, "text", 200),
    ]
    for name, idx, kw, limit in specs:
        m = getattr(Client, name, None)
        if m is not None:
            setattr(Client, name, _wrap(m, idx, kw, limit))

    # edit_message_media: InputMedia.caption
    _edit_media = Client.edit_message_media

    @functools.wraps(_edit_media)
    async def edit_message_media(self, chat_id, message_id, media, *a, **k):
        try:
            cap = getattr(media, "caption", None)
            if cap:
                media.caption = stylize(cap, 1024)
        except Exception:
            pass
        return await _edit_media(self, chat_id, message_id, media, *a, **k)

    Client.edit_message_media = edit_message_media

    # Tugmalar matni
    _btn_init = InlineKeyboardButton.__init__

    @functools.wraps(_btn_init)
    def btn_init(self, text, *a, **k):
        _btn_init(self, stylize(text, 64, heading=False), *a, **k)

    InlineKeyboardButton.__init__ = btn_init
