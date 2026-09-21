# -*- coding: utf-8 -*-
"""
dbrestore.py — botga bazani QO'LDA yuklash (restore) va zaxira olish (backup).

Serverni ko'chirganda: eski botdan /backup bilan fayl olinadi, yangi serverdagi
botga o'sha fayl (owner tomonidan) yuboriladi -> bot tekshiradi, tasdiq so'raydi,
bazani almashtiradi va o'zini qayta ishga tushiradi.

Xavfsizlik:
  * faqat OWNER (is_owner) ishlata oladi; boshqalar uchun handler "ko'rinmaydi";
  * fayl avval TEKSHIRILADI (SQLite: integrity_check, Postgres/Mongo: to'liqlik);
  * tiklashdan OLDIN joriy baza nusxasi owner'ga yuboriladi (va SQLite'da diskda
    ham .before_restore_* nomi bilan qoladi);
  * Postgres bitta tranzaksiyada tiklanadi — xato bo'lsa eski baza o'zgarmaydi.

Ulash (aiogram 3):   dbrestore.setup_aiogram(dp, bot, adapter, is_owner)
Ulash (Telethon):    dbrestore.setup_telethon(client, adapter, is_owner)
Ulash (Pyrogram):    dbrestore.setup_pyrogram(app, adapter, is_owner)
Ulash (FastAPI):     dbrestore.Restorer(adapter) — uzen-shop backend'ga qarang.

Telegram Bot API cheklovi: bot faqat <=20MB fayl yuklab oladi. Kattaroq baza uchun
/restore_url <to'g'ridan-to'g'ri havola> ishlatiladi.
"""
from __future__ import annotations

import asyncio
import base64
import datetime as _dt
import decimal
import gzip
import json
import logging
import os
import secrets
import shutil
import sqlite3
import sys
import tempfile
import time
import uuid
from typing import Any, Awaitable, Callable, Iterable, Optional

log = logging.getLogger("dbrestore")

TG_DOWNLOAD_LIMIT = 20 * 1024 * 1024      # Bot API getFile chegarasi
TG_UPLOAD_LIMIT = 49 * 1024 * 1024        # Bot API sendDocument chegarasi (50MB dan kichik)
URL_DOWNLOAD_LIMIT = 2 * 1024 ** 3        # /restore_url uchun maksimal hajm
PENDING_TTL = 15 * 60                     # tasdiqlash uchun kutish vaqti (soniya)
PENDING_DIR = os.path.join(tempfile.gettempdir(), "dbrestore_pending")
WORK_DIR = os.path.join(tempfile.gettempdir(), "dbrestore_work")
PG_FORMAT = "dbrestore-pg-1"
MONGO_FORMAT = "dbrestore-mongo-1"


class RestoreError(Exception):
    """Foydalanuvchiga ko'rsatish mumkin bo'lgan xato matni."""


# ════════════════════════════════════════════════════════════════════
# Yordamchi funksiyalar
# ════════════════════════════════════════════════════════════════════
def _ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _mkdir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _is_gzip(path: str) -> bool:
    with open(path, "rb") as f:
        return f.read(2) == b"\x1f\x8b"


def _open_text(path: str):
    """Oddiy yoki gzip matn faylini o'qish uchun ochadi."""
    if _is_gzip(path):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "rt", encoding="utf-8")


def _gunzip(src: str, dst: str) -> None:
    with gzip.open(src, "rb") as fi, open(dst, "wb") as fo:
        shutil.copyfileobj(fi, fo, 1024 * 1024)


def _gzip_file(src: str, dst: str) -> None:
    with open(src, "rb") as fi, gzip.open(dst, "wb", compresslevel=6) as fo:
        shutil.copyfileobj(fi, fo, 1024 * 1024)


