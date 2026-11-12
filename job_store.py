"""Persistent local queue and history; one job at a time, no background worker."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB = Path("outputs") / "mntage.sqlite3"

@contextmanager
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
    # Existing local queues predate the narration speed setting.
    columns={row[1] for row in con.execute("PRAGMA table_info(jobs)")}
    if "voice_rate" not in columns:
        con.execute("ALTER TABLE jobs ADD COLUMN voice_rate TEXT NOT NULL DEFAULT '-5%'")
    con.commit()
    try:
        with con:
            yield con
    finally:
        con.close()

def enqueue(title, script, mode, voice, captions, voice_rate="-5%"):
    with connect() as con:
        cur = con.execute("INSERT INTO jobs(created,title,script,mode,voice,captions,voice_rate,status) VALUES(?,?,?,?,?,?,?,'queued')",
                          (datetime.now(timezone.utc).isoformat(timespec="seconds"),title,script,mode,voice,int(captions),voice_rate))
        return cur.lastrowid

def jobs(limit=100):
    with connect() as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?",(limit,))]

def next_job():
    with connect() as con:
        # Serialize claimers: two Streamlit sessions must not start the same job.
        con.execute("BEGIN IMMEDIATE")
        con.row_factory = sqlite3.Row
        # Only one render may run at a time, even from separate browser tabs.
        if con.execute("SELECT 1 FROM jobs WHERE status='running' LIMIT 1").fetchone():
            return None
        row = con.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
        if row:
            con.execute("UPDATE jobs SET status='running' WHERE id=? AND status='queued'",(row["id"],))
            claimed = dict(row)
            claimed["status"] = "running"
            return claimed
        return None

def finish(job_id, video=None, error=None):
    """Complete only a running render; never overwrite cancelled or retried jobs."""
    with connect() as con:
        result = con.execute(
            "UPDATE jobs SET status=?,video=?,error=? WHERE id=? AND status='running'",
            ("failed" if error else "done",str(video) if video else None,error,job_id))
        return result.rowcount == 1

def cancel_queued(job_id):
    """Cancel only pending jobs; never interrupt an active FFmpeg render."""
    with connect() as con:
        result=con.execute(
            "UPDATE jobs SET status='cancelled' WHERE id=? AND status='queued'",
            (job_id,))
        return result.rowcount == 1

def retry_failed(job_id):
    """Return only a failed task to the queue; preserve its script and settings."""
    with connect() as con:
        result=con.execute(
            "UPDATE jobs SET status='queued',error=NULL,video=NULL "
            "WHERE id=? AND status='failed'",(job_id,))
        return result.rowcount == 1

def recover_interrupted(job_id):
    """Manual recovery only: never automatically reset an active render."""
    with connect() as con:
        result=con.execute(
            "UPDATE jobs SET status='queued',error=NULL,video=NULL "
            "WHERE id=? AND status='running'",(job_id,))
        return result.rowcount == 1

def update_metrics(job_id, views, revenue, costs):
    with connect() as con:
        con.execute("UPDATE jobs SET views=?,revenue=?,costs=? WHERE id=?",
                    (max(0,int(views)),float(revenue),float(costs),job_id))

def set_youtube(job_id, url):
    with connect() as con:
        con.execute("UPDATE jobs SET youtube_url=? WHERE id=?",(url,job_id))
