import sqlite3, os, datetime, bcrypt, uuid
from pymongo import MongoClient

DB_PATH = "local.db"

# --- Load MongoDB URI ---
MONGO_URI = None
MONGO_DB_NAME = "test" # Default to 'test' if not specified

if os.path.exists("config/config.env"):
    for line in open("config/config.env"):
        if line.startswith("MONGO_URI"):
            MONGO_URI = line.split("=", 1)[1].strip()
        elif line.startswith("MONGO_DB_NAME"):
            MONGO_DB_NAME = line.split("=", 1)[1].strip()

# ------------------------
# SQLite + MongoDB setup
# ------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS biomass_records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ownerId TEXT,
        recordId TEXT,
        shrimpCount INTEGER,
        biomass REAL,
        feedMeasurement REAL,
        dateTime TEXT,
        synced INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    cur = conn.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        hashed_pw = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
        conn.execute("INSERT INTO users(id, username, email, password) VALUES(?,?,?,?)",
                     ("local-admin", "admin", "admin@example.com", hashed_pw))
        conn.commit()
    conn.close()

# ------------------------
# User Authentication
# ------------------------

def verify_user(username, password):
    """Try verifying via MongoDB first; fallback to local SQLite."""
    try:
        print(f"Attempting MongoDB verification for user: {username}")
        print(f"Using MONGO_URI: {MONGO_URI}")
        print(f"Using MONGO_DB_NAME: {MONGO_DB_NAME}")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client[MONGO_DB_NAME]
        user = db["users"].find_one({"username": username})
        print(f"MongoDB user found: {user is not None}")
        if user:
            print(f"Stored password hash (MongoDB): {user.get('password')}")
            if bcrypt.checkpw(password.encode(), user["password"].encode()):
                print("bcrypt.checkpw successful for MongoDB user.")
                # Convert ObjectId to string before caching in SQLite
                cache_user(str(user["_id"]), user["username"], user["email"], user["password"])
                return str(user["_id"])
            else:
                print("bcrypt.checkpw failed for MongoDB user.")
        else:
            print(f"User '{username}' not found in MongoDB.")
    except Exception as e:
        print(f"MongoDB verification failed: {e}")
        pass  # fallback if offline

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT id, password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row[1].encode()):
        return row[0]
    return None

def cache_user(uid, username, email, hashed_pw):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    INSERT OR IGNORE INTO users(id, username, email, password)
    VALUES(?,?,?,?)
    """, (uid, username, email, hashed_pw))
    conn.commit(); conn.close()

# ------------------------
# Biomass Record Handling
# ------------------------

def save_biomass_record(owner_id, shrimp_count, biomass, feed_measurement):
    conn = sqlite3.connect(DB_PATH)
    record_id = str(uuid.uuid4())
    date_time = datetime.datetime.now().isoformat()
    conn.execute("""
    INSERT INTO biomass_records(ownerId, recordId, shrimpCount, biomass, feedMeasurement, dateTime, synced)
    VALUES(?,?,?,?,?, ?,0)
    """, (owner_id, record_id, shrimp_count, biomass, feed_measurement, date_time))
    conn.commit(); conn.close()

def sync_biomass_records():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT ownerId, recordId, shrimpCount, biomass, feedMeasurement, dateTime FROM biomass_records WHERE synced=0").fetchall()
    if not rows:
        conn.close()
        return 0
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        db = client[MONGO_DB_NAME]
        col = db["biomassrecords"]
        docs = []
        for (ownerId, recordId, shrimpCount, biomass, feedMeasurement, dateTime) in rows:
            docs.append({
                "ownerId": ownerId,
                "recordId": recordId,
                "shrimpCount": shrimpCount,
                "biomass": biomass,
                "feedMeasurement": feedMeasurement,
                "dateTime": datetime.datetime.fromisoformat(dateTime)
            })
        if docs:
            col.insert_many(docs)
            conn.execute("UPDATE biomass_records SET synced=1")
            conn.commit()
            n = len(docs)
    except Exception as e:
        print("Sync error:", e)
        n = 0
    conn.close()
    return n
