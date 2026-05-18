"""
FastAPI for collecting posts from Telegram channels and storing them in SQLite.

Run:
  uvicorn api_telegram:app --reload
"""

import os
import sqlite3
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from scraper_telegram import clean_text, extract_channel

API_ID   = int(os.getenv("TG_API_ID",   "25329178"))
API_HASH = os.getenv("TG_API_HASH", "ec2826d2e3f4fd2f40624394c8fe0d00")
# !! enter here your parsing phone number
PHONE    = os.getenv("TG_PHONE",    "")

DATA_DIR = Path("dynamic_data_collection")
DB_PATH  = DATA_DIR / "telegram_posts.db"
DATA_DIR.mkdir(exist_ok=True)

_executor = ThreadPoolExecutor(max_workers=4)

# ─── Database ─────────────────────────────────────────────────────────────────

def _init_db() -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id        INTEGER,
                channel   TEXT,
                person    TEXT,
                posted_at TEXT,
                source    TEXT,
                text      TEXT,
                PRIMARY KEY (id, channel)
            )
        """)

_init_db()


@contextmanager
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def db_existing_ids(channel: str, date_from: datetime, date_to: datetime) -> set[int]:
    with get_db() as con:
        rows = con.execute(
            "SELECT id FROM posts WHERE channel = ? AND posted_at >= ? AND posted_at <= ?",
            (channel, date_from.strftime("%Y-%m-%dT%H:%M:%SZ"), date_to.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ).fetchall()
    return {r["id"] for r in rows}


def db_insert(posts: list[dict], channel: str) -> None:
    with get_db() as con:
        con.executemany(
            "INSERT OR IGNORE INTO posts (id, channel, person, posted_at, source, text) VALUES (?,?,?,?,?,?)",
            [(p["id"], channel, p["person"], p["posted_at"], p["source"], p["text"]) for p in posts],
        )


def db_fetch_range(channel: str, date_from: datetime, date_to: datetime) -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            "SELECT id, person, posted_at, source, text FROM posts "
            "WHERE channel = ? AND posted_at >= ? AND posted_at <= ? ORDER BY posted_at",
            (channel, date_from.strftime("%Y-%m-%dT%H:%M:%SZ"), date_to.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    channel_url: str    = Field(..., example="t.me/Denys_Smyhal")
    person: str         = Field(..., example="Денис Шмигаль")
    date_from: datetime = Field(..., example="2024-01-01T00:00:00Z")
    date_to: datetime   = Field(..., example="2026-05-17T23:59:59Z")


class ScrapeResponse(BaseModel):
    status: str         # "added" | "exists"
    newly_added: int
    total_in_range: int
    posts: list[dict]


# ─── Scraping logic ───────────────────────────────────────────────────────────

def _scrape_sync(req: ScrapeRequest) -> ScrapeResponse:
    from telethon.sync import TelegramClient

    channel   = extract_channel(req.channel_url)
    date_from = req.date_from if req.date_from.tzinfo else req.date_from.replace(tzinfo=timezone.utc)
    date_to   = req.date_to   if req.date_to.tzinfo   else req.date_to.replace(tzinfo=timezone.utc)

    existing_ids = db_existing_ids(channel, date_from, date_to)

    new_posts: list[dict] = []

    with TelegramClient("tg_session", API_ID, API_HASH) as client:
        client.start(phone=PHONE)

        for message in client.iter_messages(channel, offset_date=date_to, reverse=False):
            msg_date = message.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)

            if msg_date < date_from:
                break

            if message.id in existing_ids:
                continue

            text = clean_text(message.text or "")
            if not text:
                continue

            new_posts.append({
                "id":        message.id,
                "posted_at": msg_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source":    "telegram",
                "person":    req.person,
                "text":      text,
            })

    if new_posts:
        db_insert(new_posts, channel)

    all_posts = db_fetch_range(channel, date_from, date_to)

    return ScrapeResponse(
        status        = "added" if new_posts else "exists",
        newly_added   = len(new_posts),
        total_in_range= len(all_posts),
        posts         = all_posts,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Telegram Scraper API",
    description="Collect posts from Telegram channels and store them in SQLite",
    version="2.0.0",
)


@app.post("/scrape", response_model=ScrapeResponse, summary="Collect posts from a channel")
async def scrape(req: ScrapeRequest):
    """
    - If no data exists for the given range → fetches from Telegram, saves to DB, returns `status: added`.
    - If all data already exists → returns `status: exists` without contacting Telegram.
    - If partial data exists → fetches only missing messages.
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _scrape_sync, req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@app.get("/posts/{channel}", summary="All channel posts from DB")
async def get_posts(channel: str, date_from: datetime | None = None, date_to: datetime | None = None):
    """Returns posts from the DB without contacting Telegram."""
    df = date_from or datetime(2000, 1, 1, tzinfo=timezone.utc)
    dt = date_to   or datetime(2099, 1, 1, tzinfo=timezone.utc)
    if df.tzinfo is None:
        df = df.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return db_fetch_range(channel, df, dt)
