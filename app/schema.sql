CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT 'mint',
    semester TEXT NOT NULL DEFAULT '',
    syllabus_progress INTEGER NOT NULL DEFAULT 0 CHECK(syllabus_progress BETWEEN 0 AND 100)
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT 'Personal',
    due_at TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 45,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low','medium','high')),
    status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','done')),
    kind TEXT NOT NULL DEFAULT 'study',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    exam_at TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    color TEXT NOT NULL DEFAULT 'violet',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    planned_minutes INTEGER NOT NULL,
    actual_minutes INTEGER NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'focus'
);
CREATE TABLE IF NOT EXISTS interaction_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    duration_ms INTEGER,
    detail TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS survey_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    primary_challenge TEXT NOT NULL,
    planning_method TEXT NOT NULL,
    planning_difficulty INTEGER NOT NULL CHECK(planning_difficulty BETWEEN 1 AND 5),
    satisfaction INTEGER NOT NULL CHECK(satisfaction BETWEEN 1 AND 5),
    missed_tasks INTEGER NOT NULL DEFAULT 0,
    current_method_hours REAL NOT NULL DEFAULT 0,
    feedback TEXT NOT NULL DEFAULT '',
    sus_answers TEXT NOT NULL DEFAULT '[]',
    sus_score REAL NOT NULL DEFAULT 0,
    consent_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(consent_confirmed IN (0,1)),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usability_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    participant_code TEXT NOT NULL,
    baseline_minutes REAL NOT NULL,
    prototype_minutes REAL NOT NULL,
    baseline_success INTEGER NOT NULL CHECK(baseline_success IN (0,1)),
    prototype_success INTEGER NOT NULL CHECK(prototype_success IN (0,1)),
    baseline_errors INTEGER NOT NULL DEFAULT 0,
    prototype_errors INTEGER NOT NULL DEFAULT 0,
    satisfaction INTEGER NOT NULL CHECK(satisfaction BETWEEN 1 AND 5),
    sus_answers TEXT NOT NULL,
    sus_score REAL NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    consent_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(consent_confirmed IN (0,1)),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_at);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON study_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_events_created ON interaction_events(created_at);
