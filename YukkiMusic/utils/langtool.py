from strings import get_string


async def L(chat_id):
    """Chat tilidagi matnlar lug'atini qaytaradi (xato bo'lsa ruscha)."""
    try:
        from YukkiMusic.utils.database import get_lang

        return get_string(await get_lang(chat_id))
    except Exception:
        return get_string("ru")


def gt(title):
    """Guruh nomini markdown buzmaydigan qilib qaytaradi."""
    return "".join(c for c in str(title or "") if c not in "*_`[]")
