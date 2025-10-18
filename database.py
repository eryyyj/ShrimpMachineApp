import sqlite3, os, datetime, hashlib
from pymongo import MongoClient

DB_PATH = "local.db"
MONGO_URI = None
if os.path.exists("config/config.env"):
    for line in open("config/config.env"):
        if line.startswith("MONGO_URI"):
            MONGO_URI = line.split("=", 1)[1].strip()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS runs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        started_at TEXT,
        ended_at TEXT,
        count INTEGER,
        biomass REAL,
        feed REAL,
        protein REAL,
        filler REAL,
        synced INTEGER DEFAULT 0
    )""")
    conn.commit()
    cur = conn.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        ph = hashlib.sha256("admin".encode()).hexdigest()
        conn.execute("INSERT INTO users(username,password_hash) VALUES(?,?)", ("admin", ph))
        conn.commit()
    conn.close()

def verify_user(username, password):
    ph = hashlib.sha256(password.encode()).hexdigest()
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        user = client["shrimpdb"]["users"].find_one({"username": username, "password_hash": ph})
        if user:
            cache_user(user["_id"], username, ph)
            return str(user["_id"])
    except Exception:
        pass
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, ph))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def cache_user(uid, username, ph):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO users(id, username, password_hash) VALUES(?,?,?)", (uid, username, ph))
    conn.commit(); conn.close()

def save_run(user_id, start, end, count, biomass, feed, protein, filler):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO runs(user_id,started_at,ended_at,count,biomass,feed,protein,filler,synced)
                    VALUES(?,?,?,?,?,?,?,?,0)""",
                 (user_id, start, end, count, biomass, feed, protein, filler))
    conn.commit(); conn.close()

def sync_runs():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM runs WHERE synced=0").fetchall()
    if not rows:
        conn.close(); return 0
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        col = client["shrimpdb"]["runs"]
        docs = []
        for r in rows:
            docs.append({
                "user_id": r[1],
                "started_at": r[2],
                "ended_at": r[3],
                "count": r[4],
                "biomass": r[5],
                "feed": r[6],
                "protein": r[7],
                "filler": r[8],
                "synced_at": datetime.datetime.utcnow().isoformat()
            })
        col.insert_many(docs)
        conn.execute("UPDATE runs SET synced=1")
        conn.commit()
        n = len(docs)
    except Exception as e:
        print("Sync error:", e)
        n = 0
    conn.close()
    return n
