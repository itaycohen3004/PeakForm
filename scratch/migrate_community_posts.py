import sqlite3
import os

db_path = os.path.join('database', 'peakform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Disable foreign keys temporarily
cursor.execute("PRAGMA foreign_keys = OFF;")
conn.commit()

# Create new table
cursor.execute("""
CREATE TABLE IF NOT EXISTS community_posts_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    post_type TEXT DEFAULT 'update' CHECK(post_type IN (
        'update','achievement','progress_photo','question','tip','template'
    )),
    media_path TEXT,
    likes_count INTEGER NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    meta_data TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
""")

# Copy data
cursor.execute("""
INSERT INTO community_posts_new (id, user_id, content, post_type, media_path, likes_count, is_deleted, created_at, meta_data)
SELECT id, user_id, content, post_type, media_path, likes_count, is_deleted, created_at, meta_data
FROM community_posts;
""")

# Drop old table and rename new table
cursor.execute("DROP TABLE community_posts;")
cursor.execute("ALTER TABLE community_posts_new RENAME TO community_posts;")

# Re-enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON;")
conn.commit()

print("Successfully migrated community_posts table.")