def _q(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _human(n: int) -> str:
    x = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if x < 1024 or unit == "GB":
            return f"{x:.0f} {unit}" if unit == "B" else f"{x:.1f} {unit}"
        x /= 1024
    return f"{n} B"


def _cleanup_old(prefix_path: str, keep: int = 2) -> None:
    """`<baza>.before_restore_*` nusxalaridan oxirgi `keep` tasini qoldiradi."""
    d = os.path.dirname(prefix_path) or "."
    base = os.path.basename(prefix_path) + ".before_restore_"
    try:
        old = sorted(f for f in os.listdir(d) if f.startswith(base))
        for f in old[:-keep] if keep else old:
            try:
                os.remove(os.path.join(d, f))
            except OSError:
                pass
    except OSError:
        pass


# ════════════════════════════════════════════════════════════════════
# Adapter interfeysi
# ════════════════════════════════════════════════════════════════════
class Adapter:
    """Baza turiga xos qism. Har bir adapter 3 ta ish qiladi."""

    label = "baza"
    exts: tuple = ()          # qabul qilinadigan fayl oxirlari (.gz ixtiyoriy)

    def accepts(self, filename: str) -> bool:
        n = (filename or "").lower()
        if n.endswith(".gz"):
            n = n[:-3]
        return any(n.endswith(e) for e in self.exts)

    async def export(self, workdir: str) -> str:            # pragma: no cover
        raise NotImplementedError

    async def validate(self, path: str) -> str:              # pragma: no cover
        raise NotImplementedError

    async def apply(self, path: str) -> None:                # pragma: no cover
        raise NotImplementedError


# ════════════════════════════════════════════════════════════════════
# SQLite (fayl)
# ════════════════════════════════════════════════════════════════════
class SqliteAdapter(Adapter):
    exts = (".db", ".sqlite", ".sqlite3")

    def __init__(self, path: str, *, label: Optional[str] = None,
                 expect_tables: Optional[Iterable[str]] = None):
        self.path = path
        self.label = label or os.path.splitext(os.path.basename(path))[0]
        self.expect_tables = set(expect_tables or [])

    # -- export
    @staticmethod
    def _snapshot(src: str, dst: str) -> None:
        if not os.path.exists(src):
            raise RestoreError("Baza fayli topilmadi.")
        s = sqlite3.connect(src, timeout=30)
        try:
            d = sqlite3.connect(dst)
            try:
                s.backup(d)
            finally:
                d.close()
        finally:
            s.close()

    async def export(self, workdir: str) -> str:
        out = os.path.join(_mkdir(workdir), f"{self.label}_{_ts()}.db")
        await asyncio.to_thread(self._snapshot, self.path, out)
        return out

    # -- validate
    def _validate_sync(self, path: str) -> str:
        with open(path, "rb") as f:
            if f.read(16) != b"SQLite format 3\x00":
                raise RestoreError("Bu SQLite baza fayli emas.")
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
        except sqlite3.Error as e:
            raise RestoreError(f"Faylni ochib bo'lmadi: {e}")
        try:
            try:
                r = con.execute("PRAGMA integrity_check").fetchone()
                tables = [x[0] for x in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            except sqlite3.Error as e:
                raise RestoreError(f"Baza buzilgan: {e}")
            if not r or r[0] != "ok":
                raise RestoreError("Baza buzilgan (integrity_check xato berdi).")
            if not tables:
                raise RestoreError("Bazada hech qanday jadval yo'q.")
            if self.expect_tables and not (self.expect_tables & set(tables)):
                raise RestoreError(
                    "Bu boshqa bot bazasiga o'xshaydi (kutilgan jadvallar: "
                    + ", ".join(sorted(self.expect_tables)[:5]) + ").")
            lines = []
            for t in tables[:12]:
                n = con.execute(f"SELECT COUNT(*) FROM {_q(t)}").fetchone()[0]
                lines.append(f"• {t}: {n}")
            if len(tables) > 12:
                lines.append(f"• … yana {len(tables) - 12} ta jadval")
            return "\n".join(lines)
        finally:
            con.close()

    async def validate(self, path: str) -> str:
        return await asyncio.to_thread(self._validate_sync, path)

    # -- apply
    def _apply_sync(self, path: str) -> None:
        target = os.path.abspath(self.path)
        _mkdir(os.path.dirname(target))
        if os.path.exists(target):
            try:
                self._snapshot(target, f"{target}.before_restore_{_ts()}")
                _cleanup_old(target, keep=2)
            except Exception as e:   # eski nusxa olinmasa ham davom etamiz (owner'ga yuboriladi)
                log.warning("before_restore nusxasi olinmadi: %s", e)
        tmp = target + ".restoring"
        shutil.copyfile(path, tmp)
        for suf in ("-wal", "-shm", "-journal"):
            try:
                os.remove(target + suf)
            except FileNotFoundError:
                pass
        os.replace(tmp, target)

    async def apply(self, path: str) -> None:
        await asyncio.to_thread(self._apply_sync, path)


# ════════════════════════════════════════════════════════════════════
# Postgres (asyncpg) — mantiqiy JSON dump (pg_dump binari kerak emas)
# ════════════════════════════════════════════════════════════════════
_PG_SIMPLE = {"int2", "int4", "int8", "float4", "float8", "numeric", "text", "varchar",
              "bpchar", "bool", "bytea", "date", "time", "timestamp", "timestamptz",
              "uuid", "json", "jsonb", "name"}


def _pg_is_simple(udt: str) -> bool:
    return udt.lstrip("_") in _PG_SIMPLE


def _enc(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, decimal.Decimal):
        return {"$d": str(v)}
    if isinstance(v, _dt.datetime):
        return {"$dt": v.isoformat()}
    if isinstance(v, _dt.date):
        return {"$date": v.isoformat()}
    if isinstance(v, _dt.time):
        return {"$time": v.isoformat()}
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"$b": base64.b64encode(bytes(v)).decode("ascii")}
    if isinstance(v, uuid.UUID):
        return {"$u": str(v)}
    if isinstance(v, (list, tuple)):
        return [_enc(x) for x in v]
    return {"$s": str(v)}


def _dec(v: Any) -> Any:
    if isinstance(v, list):
        return [_dec(x) for x in v]
    if isinstance(v, dict) and len(v) == 1:
        (k, x), = v.items()
        if k == "$d":
            return decimal.Decimal(x)
        if k == "$dt":
            return _dt.datetime.fromisoformat(x)
        if k == "$date":
            return _dt.date.fromisoformat(x)
        if k == "$time":
            return _dt.time.fromisoformat(x)
        if k == "$b":
            return base64.b64decode(x)
        if k == "$u":
            return uuid.UUID(x)
        if k == "$s":
            return x
    return v


def _scan_dump(path: str, fmt: str) -> list:
    """Dump faylini to'liq o'qib chiqadi; [(jadval, ustunlar, qatorlar_soni)] qaytaradi.
    Fayl kesilgan/buzilgan bo'lsa RestoreError."""
    tables: list = []
    cur: Optional[dict] = None
    try:
        with _open_text(path) as f:
            first = f.readline()
            try:
                head = json.loads(first)
            except Exception:
                raise RestoreError("Fayl formati noto'g'ri (bu botning zaxira fayli emas).")
            if not isinstance(head, dict) or head.get("format") != fmt:
                raise RestoreError("Fayl formati mos emas (boshqa turdagi baza zaxirasi).")
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict) and "table" in obj:
                    if cur is not None:
                        raise RestoreError("Fayl buzilgan (jadval yakunlanmagan).")
                    cur = {"name": obj["table"], "columns": obj.get("columns", []), "rows": 0}
                elif isinstance(obj, dict) and "end" in obj:
                    if cur is None or cur["name"] != obj["end"] or cur["rows"] != obj.get("rows"):
                        raise RestoreError("Fayl buzilgan (qatorlar soni mos kelmadi).")
                    tables.append((cur["name"], cur["columns"], cur["rows"]))
                    cur = None
                else:
                    if cur is None:
                        raise RestoreError("Fayl buzilgan (kutilmagan qator).")
                    cur["rows"] += 1
    except (OSError, EOFError, gzip.BadGzipFile) as e:
        raise RestoreError(f"Faylni o'qib bo'lmadi (to'liq yuklanmagan bo'lishi mumkin): {e}")
    except json.JSONDecodeError:
        raise RestoreError("Fayl buzilgan (JSON xato).")
    if cur is not None:
        raise RestoreError("Fayl kesilgan (oxiri yo'q) — qaytadan yuboring.")
    if not tables:
        raise RestoreError("Faylda hech qanday jadval yo'q.")
    return tables


