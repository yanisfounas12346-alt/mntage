"""Persistent local queue and history; one job at a time, no background worker."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path("outputs") / "mntage.sqlite3"

def connect():
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT NOT NULL,
      title TEXT NOT NULL, script TEXT NOT NULL, mode TEXT NOT NULL,
      voice TEXT NOT NULL, captions INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued', video TEXT, error TEXT,
      views INTEGER NOT NULL DEFAULT 0, revenue REAL NOT NULL DEFAULT 0,
      costs REAL NOT NULL DEFAULT 0, youtube_url TEXT
    )""")
    con.commit()
    return con

def enqueue(title, script, mode, voice, captions):
    with connect() as con:
        cur = con.execute("INSERT INTO jobs(created,title,script,mode,voice,captions,status) VALUES(?,?,?,?,?,?,'queued')",
                          (datetime.now(timezone.utc).isoformat(timespec="seconds"),title,script,mode,voice,int(captions)))
        return cur.lastrowid

def jobs(limit=100):
    with connect() as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?",(limit,))]

def next_job():
    with connect() as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
        if row:
            con.execute("UPDATE jobs SET status='running' WHERE id=?",(row["id"],))
        return dict(row) if row else None

def finish(job_id, video=None, error=None):
    with connect() as con:
        con.execute("UPDATE jobs SET status=?,video=?,error=? WHERE id=?",
                    ("failed" if error else "done",str(video) if video else None,error,job_id))

def update_metrics(job_id, views, revenue, costs):
    with connect() as con:
        con.execute("UPDATE jobs SET views=?,revenue=?,costs=? WHERE id=?",
                    (max(0,int(views)),float(revenue),float(costs),job_id))

def set_youtube(job_id, url):
    with connect() as con:
        con.execute("UPDATE jobs SET youtube_url=? WHERE id=?",(url,job_id))
