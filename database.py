import sqlite3, os, datetime, bcrypt, uuid
from pymongo import MongoClient


# ------------------------
# Configuration
# ------------------------
DB_PATH = "local.db"
MONGO_URI = None
MONGO_DB_NAME = "test"  # your MongoDB database name

# --- Load MongoDB URI from config.env ---
if os.path.exists("config/config.env"):
    for line in open("config/config.env"):
        if line.startswith("MONGO_URI"):
            MONGO_URI = line.split("=", 1)[1].strip()


# ------------------------
# Database Initialization
# ------------------------
def init_db():
    """Initialize local SQLite database tables."""
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

    # Create default offline admin if no user exists
    cur = conn.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        hashed_pw = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users(id, username, email, password) VALUES(?,?,?,?)",
            ("local-admin", "admin", "admin@example.com", hashed_pw)
        )
        conn.commit()
    conn.close()


# ------------------------
# User Authentication
# ------------------------
def verify_user(username, password):
    print(f"Attempting MongoDB verification for user: {username}")
    print(f"Using MONGO_URI: {MONGO_URI}")
    print(f"Using MONGO_DB_NAME: {MONGO_DB_NAME}")

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
        db = client[MONGO_DB_NAME]
        user = db["users"].find_one({"username": username})
        print(f"MongoDB user found: {bool(user)}")
        if user:
            print(f"Stored password hash (MongoDB): {user['password']}")
            if bcrypt.checkpw(password.encode(), user["password"].encode()):
                print("bcrypt.checkpw successful for MongoDB user.")
                # ✅ FIXED: Convert ObjectId to string before caching
                cache_user(str(user["_id"]), user["username"], user["email"], user["password"])
                return str(user["_id"])
    except Exception as e:
        print("MongoDB connection failed:", e)

    # Fallback: Local login
    print("Falling back to local SQLite verification...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT id, password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row[1].encode()):
        print("Local user verified successfully.")
        return row[0]

    print("Invalid credentials for all sources.")
    return None

def cache_user(uid, username, email, hashed_pw):
    """Cache verified MongoDB user locally for offline access."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    INSERT OR IGNORE INTO users(id, username, email, password)
    VALUES(?,?,?,?)
    """, (uid, username, email, hashed_pw))
    conn.commit()
    conn.close()


# ------------------------
# Biomass Record Handling
# ------------------------
def save_biomass_record(owner_id, shrimp_count, biomass, feed_measurement):
    """Save a local record for the current user."""
    conn = sqlite3.connect(DB_PATH)
    record_id = str(uuid.uuid4())
    date_time = datetime.datetime.now().isoformat()
    conn.execute("""
    INSERT INTO biomass_records(ownerId, recordId, shrimpCount, biomass, feedMeasurement, dateTime, synced)
    VALUES(?,?,?,?,?, ?,0)
    """, (owner_id, record_id, shrimp_count, biomass, feed_measurement, date_time))
    conn.commit()
    conn.close()


def get_all_records(owner_id):
    """Retrieve all local records belonging to a specific user."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT * FROM biomass_records WHERE ownerId=? ORDER BY id DESC",
        (owner_id,)
    ).fetchall()
    conn.close()
    return rows


def get_last_record(owner_id=None):
    """Retrieve the most recent record (optionally filtered by user)."""
    conn = sqlite3.connect(DB_PATH)
    if owner_id:
        row = conn.execute(
            "SELECT * FROM biomass_records WHERE ownerId=? ORDER BY id DESC LIMIT 1",
            (owner_id,)
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM biomass_records ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row

from bson import ObjectId
from pymongo import MongoClient

def delete_record(record_id, owner_id):
    """
    Delete a specific record both locally and in MongoDB Atlas (if synced).
    """
    print(f"Deleting record {record_id} for user {owner_id}...")

    # --- 1. Delete locally ---
    conn = sqlite3.connect(DB_PATH)
    record = conn.execute(
        "SELECT recordId, synced FROM biomass_records WHERE id=? AND ownerId=?",
        (record_id, owner_id)
    ).fetchone()

    if not record:
        print("No record found locally.")
        conn.close()
        return

    record_uuid, synced = record

    conn.execute("DELETE FROM biomass_records WHERE id=? AND ownerId=?", (record_id, owner_id))
    conn.commit()
    conn.close()
    print("Deleted locally.")

    # --- 2. If it was synced, delete it from MongoDB as well ---
    if synced == 1:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
            db = client[MONGO_DB_NAME]
            col = db["biomassrecords"]

            # Try to delete using both ObjectId and string ownerId for safety
            delete_result = col.delete_one({
                "recordId": record_uuid,
                "$or": [
                    {"ownerId": ObjectId(str(owner_id))},
                    {"ownerId": str(owner_id)}
                ]
            })

            if delete_result.deleted_count > 0:
                print("Deleted from MongoDB Atlas.")
            else:
                print("No matching MongoDB record found.")
        except Exception as e:
            print("Error deleting from MongoDB Atlas:", e)
    else:
        print("Record was not synced yet, skipped MongoDB deletion.")


def sync_biomass_records(owner_id):
    """
    Sync only the current user's unsynced records to MongoDB Atlas.
    After syncing, mark them as synced locally.
    """
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT ownerId, recordId, shrimpCount, biomass, feedMeasurement, dateTime
        FROM biomass_records
        WHERE synced=0 AND ownerId=?
    """, (owner_id,)).fetchall()

    if not rows:
        conn.close()
        print("No unsynced records found for this user.")
        return 0

    try:
        print(f"Preparing to sync {len(rows)} record(s) for user {owner_id}...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
        db = client[MONGO_DB_NAME]          
        col = db["biomassrecords"]           

        docs = []
        for (ownerId, recordId, shrimpCount, biomass, feedMeasurement, dateTime) in rows:
            try:
                mongo_owner_id = ObjectId(str(ownerId))  
            except Exception:
                mongo_owner_id = str(ownerId)  # fallback if invalid format

            biomass = round(float(biomass), 2) if biomass is not None else 0.0
            feedMeasurement = round(float(feedMeasurement), 2) if feedMeasurement is not None else 0.0
            docs.append({
                "ownerId": mongo_owner_id,
                "recordId": recordId,
                "shrimpCount": shrimpCount,
                "biomass": biomass,
                "feedMeasurement": feedMeasurement,
                "dateTime": datetime.datetime.fromisoformat(dateTime),
                "timestamp_str": datetime.datetime.fromisoformat(dateTime).strftime("%Y-%m-%d %H:%M:%S")
            })

        if docs:
            result = col.insert_many(docs)
            print(f"Inserted {len(result.inserted_ids)} documents into MongoDB Atlas.")
            conn.execute("UPDATE biomass_records SET synced=1 WHERE ownerId=?", (owner_id,))
            conn.commit()

        n = len(docs)
    except Exception as e:
        print("Sync error:", e)
        n = 0

    conn.close()
    return n