class PgAdapter(Adapter):
    exts = (".dbdump.json",)

    def __init__(self, dsn: str, *, label: str = "postgres", schema: str = "public",
                 exclude: Iterable[str] = ()):
        # SQLAlchemy uslubidagi DSN ni ham qabul qilamiz
        for bad in ("+asyncpg", "+psycopg2", "+psycopg"):
            dsn = dsn.replace(bad, "")
        self.dsn = dsn
        self.label = label
        self.schema = schema
        self.exclude = set(exclude)

    @staticmethod
    def _asyncpg():
        try:
            import asyncpg
            return asyncpg
        except ImportError:
            raise RestoreError("asyncpg o'rnatilmagan (requirements.txt ga 'asyncpg' qo'shing).")

    async def _connect(self):
        return await self._asyncpg().connect(self.dsn, timeout=30)

    async def _tables(self, conn) -> list:
        rows = await conn.fetch(
            "SELECT c.oid, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname=$1 AND c.relkind IN ('r','p') AND NOT c.relispartition "
            "ORDER BY c.relname", self.schema)
        return [(r["oid"], r["relname"]) for r in rows if r["relname"] not in self.exclude]

    async def _ordered_tables(self, conn) -> list:
        """FK bo'yicha: ota jadvallar avval (dump va tiklash tartibi)."""
        tables = await self._tables(conn)
        by_oid = {oid: name for oid, name in tables}
        deps: dict = {oid: set() for oid in by_oid}
        for r in await conn.fetch("SELECT conrelid, confrelid FROM pg_constraint WHERE contype='f'"):
            a, b = r["conrelid"], r["confrelid"]
            if a in deps and b in by_oid and a != b:
                deps[a].add(b)
        out, done = [], set()
        pending = sorted(by_oid, key=lambda o: by_oid[o])
        while pending:
            progressed = False
            for oid in list(pending):
                if deps[oid] <= done:
                    out.append((oid, by_oid[oid]))
                    done.add(oid)
                    pending.remove(oid)
                    progressed = True
            if not progressed:          # sikl (o'ziga bog'liq FK'lar) — qolganini shundayligicha qo'shamiz
                for oid in pending:
                    out.append((oid, by_oid[oid]))
                break
        return out

    async def _cols(self, conn, oid) -> list:
        rows = await conn.fetch(
            "SELECT a.attname AS name, t.typname AS udt, "
            "(a.attgenerated <> '') AS generated "
            "FROM pg_attribute a JOIN pg_type t ON t.oid=a.atttypid "
            "WHERE a.attrelid=$1 AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum", oid)
        return [dict(r) for r in rows]

    # -- export
    async def export(self, workdir: str) -> str:
        out = os.path.join(_mkdir(workdir), f"{self.label}_{_ts()}.dbdump.json.gz")
        conn = await self._connect()
        try:
            async with conn.transaction(isolation="repeatable_read", readonly=True):
                tables = await self._ordered_tables(conn)
                if not tables:
                    raise RestoreError("Bazada hech qanday jadval yo'q.")
                with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
                    f.write(json.dumps({"format": PG_FORMAT, "label": self.label,
                                        "created": _dt.datetime.now(_dt.timezone.utc).isoformat()}) + "\n")
                    for oid, name in tables:
                        cols = [c for c in await self._cols(conn, oid) if not c["generated"]]
                        if not cols:
                            continue
                        sel = ", ".join(_q(c["name"]) if _pg_is_simple(c["udt"])
                                        else f'{_q(c["name"])}::text AS {_q(c["name"])}' for c in cols)
                        f.write(json.dumps({"table": name, "columns": [
                            {"name": c["name"], "udt": c["udt"], "simple": _pg_is_simple(c["udt"])}
                            for c in cols]}) + "\n")
                        n = 0
                        async for rec in conn.cursor(f"SELECT {sel} FROM {_q(self.schema)}.{_q(name)}",
                                                     prefetch=1000):
                            f.write(json.dumps([_enc(v) for v in rec.values()],
                                               separators=(",", ":"), ensure_ascii=False) + "\n")
                            n += 1
                            if n % 2000 == 0:
                                await asyncio.sleep(0)
                        f.write(json.dumps({"end": name, "rows": n}) + "\n")
        except BaseException:
            try:
                os.remove(out)
            except OSError:
                pass
            raise
        finally:
            await conn.close()
        return out

    # -- validate
    async def validate(self, path: str) -> str:
        tables = await asyncio.to_thread(_scan_dump, path, PG_FORMAT)
        conn = await self._connect()
        try:
            existing = {n for _, n in await self._tables(conn)}
        finally:
            await conn.close()
        common = [t for t in tables if t[0] in existing]
        if not common:
            raise RestoreError(
                "Fayldagi jadvallar bu bazada topilmadi — bu boshqa bot zaxirasi bo'lishi mumkin "
                "(yoki bot hali jadvallarni yaratmagan).")
        lines = [f"• {n}: {rows}" for n, _, rows in common[:12]]
        if len(common) > 12:
            lines.append(f"• … yana {len(common) - 12} ta jadval")
        missing = [t[0] for t in tables if t[0] not in existing]
        if missing:
            lines.append("⚠️ Bu jadvallar bazada yo'q, o'tkazib yuboriladi: " + ", ".join(missing[:8]))
        return "\n".join(lines)

    # -- apply
    async def apply(self, path: str) -> None:
        tables = await asyncio.to_thread(_scan_dump, path, PG_FORMAT)
        conn = await self._connect()
        try:
            targets = {name: oid for oid, name in await self._ordered_tables(conn)}
            common = [t for t in tables if t[0] in targets]
            if not common:
                raise RestoreError("Fayldagi jadvallar bazada topilmadi.")
            common_names = {t[0] for t in common}
            async with conn.transaction():
                await conn.execute("SET LOCAL lock_timeout = '30s'")
                try:                                   # FK tekshiruvini vaqtincha o'chirish (superuser bo'lsa)
                    async with conn.transaction():
                        await conn.execute("SET LOCAL session_replication_role = replica")
                except Exception:
                    log.info("session_replication_role ruxsati yo'q — FK tartibi bo'yicha tiklanadi")
                await conn.execute("TRUNCATE " + ", ".join(f"{_q(self.schema)}.{_q(n)}" for n in
                                                          [t[0] for t in common]) + " RESTART IDENTITY CASCADE")
                await self._load(conn, path, targets, common_names)
                await self._fix_sequences(conn, [t[0] for t in common])
        finally:
            await conn.close()

    async def _load(self, conn, path: str, targets: dict, common_names: set) -> None:
        f = _open_text(path)
        try:
            f.readline()  # header
            sql = None
            keep: list = []
            casts: list = []
            batch: list = []

            async def flush():
                nonlocal batch
                if batch and sql:
                    await conn.executemany(sql, batch)
                batch = []

            skip = False
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict) and "table" in obj:
                    name = obj["table"]
                    skip = name not in common_names
                    if skip:
                        sql = None
                        continue
                    tcols = {c["name"]: c for c in await self._cols(conn, targets[name])
                             if not c["generated"]}
                    dump_cols = obj["columns"]
                    keep = [i for i, c in enumerate(dump_cols) if c["name"] in tcols]
                    casts = [tcols[dump_cols[i]["name"]]["udt"] for i in keep]
                    if not keep:
                        skip = True
                        sql = None
                        continue
                    ph = []
                    for n, udt in enumerate(casts, 1):
                        ph.append(f"${n}" if _pg_is_simple(udt) else f'${n}::text::{_q(udt)}')
                    sql = (f"INSERT INTO {_q(self.schema)}.{_q(name)} "
                           f"({', '.join(_q(dump_cols[i]['name']) for i in keep)}) "
                           f"OVERRIDING SYSTEM VALUE VALUES ({', '.join(ph)})")
                elif isinstance(obj, dict) and "end" in obj:
                    await flush()
                    skip = False
                    sql = None
                elif not skip and sql:
                    row = []
                    for pos, i in enumerate(keep):
                        v = _dec(obj[i])
                        if v is not None and not _pg_is_simple(casts[pos]) and not isinstance(v, str):
                            v = str(v)
                        row.append(v)
                    batch.append(row)
                    if len(batch) >= 500:
                        await flush()
        finally:
            f.close()

    async def _fix_sequences(self, conn, names: list) -> None:
        for name in names:
            qual = f"{_q(self.schema)}.{_q(name)}"
            oid = await conn.fetchval("SELECT $1::text::regclass::oid", qual)
            for c in await self._cols(conn, oid):
                seq = await conn.fetchval("SELECT pg_get_serial_sequence($1, $2)", qual, c["name"])
                if not seq:
                    continue
                mx = await conn.fetchval(f"SELECT MAX({_q(c['name'])}) FROM {qual}")
                await conn.fetchval("SELECT setval($1::text::regclass, $2, $3)",
                                    seq, int(mx) if mx else 1, bool(mx))


