import sqlite3
import contextlib
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "guardia.db"

DEFAULT_ROLES = [
    "Conductor",
    "Jefe de guardia",
    "Atacante",
    "Entrada forzada",
    "Rescate",
    "Apoyo exterior",
    "Sanitario",
    "Comunicaciones",
]


@contextlib.contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS volunteers (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                name   TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS beds (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT NOT NULL,
                notes  TEXT
            );

            CREATE TABLE IF NOT EXISTS trucks (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT
            );

            CREATE TABLE IF NOT EXISTS shifts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT NOT NULL,
                notes      TEXT,
                is_active  INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS bed_assignments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id     INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
                volunteer_id INTEGER NOT NULL REFERENCES volunteers(id),
                bed_id       INTEGER NOT NULL REFERENCES beds(id),
                UNIQUE(shift_id, volunteer_id),
                UNIQUE(shift_id, bed_id)
            );

            CREATE TABLE IF NOT EXISTS truck_assignments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id     INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
                volunteer_id INTEGER NOT NULL REFERENCES volunteers(id),
                truck_id     INTEGER NOT NULL REFERENCES trucks(id),
                role         TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS roles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS shift_trucks (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
                truck_id INTEGER NOT NULL REFERENCES trucks(id) ON DELETE CASCADE,
                enabled  INTEGER NOT NULL DEFAULT 1,
                UNIQUE(shift_id, truck_id)
            );
        """)
        seed_defaults(conn)
        migrate(conn)


def migrate(conn: sqlite3.Connection):
    """Add new columns and fix constraints without breaking existing DBs."""
    # Add columns if missing
    for sql in [
        "ALTER TABLE beds ADD COLUMN room TEXT",
        "ALTER TABLE trucks ADD COLUMN color TEXT DEFAULT '#93c5fd'",
        "ALTER TABLE volunteers ADD COLUMN permanent INTEGER NOT NULL DEFAULT 0",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Seed roles from DEFAULT_ROLES if table is empty
    role_count = conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
    if role_count == 0:
        for i, r in enumerate(DEFAULT_ROLES):
            conn.execute("INSERT OR IGNORE INTO roles (name, sort_order) VALUES (?, ?)", (r, i))

    # Remove UNIQUE(shift_id, volunteer_id) from truck_assignments if present
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='truck_assignments'"
    ).fetchone()
    if schema and "UNIQUE(shift_id, volunteer_id)" in schema["sql"]:
        conn.executescript("""
            PRAGMA foreign_keys = OFF;
            CREATE TABLE truck_assignments_new (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id     INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
                volunteer_id INTEGER NOT NULL REFERENCES volunteers(id),
                truck_id     INTEGER NOT NULL REFERENCES trucks(id),
                role         TEXT NOT NULL
            );
            INSERT INTO truck_assignments_new SELECT * FROM truck_assignments;
            DROP TABLE truck_assignments;
            ALTER TABLE truck_assignments_new RENAME TO truck_assignments;
            PRAGMA foreign_keys = ON;
        """)


def seed_defaults(conn: sqlite3.Connection):
    bed_count = conn.execute("SELECT COUNT(*) FROM beds").fetchone()[0]
    if bed_count == 0:
        beds = [(str(i), None) for i in range(1, 21)]
        beds.append(("Cama Jefe", "Reservada para el jefe de guardia"))
        conn.executemany("INSERT INTO beds (number, notes) VALUES (?, ?)", beds)

    truck_count = conn.execute("SELECT COUNT(*) FROM trucks").fetchone()[0]
    if truck_count == 0:
        conn.executemany(
            "INSERT INTO trucks (name, type) VALUES (?, ?)",
            [("Autobomba 1", "Autobomba"), ("Autobomba 2", "Autobomba")],
        )


MONTHS_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def es_date(date_str: str) -> str:
    """Convert ISO date string 'YYYY-MM-DD' to Spanish long form."""
    try:
        year, month, day = date_str.split("-")
        return f"{int(day)} de {MONTHS_ES[int(month)]} de {year}"
    except Exception:
        return date_str
