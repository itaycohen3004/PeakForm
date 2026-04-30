"""
PeakForm — Database migration script.
Adds missing columns to existing database without recreating tables.
Safe to run multiple times.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'peakform.db')

def migrate(db_path=DB_PATH):
    print(f"[Migration] Connecting to: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    migrations = []

    def add_column_if_missing(table, column, definition):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cursor.fetchall()]
        if column not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            migrations.append(f"Added {table}.{column}")

    # athlete_profiles
    add_column_if_missing("athlete_profiles", "current_weight_kg",  "REAL")
    add_column_if_missing("athlete_profiles", "target_weight_kg",   "REAL")
    add_column_if_missing("athlete_profiles", "main_goal",          "TEXT DEFAULT 'general_fitness'")
    add_column_if_missing("athlete_profiles", "days_per_week",      "INTEGER DEFAULT 3")
    add_column_if_missing("athlete_profiles", "onboarding_complete","INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("athlete_profiles", "avatar_url",         "TEXT")

    # users
    add_column_if_missing("users", "email_index", "TEXT UNIQUE")
    add_column_if_missing("users", "role", "TEXT NOT NULL DEFAULT 'user'")

    # exercises — add status for approval workflow and muscles_tags for multi-category
    add_column_if_missing("exercises", "training_styles",  "TEXT DEFAULT 'gym,hybrid'")
    add_column_if_missing("exercises", "muscles_secondary","TEXT")
    add_column_if_missing("exercises", "muscles_tags",     "TEXT")  # comma-sep multi-muscle
    add_column_if_missing("exercises", "status",           "TEXT NOT NULL DEFAULT 'approved'")

    # Set all existing exercises to approved (seeded ones)
    cursor.execute("UPDATE exercises SET status = 'approved' WHERE status IS NULL OR status = ''")

    # workouts
    add_column_if_missing("workouts", "is_draft",        "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing("workouts", "total_sets",      "INTEGER DEFAULT 0")
    add_column_if_missing("workouts", "total_reps",      "INTEGER DEFAULT 0")
    add_column_if_missing("workouts", "total_volume_kg", "REAL DEFAULT 0")
    add_column_if_missing("workouts", "muscles_worked",  "TEXT")

    # workout_sets
    add_column_if_missing("workout_sets", "rpe", "REAL")

    # template_exercises — add default_reps for manual template creation
    add_column_if_missing("template_exercises", "default_reps", "INTEGER")

    # goals — new types (need to recreate table if CHECK constraint is wrong)
    add_column_if_missing("goals", "starting_value", "REAL DEFAULT 0")
    add_column_if_missing("goals", "photo_path",     "TEXT")
    add_column_if_missing("goals", "completed_at",   "DATETIME")

    # Create personal_records if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            weight_kg REAL,
            reps INTEGER,
            estimated_1rm REAL,
            achieved_at DATE NOT NULL,
            workout_id INTEGER,
            UNIQUE(user_id, exercise_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
            FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE SET NULL
        )
    """)

    # Create notifications if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            action_url TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # community_posts — add meta_data for rich template/workout posts
    add_column_if_missing("community_posts", "meta_data", "TEXT")

    # chat_rooms — add room_type for public/dm distinction
    add_column_if_missing("chat_rooms", "room_type", "TEXT NOT NULL DEFAULT 'public'")
    add_column_if_missing("chat_rooms", "owner_user_id", "INTEGER")  # For DM: user who owns the room

    # Ensure default chat rooms have room_type set
    cursor.execute("UPDATE chat_rooms SET room_type='public' WHERE room_type IS NULL OR room_type=''")

    # Create ai_sessions if not exists

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            message TEXT NOT NULL,
            context_snapshot TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Create body_weight_logs if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS body_weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weight_kg REAL NOT NULL,
            photo_path TEXT,
            notes TEXT,
            logged_at DATE NOT NULL DEFAULT CURRENT_DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_body_weight_user ON body_weight_logs(user_id, logged_at)")

    # Create weekly_schedule if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
            UNIQUE(user_id, weekday),
            FOREIGN KEY (user_id)       REFERENCES users(id)             ON DELETE CASCADE,
            FOREIGN KEY (template_id)   REFERENCES workout_templates(id) ON DELETE CASCADE
        )
    """)

    # Fix goals CHECK constraint — SQLite doesn't support ALTER TABLE for this,
    # so we recreate if needed
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='goals'")
    goals_sql = (cursor.fetchone() or [None])[0] or ''
    if 'exercise_1rm' not in goals_sql:
        print("[Migration] Recreating goals table with updated types...")
        # Save data
        cursor.execute("SELECT * FROM goals")
        existing_goals_cols = [d[0] for d in cursor.description or []]
        existing_goals = cursor.fetchall()
        # Recreate
        cursor.execute("DROP TABLE IF EXISTS goals_old")
        cursor.execute("ALTER TABLE goals RENAME TO goals_old")
        cursor.execute("""
            CREATE TABLE goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                goal_type TEXT NOT NULL,
                title TEXT NOT NULL,
                exercise_id INTEGER,
                target_value REAL NOT NULL,
                current_value REAL NOT NULL DEFAULT 0,
                starting_value REAL DEFAULT 0,
                unit TEXT,
                deadline DATE,
                is_completed INTEGER NOT NULL DEFAULT 0,
                photo_path TEXT,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE SET NULL
            )
        """)
        # Migrate data
        safe_cols = ['id','user_id','goal_type','title','exercise_id','target_value',
                     'current_value','starting_value','unit','deadline',
                     'is_completed','photo_path','completed_at','created_at']
        insert_cols  = [c for c in safe_cols if c in existing_goals_cols]
        source_idxs  = [existing_goals_cols.index(c) for c in insert_cols]
        if existing_goals:
            for row in existing_goals:
                vals = tuple(row[i] for i in source_idxs)
                qs = ','.join(['?']*len(vals))
                cursor.execute(f"INSERT OR IGNORE INTO goals ({','.join(insert_cols)}) VALUES ({qs})", vals)
        cursor.execute("DROP TABLE IF EXISTS goals_old")
        migrations.append("Recreated goals table")

    from backend.services.encryption_service import encrypt_data, decrypt_data, blind_index
    cursor.execute("SELECT id, email, email_index FROM users")
    users = cursor.fetchall()
    for u_id, email, idx in users:
        if not idx: # Likely unencrypted/not indexed
            # Decrypt if it was accidentally encrypted already, or take as plain
            raw = decrypt_data(email)
            enc = encrypt_data(raw)
            bidx = blind_index(raw)
            try:
                cursor.execute("UPDATE users SET email = ?, email_index = ? WHERE id = ?", (enc, bidx, u_id))
                migrations.append(f"Encrypted/indexed user {u_id}")
            except Exception as e:
                print(f"Skipping user {u_id} due to error: {e}")

    conn.commit()
    conn.close()

    if migrations:
        print("[Migration] Applied:")
        for m in migrations:
            print(f"  [OK] {m}")
    else:
        print("[Migration] Database is up to date.")

    return len(migrations)


if __name__ == "__main__":
    migrate()
    print("[Migration] Done.")