# ════════════════════════════════════════════════════════════════════
# MongoDB (motor)
# ════════════════════════════════════════════════════════════════════
class MongoAdapter(Adapter):
    exts = (".dbdump.json",)

    def __init__(self, uri: str, db_name: str, *, label: Optional[str] = None):
        self.uri = uri
        self.db_name = db_name
        self.label = label or db_name

    def _client(self):
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError:
            raise RestoreError("motor o'rnatilmagan.")
        return AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=15000)

    async def export(self, workdir: str) -> str:
        from bson import json_util
        out = os.path.join(_mkdir(workdir), f"{self.label}_{_ts()}.dbdump.json.gz")
        client = self._client()
        try:
            db = client[self.db_name]
            names = sorted(n for n in await db.list_collection_names() if not n.startswith("system."))
            if not names:
                raise RestoreError("Bazada hech qanday collection yo'q.")
            with gzip.open(out, "wt", encoding="utf-8", compresslevel=6) as f:
                f.write(json.dumps({"format": MONGO_FORMAT, "label": self.label,
                                    "created": _dt.datetime.now(_dt.timezone.utc).isoformat()}) + "\n")
                for name in names:
                    coll = db[name]
                    idx = []
                    for iname, info in (await coll.index_information()).items():
                        if iname == "_id_":
                            continue
                        opts = {k: info[k] for k in ("unique", "sparse", "expireAfterSeconds",
                                                     "partialFilterExpression") if k in info}
                        idx.append({"name": iname, "key": [list(k) for k in info["key"]], "options": opts})
                    f.write(json_util.dumps({"table": name, "columns": [], "indexes": idx}) + "\n")
                    n = 0
                    async for doc in coll.find({}):
                        f.write(json_util.dumps([doc]) + "\n")
                        n += 1
                        if n % 2000 == 0:
                            await asyncio.sleep(0)
                    f.write(json.dumps({"end": name, "rows": n}) + "\n")
        except BaseException:
            try:
                os.remove(out)
            except OSError:
                pass
            raise
        finally:
            client.close()
        return out

    async def validate(self, path: str) -> str:
        tables = await asyncio.to_thread(_scan_dump, path, MONGO_FORMAT)
        return "\n".join(f"• {n}: {rows}" for n, _, rows in tables[:14])

    async def apply(self, path: str) -> None:
        from bson import json_util
        await asyncio.to_thread(_scan_dump, path, MONGO_FORMAT)   # avval to'liq tekshiriladi
        client = self._client()
        try:
            db = client[self.db_name]
            f = _open_text(path)
            try:
                f.readline()
                coll = None
                batch: list = []
                indexes: list = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json_util.loads(line)
                    if isinstance(obj, dict) and "table" in obj:
                        coll = db[obj["table"]]
                        await coll.drop()
                        batch, indexes = [], obj.get("indexes", [])
                    elif isinstance(obj, dict) and "end" in obj:
                        if batch:
                            await coll.insert_many(batch, ordered=False)
                            batch = []
                        for ix in indexes:
                            try:
                                await coll.create_index([tuple(k) for k in ix["key"]], name=ix["name"],
                                                        **ix.get("options", {}))
                            except Exception as e:
                                log.warning("index %s tiklanmadi: %s", ix.get("name"), e)
                        coll = None
                    elif isinstance(obj, list) and coll is not None:
                        batch.append(obj[0])
                        if len(batch) >= 500:
                            await coll.insert_many(batch, ordered=False)
                            batch = []
            finally:
                f.close()
        finally:
            client.close()


def adapter_from_url(url: str, *, label: str = "baza", expect_tables: Optional[Iterable[str]] = None) -> Adapter:
    """DATABASE_URL ga qarab SQLite yoki Postgres adapterini tanlaydi."""
    u = (url or "").strip()
    low = u.lower()
    if low.startswith("sqlite"):
        path = u.split(":///", 1)[1] if ":///" in u else u.split("://", 1)[-1]
        return SqliteAdapter(path, label=label, expect_tables=expect_tables)
    if low.startswith(("postgres", "postgresql")):
        return PgAdapter(u, label=label)
    raise RestoreError(f"Noma'lum baza turi: {u.split(':', 1)[0]}")


