import pytest
import sqlite3
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS societies (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, config_yaml TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, society_id TEXT REFERENCES societies(id),
    task TEXT NOT NULL, status TEXT DEFAULT 'running',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP, finished_at DATETIME
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT REFERENCES runs(id),
    round INTEGER NOT NULL, event_type TEXT NOT NULL,
    from_agent TEXT, to_agent TEXT, content TEXT, confidence REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT REFERENCES runs(id),
    round INTEGER NOT NULL, agent TEXT NOT NULL, vote INTEGER NOT NULL,
    weight REAL NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT REFERENCES runs(id) UNIQUE,
    content TEXT NOT NULL, format TEXT DEFAULT 'markdown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS agent_reputation (
    id INTEGER PRIMARY KEY AUTOINCREMENT, society_id TEXT REFERENCES societies(id),
    agent_name TEXT NOT NULL, total_proposals INTEGER DEFAULT 0,
    proposals_won INTEGER DEFAULT 0, avg_confidence REAL DEFAULT 0.0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(society_id, agent_name)
);
"""


@pytest.fixture
def db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    yield conn
    conn.close()


def make_society(db, name="S"):
    sid = str(uuid.uuid4())
    db.execute("INSERT INTO societies (id, name, config_yaml) VALUES (?, ?, ?)", (sid, name, "y"))
    db.commit()
    return sid


def make_run(db, sid, task="task"):
    run_id = str(uuid.uuid4())
    db.execute("INSERT INTO runs (id, society_id, task) VALUES (?, ?, ?)", (run_id, sid, task))
    db.commit()
    return run_id


def test_create_and_get_run(db):
    sid = make_society(db)
    run_id = make_run(db, sid, "Test task")
    row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert row["task"] == "Test task"
    assert row["status"] == "running"


def test_mark_run_complete(db):
    sid = make_society(db)
    run_id = make_run(db, sid)
    db.execute("UPDATE runs SET status = 'complete', finished_at = CURRENT_TIMESTAMP WHERE id = ?", (run_id,))
    db.commit()
    row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert row["status"] == "complete"


def test_list_runs(db):
    sid = make_society(db)
    make_run(db, sid, "task 1")
    make_run(db, sid, "task 2")
    rows = db.execute("SELECT * FROM runs WHERE society_id = ?", (sid,)).fetchall()
    assert len(rows) == 2


def test_insert_and_get_events(db):
    sid = make_society(db)
    run_id = make_run(db, sid)
    db.execute(
        "INSERT INTO events (run_id, round, event_type, from_agent, content, confidence) VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, 1, "proposal", "CEO", "Expand.", 0.9)
    )
    db.commit()
    rows = db.execute("SELECT * FROM events WHERE run_id = ?", (run_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["from_agent"] == "CEO"


def test_replay_up_to_round(db):
    sid = make_society(db)
    run_id = make_run(db, sid)
    for r in [1, 2, 3]:
        db.execute("INSERT INTO events (run_id, round, event_type, content) VALUES (?, ?, ?, ?)",
                   (run_id, r, "proposal", f"R{r}"))
    db.commit()
    rows = db.execute("SELECT * FROM events WHERE run_id = ? AND round <= ?", (run_id, 2)).fetchall()
    assert len(rows) == 2
    assert all(r["round"] <= 2 for r in rows)


def test_get_max_round(db):
    sid = make_society(db)
    run_id = make_run(db, sid)
    db.execute("INSERT INTO events (run_id, round, event_type, content) VALUES (?, 1, 'proposal', '')", (run_id,))
    db.execute("INSERT INTO events (run_id, round, event_type, content) VALUES (?, 3, 'proposal', '')", (run_id,))
    db.commit()
    row = db.execute("SELECT MAX(round) as max_round FROM events WHERE run_id = ?", (run_id,)).fetchone()
    assert row["max_round"] == 3


def test_save_and_get_report(db):
    sid = make_society(db)
    run_id = make_run(db, sid)
    db.execute("INSERT INTO reports (run_id, content) VALUES (?, ?)", (run_id, "# Report\nAll good."))
    db.commit()
    row = db.execute("SELECT * FROM reports WHERE run_id = ?", (run_id,)).fetchone()
    assert "All good" in row["content"]


def test_get_missing_report_returns_none(db):
    row = db.execute("SELECT * FROM reports WHERE run_id = ?", ("nonexistent",)).fetchone()
    assert row is None


def test_record_and_get_reputation(db):
    sid = make_society(db)
    db.execute("INSERT OR IGNORE INTO agent_reputation (society_id, agent_name) VALUES (?, ?)", (sid, "CEO"))
    db.execute("UPDATE agent_reputation SET total_proposals = 2, proposals_won = 1 WHERE society_id = ? AND agent_name = ?", (sid, "CEO"))
    db.commit()
    row = db.execute("SELECT * FROM agent_reputation WHERE society_id = ? AND agent_name = ?", (sid, "CEO")).fetchone()
    assert row["total_proposals"] == 2
    assert row["proposals_won"] == 1


def test_win_rate(db):
    sid = make_society(db)
    db.execute("INSERT OR IGNORE INTO agent_reputation (society_id, agent_name) VALUES (?, ?)", (sid, "CFO"))
    db.execute("UPDATE agent_reputation SET total_proposals = 3, proposals_won = 2 WHERE society_id = ? AND agent_name = ?", (sid, "CFO"))
    db.commit()
    row = db.execute("SELECT total_proposals, proposals_won FROM agent_reputation WHERE society_id = ? AND agent_name = ?", (sid, "CFO")).fetchone()
    rate = row["proposals_won"] / row["total_proposals"]
    assert abs(rate - 2/3) < 0.01