# ════════════════════════════════════════════════════════════════════
# Restorer — framework'dan mustaqil oqim: stage -> commit
# ════════════════════════════════════════════════════════════════════
class Restorer:
    def __init__(self, adapter: Adapter):
        self.adapter = adapter

    # -- backup
    async def make_backup(self) -> tuple:
        """(fayl_yo'li, izoh) — Telegram'ga yuborishga tayyor (kerak bo'lsa gzip)."""
        _mkdir(WORK_DIR)
        path = await self.adapter.export(WORK_DIR)
        if os.path.getsize(path) > TG_UPLOAD_LIMIT and not path.endswith(".gz"):
            gz = path + ".gz"
            await asyncio.to_thread(_gzip_file, path, gz)
            os.remove(path)
            path = gz
        size = os.path.getsize(path)
        if size > TG_UPLOAD_LIMIT:
            os.remove(path)
            raise RestoreError(
                f"Baza juda katta ({_human(size)}) — Telegram orqali yuborib bo'lmaydi "
                f"(chegara ~50MB). Bazani server orqali ko'chiring.")
        cap = (f"💾 {self.adapter.label} zaxirasi ({_human(size)})\n"
               f"Yangi serverda botga shu faylni yuboring — bot o'zi tiklaydi.")
        return path, cap

    # -- pending
    @staticmethod
    def _purge_pending() -> None:
        _mkdir(PENDING_DIR)
        now = time.time()
        for d in os.listdir(PENDING_DIR):
            p = os.path.join(PENDING_DIR, d)
            try:
                if now - os.path.getmtime(p) > PENDING_TTL:
                    shutil.rmtree(p, ignore_errors=True)
            except OSError:
                pass

    async def stage(self, src_path: str, uid: int, filename: str) -> tuple:
        """Faylni tekshiradi va tasdiq kutish holatiga qo'yadi. (token, xulosa)."""
        if not self.adapter.accepts(filename):
            raise RestoreError("Bu fayl turi mos emas: " + ", ".join(self.adapter.exts) + " (yoki .gz)")
        self._purge_pending()
        token = secrets.token_hex(6)
        d = _mkdir(os.path.join(PENDING_DIR, token))
        data = os.path.join(d, "data")
        try:
            if _is_gzip(src_path) and self.adapter.exts == SqliteAdapter.exts:
                await asyncio.to_thread(_gunzip, src_path, data)     # sqlite: ochib qo'yamiz
            else:
                await asyncio.to_thread(shutil.copyfile, src_path, data)
            summary = await self.adapter.validate(data)
        except BaseException:
            shutil.rmtree(d, ignore_errors=True)
            raise
        with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
            json.dump({"uid": uid, "name": filename, "ts": time.time()}, f)
        return token, summary

    def _load_pending(self, token: str, uid: int) -> str:
        if not token or not all(c in "0123456789abcdef" for c in token):
            raise RestoreError("Noto'g'ri so'rov.")
        d = os.path.join(PENDING_DIR, token)
        try:
            with open(os.path.join(d, "meta.json"), encoding="utf-8") as f:
                meta = json.load(f)
        except OSError:
            raise RestoreError("So'rov eskirgan yoki topilmadi — faylni qaytadan yuboring.")
        if meta.get("uid") != uid:
            raise RestoreError("Bu so'rov boshqa foydalanuvchiga tegishli.")
        if time.time() - meta.get("ts", 0) > PENDING_TTL:
            shutil.rmtree(d, ignore_errors=True)
            raise RestoreError("So'rov eskirgan (15 daqiqadan oshdi) — faylni qaytadan yuboring.")
        return os.path.join(d, "data")

    def cancel(self, token: str) -> None:
        if token and all(c in "0123456789abcdef" for c in token):
            shutil.rmtree(os.path.join(PENDING_DIR, token), ignore_errors=True)

    async def commit(self, token: str, uid: int,
                     send_safety_copy: Optional[Callable[[str, str], Awaitable[None]]] = None) -> None:
        """Tiklaydi. Avval joriy bazaning nusxasini (send_safety_copy orqali) yuboradi."""
        data = self._load_pending(token, uid)
        if send_safety_copy is not None:
            try:
                path, _ = await self.make_backup()
                try:
                    await send_safety_copy(path, "🛟 Tiklashdan OLDINGI baza nusxasi (kerak bo'lib qolsa saqlab qo'ying).")
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            except Exception as e:      # bo'sh/katta baza — to'xtatmaymiz
                log.info("Tiklashdan oldingi nusxa yuborilmadi: %s", e)
        await self.adapter.apply(data)
        self.cancel(token)


# ════════════════════════════════════════════════════════════════════
# Qayta ishga tushirish
# ════════════════════════════════════════════════════════════════════
def restart_process() -> None:
    """Jarayonni o'sha PID bilan qayta ishga tushiradi (Railway/supervisor uchun xavfsiz)."""
    argv = list(getattr(sys, "orig_argv", None) or ([sys.executable] + sys.argv))
    log.warning("Qayta ishga tushirilmoqda: %s", argv)
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os.execv(sys.executable, argv)


async def _download_url(url: str, dst: str) -> str:
    """Havoladan faylni yuklaydi, fayl nomini qaytaradi."""
    try:
        import aiohttp
    except ImportError:
        raise RestoreError("aiohttp o'rnatilmagan.")
    if not url.lower().startswith(("http://", "https://")):
        raise RestoreError("Havola http(s):// bilan boshlanishi kerak.")
    timeout = aiohttp.ClientTimeout(total=60 * 30, connect=30)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url, allow_redirects=True) as r:
            if r.status != 200:
                raise RestoreError(f"Havola javobi: HTTP {r.status}")
            size = 0
            with open(dst, "wb") as f:
                async for chunk in r.content.iter_chunked(1024 * 256):
                    size += len(chunk)
                    if size > URL_DOWNLOAD_LIMIT:
                        raise RestoreError("Fayl juda katta (>2GB).")
                    f.write(chunk)
            cd = r.headers.get("Content-Disposition", "")
            name = ""
            if "filename=" in cd:
                name = cd.split("filename=", 1)[1].strip().strip('"; ')
            if not name:
                name = os.path.basename(str(r.url.path)) or "download"
            return name


# ════════════════════════════════════════════════════════════════════
# aiogram 3 ulanishi
# ════════════════════════════════════════════════════════════════════
HELP_TEXT = (
    "💾 <b>Baza zaxirasi / tiklash</b>\n\n"
    "• <code>/{bk}</code> — hozirgi bazani fayl qilib yuboradi\n"
    "• Tiklash: zaxira faylini shu botga <b>hujjat (document)</b> sifatida yuboring\n"
    "• Fayl 20MB dan katta bo'lsa: <code>/restore_url https://…</code>\n\n"
    "Bot faylni tekshiradi, tasdiq so'raydi, bazani almashtiradi va o'zini qayta ishga tushiradi."
)


MENU_TEXT = "💾 <b>Baza</b>\n\nKerakli amalni tanlang:"
UP_TEXT = ("📥 <b>Bazani yuklash</b>\n\nZaxira faylini shu chatga <b>hujjat (document)</b> sifatida yuboring.\n"
           "Fayl 20MB dan katta bo'lsa: <code>/restore_url https://…</code>")
BUTTON_TEXT = "💾 Baza (yuklash / olish)"


def aiogram_button(text: str = BUTTON_TEXT):
    """Owner panelidagi klaviaturaga qo'shish uchun tugma (aiogram)."""
    from aiogram.types import InlineKeyboardButton
    return InlineKeyboardButton(text=text, callback_data="dbrestore:menu")


def telethon_button(text: str = BUTTON_TEXT):
    from telethon import Button
    return Button.inline(text, data=b"dbrestore:menu")


def pyrogram_button(text: str = BUTTON_TEXT):
    from pyrogram.types import InlineKeyboardButton
    return InlineKeyboardButton(text, callback_data="dbrestore:menu")


def setup_aiogram(dp, bot, adapter: Adapter, is_owner: Callable[[int], bool], *,
                  backup_cmd: bool = True, help_cmd: bool = True, backup_command: str = "backup",
                  before_restart: Optional[Callable[[], Awaitable[None]]] = None) -> Restorer:
    """dp ga handlerlarni RO'YXATDAN O'TKAZADI. Boshqa handlerlardan OLDIN chaqiring
    (dp yaratilgandan keyin darhol) — shunda fayl boshqa handlerga tushib qolmaydi."""
    from aiogram import F
    from aiogram.filters import Command
    from aiogram.types import (BufferedInputFile, CallbackQuery, FSInputFile,
                               InlineKeyboardButton, InlineKeyboardMarkup, Message)

    rs = Restorer(adapter)

    def owner_msg(m: Message) -> bool:
        return bool(m.from_user) and m.chat.type == "private" and is_owner(m.from_user.id)

    def owner_doc(m: Message) -> bool:
        return owner_msg(m) and bool(m.document) and adapter.accepts(m.document.file_name or "")

    def owner_cb(c: CallbackQuery) -> bool:
        return bool(c.from_user) and is_owner(c.from_user.id)

    def confirm_kb(token: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tiklash", callback_data=f"dbrestore:yes:{token}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data=f"dbrestore:no:{token}"),
        ]])

    def menu_kb() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Bazani yuklash (tiklash)", callback_data="dbrestore:up")],
            [InlineKeyboardButton(text="📤 Bazani yuklab olish", callback_data="dbrestore:get")]])

    async def _stage_and_ask(m: Message, path: str, name: str):
        try:
            token, summary = await rs.stage(path, m.from_user.id, name)
        except RestoreError as e:
            await m.answer(f"❌ {e}")
            return
        except Exception as e:
            log.exception("stage xato")
            await m.answer(f"❌ Faylni tekshirishda xato: {e}")
            return
        await m.answer(
            "📦 <b>Fayl tekshirildi</b>\n" + summary +
            "\n\n⚠️ Joriy baza <b>shu fayl bilan almashtiriladi</b>. "
            "Tiklashdan oldin joriy baza nusxasi sizga yuboriladi.\nDavom etamizmi?",
            parse_mode="HTML", reply_markup=confirm_kb(token))

    async def on_menu(m: Message):
        await m.answer(MENU_TEXT, parse_mode="HTML", reply_markup=menu_kb())

    async def on_backup(m: Message):
        await _send_backup(m)

    async def _send_backup(m: Message):
        wait = await m.answer("⏳ Zaxira tayyorlanmoqda...")
        try:
            path, cap = await rs.make_backup()
        except RestoreError as e:
            await wait.edit_text(f"❌ {e}")
            return
        except Exception as e:
            log.exception("backup xato")
            await wait.edit_text(f"❌ Zaxira olishda xato: {e}")
            return
        try:
            await m.answer_document(FSInputFile(path), caption=cap)
            await wait.delete()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    async def on_help(m: Message):
        await m.answer(HELP_TEXT.format(bk=backup_command), parse_mode="HTML")

    async def on_document(m: Message):
        d = m.document
        if d.file_size and d.file_size > TG_DOWNLOAD_LIMIT:
            await m.answer("❌ Fayl 20MB dan katta — Telegram bot uni yuklab ololmaydi.\n"
                           "Faylni biror joyga (masalan GitHub Release) yuklab, "
                           "<code>/restore_url https://…</code> deb yuboring.", parse_mode="HTML")
            return
        tmp = os.path.join(_mkdir(WORK_DIR), f"up_{secrets.token_hex(4)}_{os.path.basename(d.file_name or 'x')}")
        try:
            await bot.download(d, destination=tmp)
            await _stage_and_ask(m, tmp, d.file_name or "")
        except Exception as e:
            log.exception("yuklab olish xato")
            await m.answer(f"❌ Faylni yuklab olib bo'lmadi: {e}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    async def on_url(m: Message):
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await m.answer("Havolani yozing: <code>/restore_url https://…</code>", parse_mode="HTML")
            return
        wait = await m.answer("⏳ Fayl yuklanmoqda...")
        tmp = os.path.join(_mkdir(WORK_DIR), f"url_{secrets.token_hex(4)}")
        try:
            name = await _download_url(parts[1].strip(), tmp)
            if not adapter.accepts(name):        # nomi noaniq bo'lsa, turini kontent bo'yicha aniqlaymiz
                name = name if name else "download"
                if _is_gzip(tmp) or open(tmp, "rb").read(16) == b"SQLite format 3\x00":
                    name = name + (adapter.exts[0] if not name.lower().endswith(adapter.exts) else "")
            await wait.delete()
            await _stage_and_ask(m, tmp, name)
        except RestoreError as e:
            await wait.edit_text(f"❌ {e}")
        except Exception as e:
            log.exception("restore_url xato")
            await wait.edit_text(f"❌ Yuklab bo'lmadi: {e}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    async def on_cb(c: CallbackQuery):
        parts = (c.data or "").split(":", 2)
        action = parts[1] if len(parts) > 1 else ""
        token = parts[2] if len(parts) > 2 else ""
        if action == "menu":
            await c.answer()
            await c.message.answer(MENU_TEXT, parse_mode="HTML", reply_markup=menu_kb())
            return
        if action == "up":
            await c.answer()
            await c.message.answer(UP_TEXT, parse_mode="HTML")
            return
        if action == "get":
            await c.answer("Zaxira tayyorlanmoqda...")
            await _send_backup(c.message)
            return
        if action == "no":
            rs.cancel(token)
            await c.answer("Bekor qilindi")
            await c.message.edit_text("❌ Tiklash bekor qilindi.")
            return
        if action != "yes":
            await c.answer()
            return
        try:
            rs._load_pending(token, c.from_user.id)
        except RestoreError as e:
            await c.answer(str(e), show_alert=True)
            return
        await c.answer()
        await c.message.edit_text("⏳ Tiklanmoqda... (avval joriy baza nusxasi yuboriladi)")

        async def safety(path: str, caption: str):
            await bot.send_document(c.from_user.id, FSInputFile(path), caption=caption)

        try:
            await rs.commit(token, c.from_user.id, safety)
        except RestoreError as e:
            await c.message.edit_text(f"❌ Tiklab bo'lmadi: {e}\nJoriy baza o'zgarmadi.")
            return
        except Exception as e:
            log.exception("commit xato")
            await c.message.edit_text(f"❌ Tiklab bo'lmadi: {e}\nJoriy baza o'zgarmadi.")
            return
        await c.message.edit_text("✅ <b>Baza tiklandi.</b> Bot qayta ishga tushmoqda (5–15 soniya)...",
                                  parse_mode="HTML")
        await asyncio.sleep(1.5)
        try:
            if before_restart is not None:
                await before_restart()
        except Exception:
            log.exception("before_restart xato")
        try:
            await bot.session.close()
        except Exception:
            pass
        restart_process()

    reg = dp.message.register
    reg(on_document, F.document, owner_doc)
    reg(on_url, Command("restore_url"), owner_msg)
    reg(on_menu, Command("baza"), owner_msg)
    if backup_cmd:
        reg(on_backup, Command(backup_command), owner_msg)
    if help_cmd:
        reg(on_help, Command("restore"), owner_msg)
    dp.callback_query.register(on_cb, F.data.startswith("dbrestore:"), owner_cb)

    async def on_cb_denied(c: CallbackQuery):
        await c.answer("Bu tugma faqat owner uchun.", show_alert=True)

    dp.callback_query.register(on_cb_denied, F.data.startswith("dbrestore:"))
    return rs


# ════════════════════════════════════════════════════════════════════
# Telethon ulanishi
# ════════════════════════════════════════════════════════════════════
def setup_telethon(client, adapter: Adapter, is_owner: Callable[[int], bool], *,
                   backup_cmd: bool = True) -> Restorer:
    from telethon import Button, events

    rs = Restorer(adapter)

    def _owner_event(e) -> bool:
        return bool(e.is_private and e.sender_id and is_owner(e.sender_id))

    async def _stage_and_ask(event, path: str, name: str):
        try:
            token, summary = await rs.stage(path, event.sender_id, name)
        except RestoreError as e:
            await event.respond(f"❌ {e}")
            return
        except Exception as e:
            log.exception("stage xato")
            await event.respond(f"❌ Faylni tekshirishda xato: {e}")
            return
        await event.respond(
            "📦 **Fayl tekshirildi**\n" + summary +
            "\n\n⚠️ Joriy baza **shu fayl bilan almashtiriladi**. "
            "Tiklashdan oldin joriy baza nusxasi sizga yuboriladi.\nDavom etamizmi?",
            buttons=[[Button.inline("✅ Tiklash", data=f"dbrestore:yes:{token}".encode()),
                      Button.inline("❌ Bekor", data=f"dbrestore:no:{token}".encode())]])

    def _md(t: str) -> str:
        return t.replace("<b>", "**").replace("</b>", "**").replace("<code>", "`").replace("</code>", "`")

    def _menu_buttons():
        return [[Button.inline("📥 Bazani yuklash (tiklash)", data=b"dbrestore:up")],
                [Button.inline("📤 Bazani yuklab olish", data=b"dbrestore:get")]]

    async def _send_backup(event):
        wait = await event.respond("⏳ Zaxira tayyorlanmoqda...")
        try:
            path, cap = await rs.make_backup()
        except RestoreError as e:
            await wait.edit(f"❌ {e}")
            return
        except Exception as e:
            log.exception("backup xato")
            await wait.edit(f"❌ Zaxira olishda xato: {e}")
            return
        try:
            await client.send_file(event.chat_id, path, caption=cap, force_document=True)
            await wait.delete()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    @client.on(events.NewMessage(incoming=True, pattern=r"^/baza(@\w+)?\s*$"))
    async def _menu(event):
        if _owner_event(event):
            await event.respond(_md(MENU_TEXT), buttons=_menu_buttons())
            raise events.StopPropagation

    if backup_cmd:
        @client.on(events.NewMessage(incoming=True, pattern=r"^/backup(@\w+)?\s*$"))
        async def _backup(event):
            if not _owner_event(event):
                return
            await _send_backup(event)
            raise events.StopPropagation

    @client.on(events.NewMessage(incoming=True, pattern=r"^/restore(@\w+)?\s*$"))
    async def _help(event):
        if _owner_event(event):
            await event.respond(HELP_TEXT.format(bk="backup").replace("<b>", "**").replace("</b>", "**")
                                .replace("<code>", "`").replace("</code>", "`"))
            raise events.StopPropagation

    @client.on(events.NewMessage(incoming=True, func=lambda e: bool(e.document)))
    async def _doc(event):
        if not _owner_event(event):
            return
        name = ""
        for a in event.document.attributes:
            if getattr(a, "file_name", None):
                name = a.file_name
        if not adapter.accepts(name):
            return
        if event.document.size and event.document.size > TG_DOWNLOAD_LIMIT * 10:
            await event.respond("❌ Fayl juda katta. `/restore_url https://…` dan foydalaning.")
            return
        tmp = os.path.join(_mkdir(WORK_DIR), f"up_{secrets.token_hex(4)}_{os.path.basename(name)}")
        try:
            await event.download_media(file=tmp)
            await _stage_and_ask(event, tmp, name)
        except Exception as e:
            log.exception("yuklab olish xato")
            await event.respond(f"❌ Faylni yuklab olib bo'lmadi: {e}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise events.StopPropagation

    @client.on(events.NewMessage(incoming=True, pattern=r"^/restore_url\s+(\S+)"))
    async def _url(event):
        if not _owner_event(event):
            return
        url = event.pattern_match.group(1)
        wait = await event.respond("⏳ Fayl yuklanmoqda...")
        tmp = os.path.join(_mkdir(WORK_DIR), f"url_{secrets.token_hex(4)}")
        try:
            name = await _download_url(url, tmp)
            if not adapter.accepts(name):
                if _is_gzip(tmp) or open(tmp, "rb").read(16) == b"SQLite format 3\x00":
                    name = (name or "download") + adapter.exts[0]
            await wait.delete()
            await _stage_and_ask(event, tmp, name)
        except RestoreError as e:
            await wait.edit(f"❌ {e}")
        except Exception as e:
            log.exception("restore_url xato")
            await wait.edit(f"❌ Yuklab bo'lmadi: {e}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise events.StopPropagation

    @client.on(events.CallbackQuery(pattern=rb"^dbrestore:"))
    async def _cb(event):
        if not (event.sender_id and is_owner(event.sender_id)):
            await event.answer("Bu tugma faqat owner uchun.", alert=True)
            return
        parts = event.data.decode().split(":", 2)
        action = parts[1] if len(parts) > 1 else ""
        token = parts[2] if len(parts) > 2 else ""
        if action == "menu":
            await event.answer()
            await event.respond(_md(MENU_TEXT), buttons=_menu_buttons())
            return
        if action == "up":
            await event.answer()
            await event.respond(_md(UP_TEXT))
            return
        if action == "get":
            await event.answer("Zaxira tayyorlanmoqda...")
            await _send_backup(event)
            return
        if action == "no":
            rs.cancel(token)
            await event.edit("❌ Tiklash bekor qilindi.")
            return
        if action != "yes":
            return
        try:
            rs._load_pending(token, event.sender_id)
        except RestoreError as e:
            await event.answer(str(e), alert=True)
            return
        await event.edit("⏳ Tiklanmoqda... (avval joriy baza nusxasi yuboriladi)")

        async def safety(path: str, caption: str):
            await client.send_file(event.sender_id, path, caption=caption, force_document=True)

        try:
            await rs.commit(token, event.sender_id, safety)
        except Exception as e:
            log.exception("commit xato")
            await event.edit(f"❌ Tiklab bo'lmadi: {e}\nJoriy baza o'zgarmadi.")
            return
        await event.edit("✅ **Baza tiklandi.** Bot qayta ishga tushmoqda (5–15 soniya)...")
        await asyncio.sleep(1.5)
        try:
            await client.disconnect()
        except Exception:
            pass
        restart_process()

    return rs


# ════════════════════════════════════════════════════════════════════
# Pyrogram ulanishi
# ════════════════════════════════════════════════════════════════════
def setup_pyrogram(app, adapter: Adapter, is_owner: Callable[[int], bool], *,
                   backup_cmd: bool = True, group: int = -100) -> Restorer:
    from pyrogram import StopPropagation, filters
    from pyrogram.handlers import CallbackQueryHandler, MessageHandler
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rs = Restorer(adapter)

    async def _owner_f(_, __, m):
        if not (m.from_user and m.chat):
            return False
        ct = getattr(m.chat.type, "name", m.chat.type)      # Pyrogram 2: enum, Pyrogram 1.x: str
        return str(ct).upper() == "PRIVATE" and is_owner(m.from_user.id)

    owner_f = filters.create(_owner_f)

    async def _doc_f(_, __, m):
        return bool(m.document) and adapter.accepts(m.document.file_name or "")

    doc_f = filters.create(_doc_f)

    async def _cb_owner(_, __, q):
        return bool(q.from_user) and is_owner(q.from_user.id)

    cb_owner_f = filters.create(_cb_owner)

    async def _stage_and_ask(m, path: str, name: str):
        try:
            token, summary = await rs.stage(path, m.from_user.id, name)
        except RestoreError as e:
            await m.reply_text(f"❌ {e}")
            return
        except Exception as e:
            log.exception("stage xato")
            await m.reply_text(f"❌ Faylni tekshirishda xato: {e}")
            return
        await m.reply_text(
            "📦 **Fayl tekshirildi**\n" + summary +
            "\n\n⚠️ Joriy baza **shu fayl bilan almashtiriladi**. "
            "Tiklashdan oldin joriy baza nusxasi sizga yuboriladi.\nDavom etamizmi?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Tiklash", callback_data=f"dbrestore:yes:{token}"),
                InlineKeyboardButton("❌ Bekor", callback_data=f"dbrestore:no:{token}")]]))

    def _md(t: str) -> str:
        return t.replace("<b>", "**").replace("</b>", "**").replace("<code>", "`").replace("</code>", "`")

    def _menu_kb():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Bazani yuklash (tiklash)", callback_data="dbrestore:up")],
            [InlineKeyboardButton("📤 Bazani yuklab olish", callback_data="dbrestore:get")]])

    async def on_menu(client, m):
        await m.reply_text(_md(MENU_TEXT), reply_markup=_menu_kb())
        raise StopPropagation

    async def on_backup(client, m):
        await _send_backup(m)
        raise StopPropagation

    async def _send_backup(m):
        wait = await m.reply_text("⏳ Zaxira tayyorlanmoqda...")
        try:
            path, cap = await rs.make_backup()
        except RestoreError as e:
            await wait.edit_text(f"❌ {e}")
            return
        except Exception as e:
            log.exception("backup xato")
            await wait.edit_text(f"❌ Zaxira olishda xato: {e}")
            return
        try:
            await m.reply_document(path, caption=cap)
            await wait.delete()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    async def on_help(client, m):
        await m.reply_text(HELP_TEXT.format(bk="backup").replace("<b>", "**").replace("</b>", "**")
                           .replace("<code>", "`").replace("</code>", "`"))
        raise StopPropagation

    async def on_document(client, m):
        d = m.document
        if d.file_size and d.file_size > TG_DOWNLOAD_LIMIT * 10:
            await m.reply_text("❌ Fayl juda katta. `/restore_url https://…` dan foydalaning.")
            return
        tmp = os.path.join(_mkdir(WORK_DIR), f"up_{secrets.token_hex(4)}_{os.path.basename(d.file_name or 'x')}")
        try:
            await m.download(file_name=tmp)
            await _stage_and_ask(m, tmp, d.file_name or "")
        except Exception as e:
            log.exception("yuklab olish xato")
            await m.reply_text(f"❌ Faylni yuklab olib bo'lmadi: {e}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise StopPropagation

    async def on_url(client, m):
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await m.reply_text("Havolani yozing: `/restore_url https://…`")
            return
        wait = await m.reply_text("⏳ Fayl yuklanmoqda...")
        tmp = os.path.join(_mkdir(WORK_DIR), f"url_{secrets.token_hex(4)}")
        try:
            name = await _download_url(parts[1].strip(), tmp)
            if not adapter.accepts(name):
                if _is_gzip(tmp) or open(tmp, "rb").read(16) == b"SQLite format 3\x00":
                    name = (name or "download") + adapter.exts[0]
            await wait.delete()
            await _stage_and_ask(m, tmp, name)
        except RestoreError as e:
            await wait.edit_text(f"❌ {e}")
        except Exception as e:
            log.exception("restore_url xato")
            await wait.edit_text(f"❌ Yuklab bo'lmadi: {e}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise StopPropagation

    async def on_cb(client, q):
        parts = (q.data or "").split(":", 2)
        action = parts[1] if len(parts) > 1 else ""
        token = parts[2] if len(parts) > 2 else ""
        if action == "menu":
            await q.answer()
            await q.message.reply_text(_md(MENU_TEXT), reply_markup=_menu_kb())
            return
        if action == "up":
            await q.answer()
            await q.message.reply_text(_md(UP_TEXT))
            return
        if action == "get":
            await q.answer("Zaxira tayyorlanmoqda...")
            await _send_backup(q.message)
            return
        if action == "no":
            rs.cancel(token)
            await q.message.edit_text("❌ Tiklash bekor qilindi.")
            return
        if action != "yes":
            return
        try:
            rs._load_pending(token, q.from_user.id)
        except RestoreError as e:
            await q.answer(str(e), show_alert=True)
            return
        await q.answer()
        await q.message.edit_text("⏳ Tiklanmoqda... (avval joriy baza nusxasi yuboriladi)")

        async def safety(path: str, caption: str):
            await client.send_document(q.from_user.id, path, caption=caption)

        try:
            await rs.commit(token, q.from_user.id, safety)
        except Exception as e:
            log.exception("commit xato")
            await q.message.edit_text(f"❌ Tiklab bo'lmadi: {e}\nJoriy baza o'zgarmadi.")
            return
        await q.message.edit_text("✅ **Baza tiklandi.** Bot qayta ishga tushmoqda (5–15 soniya)...")
        await asyncio.sleep(1.5)
        restart_process()

    app.add_handler(MessageHandler(on_document, filters.document & doc_f & owner_f), group=group)
    app.add_handler(MessageHandler(on_url, filters.command("restore_url") & owner_f), group=group)
    app.add_handler(MessageHandler(on_menu, filters.command("baza") & owner_f), group=group)
    if backup_cmd:
        app.add_handler(MessageHandler(on_backup, filters.command("backup") & owner_f), group=group)
    app.add_handler(MessageHandler(on_help, filters.command("restore") & owner_f), group=group)
    app.add_handler(CallbackQueryHandler(on_cb, filters.regex(r"^dbrestore:") & cb_owner_f), group=group)

    async def on_cb_denied(client, q):
        await q.answer("Bu tugma faqat owner uchun.", show_alert=True)

    app.add_handler(CallbackQueryHandler(on_cb_denied, filters.regex(r"^dbrestore:")), group=group)
    return rs
