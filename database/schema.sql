-- PeakForm — Strength Training Platform
-- SQLite Schema

PRAGMA foreign_keys = ON;

-- ============================================================
-- AUTH
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    email_index TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'athlete' CHECK(role IN ('athlete','admin')),
    is_locked INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS two_factor_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- ATHLETE PROFILES
-- ============================================================

CREATE TABLE IF NOT EXISTS athlete_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    training_type TEXT DEFAULT 'gym' CHECK(training_type IN (
        'gym','calisthenics','hybrid','home','functional','other'
    )),
    age INTEGER,
    gender TEXT CHECK(gender IN ('male','female','other')),
    height_cm REAL,
    current_weight_kg REAL,
    target_weight_kg REAL,
    experience_level TEXT DEFAULT 'intermediate' CHECK(experience_level IN (
        'beginner','intermediate','advanced','elite'
    )),
    main_goal TEXT DEFAULT 'general_fitness' CHECK(main_goal IN (
        'build_muscle','strength','fat_loss','general_fitness'
    )),
    days_per_week INTEGER DEFAULT 3,
    bio TEXT,
    avatar_url TEXT,
    onboarding_complete INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- EXERCISE LIBRARY
-- ============================================================

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK(category IN (
        'chest','back','shoulders','arms','legs','core','full_body','skill','cardio'
    )),
    set_type TEXT NOT NULL DEFAULT 'reps_weight' CHECK(set_type IN (
        'reps_weight','reps_only','time_only','time_weight'
    )),
    muscles TEXT,
    muscles_secondary TEXT,
    equipment TEXT,
    training_styles TEXT DEFAULT 'gym,hybrid',
    is_custom INTEGER NOT NULL DEFAULT 0,
    created_by INTEGER,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_exercises_category ON exercises(category);
CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises(name);

-- ============================================================
-- WORKOUT TEMPLATES
-- ============================================================

CREATE TABLE IF NOT EXISTS workout_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    training_type TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS template_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    default_sets INTEGER DEFAULT 3,
    default_reps INTEGER,
    notes TEXT,
    FOREIGN KEY (template_id) REFERENCES workout_templates(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS template_exercise_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    target_reps INTEGER,
    target_weight REAL,
    target_seconds INTEGER,
    FOREIGN KEY (template_exercise_id) REFERENCES template_exercises(id) ON DELETE CASCADE
);

-- ============================================================
-- WEEKLY SCHEDULE
-- ============================================================

CREATE TABLE IF NOT EXISTS weekly_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    template_id INTEGER NOT NULL,
    weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
    UNIQUE(user_id, weekday),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES workout_templates(id) ON DELETE CASCADE
);

-- ============================================================
-- WORKOUT SESSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    template_id INTEGER,
    name TEXT,
    workout_date DATE NOT NULL,
    started_at DATETIME,
    finished_at DATETIME,
    duration_minutes INTEGER,
    total_sets INTEGER DEFAULT 0,
    total_reps INTEGER DEFAULT 0,
    total_volume_kg REAL DEFAULT 0,
    muscles_worked TEXT,
    notes TEXT,
    is_draft INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES workout_templates(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON workouts(user_id, workout_date);

CREATE TABLE IF NOT EXISTS workout_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workout_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    reps INTEGER,
    weight_kg REAL,
    duration_seconds INTEGER,
    is_warmup INTEGER NOT NULL DEFAULT 0,
    is_failure INTEGER NOT NULL DEFAULT 0,
    rpe REAL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workout_exercise_id) REFERENCES workout_exercises(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise ON workout_sets(workout_exercise_id);

-- ============================================================
-- PERSONAL RECORDS
-- ============================================================

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
);

-- ============================================================
-- BODY WEIGHT TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS body_weight_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    weight_kg REAL NOT NULL,
    photo_path TEXT,
    notes TEXT,
    logged_at DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_body_weight_user ON body_weight_logs(user_id, logged_at);

-- ============================================================
-- GOALS
-- ============================================================

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    goal_type TEXT NOT NULL CHECK(goal_type IN (
        'exercise_weight',
        'exercise_reps',
        'exercise_1rm',
        'weekly_frequency',
        'body_weight_target',
        'workout_count',
        'volume_target',
        'streak_days',
        'custom'
    )),
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
);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    action_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);

-- ============================================================
-- COMMUNITY FEED
-- ============================================================

CREATE TABLE IF NOT EXISTS community_posts (
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

CREATE TABLE IF NOT EXISTS community_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS community_likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- GROUP CHAT (SocketIO)
-- ============================================================

CREATE TABLE IF NOT EXISTS chat_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    room_type TEXT DEFAULT 'public' CHECK(room_type IN ('public','private')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_room_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    nickname TEXT,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(room_id, user_id),
    FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    message TEXT NOT NULL,
    is_reported INTEGER NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_room ON chat_messages(room_id, sent_at);

-- ============================================================
-- AI COACH SESSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    message TEXT NOT NULL,
    context_snapshot TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- AUDIT LOGS
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- SEED DATA — Exercise Library
-- ============================================================

-- CHEST
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Barbell Bench Press', 'chest', 'reps_weight', 'chest,triceps', 'barbell,bench', 'gym,hybrid'),
('Dumbbell Bench Press', 'chest', 'reps_weight', 'chest,triceps', 'dumbbells,bench', 'gym,hybrid,home'),
('Incline Barbell Press', 'chest', 'reps_weight', 'upper chest,triceps', 'barbell,incline bench', 'gym'),
('Incline Dumbbell Press', 'chest', 'reps_weight', 'upper chest,triceps', 'dumbbells,incline bench', 'gym,hybrid'),
('Decline Bench Press', 'chest', 'reps_weight', 'lower chest,triceps', 'barbell,decline bench', 'gym'),
('Cable Fly', 'chest', 'reps_weight', 'chest', 'cable machine', 'gym'),
('Dumbbell Fly', 'chest', 'reps_weight', 'chest', 'dumbbells,bench', 'gym,hybrid,home'),
('Push-up', 'chest', 'reps_only', 'chest,triceps,shoulders', 'bodyweight', 'home,calisthenics,hybrid,gym'),
('Weighted Push-up', 'chest', 'reps_weight', 'chest,triceps', 'bodyweight,weight plate', 'calisthenics,hybrid'),
('Chest Dip', 'chest', 'reps_only', 'lower chest,triceps', 'dip bars', 'gym,calisthenics,hybrid'),
('Weighted Chest Dip', 'chest', 'reps_weight', 'lower chest,triceps', 'dip bars,belt', 'gym,calisthenics'),
('Pec Deck Machine', 'chest', 'reps_weight', 'chest', 'pec deck machine', 'gym'),
('Machine Chest Press', 'chest', 'reps_weight', 'chest,triceps', 'chest press machine', 'gym'),
('Svend Press', 'chest', 'reps_weight', 'inner chest', 'weight plate', 'gym,hybrid');

-- BACK
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Pull-up', 'back', 'reps_only', 'lats,biceps', 'pull-up bar', 'calisthenics,hybrid,gym,home'),
('Weighted Pull-up', 'back', 'reps_weight', 'lats,biceps', 'pull-up bar,belt', 'calisthenics,gym'),
('Chin-up', 'back', 'reps_only', 'lats,biceps', 'pull-up bar', 'calisthenics,hybrid,gym,home'),
('Weighted Chin-up', 'back', 'reps_weight', 'lats,biceps', 'pull-up bar,belt', 'calisthenics,gym'),
('Barbell Row', 'back', 'reps_weight', 'lats,rhomboids,biceps', 'barbell', 'gym'),
('Dumbbell Row', 'back', 'reps_weight', 'lats,rhomboids', 'dumbbell,bench', 'gym,hybrid,home'),
('Cable Row', 'back', 'reps_weight', 'lats,rhomboids', 'cable machine', 'gym'),
('Lat Pulldown', 'back', 'reps_weight', 'lats,biceps', 'cable machine', 'gym'),
('T-Bar Row', 'back', 'reps_weight', 'lats,rhomboids', 't-bar', 'gym'),
('Deadlift', 'back', 'reps_weight', 'entire back,glutes,hamstrings', 'barbell', 'gym,hybrid'),
('Romanian Deadlift', 'back', 'reps_weight', 'hamstrings,glutes,lower back', 'barbell', 'gym,hybrid'),
('Face Pull', 'back', 'reps_weight', 'rear delts,rhomboids', 'cable machine', 'gym'),
('Shrug', 'back', 'reps_weight', 'traps', 'barbell,dumbbells', 'gym,hybrid'),
('Hyperextension', 'back', 'reps_only', 'lower back,glutes', 'hyperextension bench', 'gym'),
('Pendlay Row', 'back', 'reps_weight', 'lats,rhomboids', 'barbell', 'gym'),
('Meadows Row', 'back', 'reps_weight', 'lats', 'barbell', 'gym');

-- SHOULDERS
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Overhead Press', 'shoulders', 'reps_weight', 'shoulders,triceps', 'barbell', 'gym,hybrid'),
('Dumbbell Shoulder Press', 'shoulders', 'reps_weight', 'shoulders,triceps', 'dumbbells', 'gym,hybrid,home'),
('Lateral Raise', 'shoulders', 'reps_weight', 'lateral delts', 'dumbbells', 'gym,hybrid,home'),
('Cable Lateral Raise', 'shoulders', 'reps_weight', 'lateral delts', 'cable machine', 'gym'),
('Front Raise', 'shoulders', 'reps_weight', 'front delts', 'dumbbells,barbell', 'gym,hybrid,home'),
('Rear Delt Fly', 'shoulders', 'reps_weight', 'rear delts', 'dumbbells,cable', 'gym,hybrid,home'),
('Arnold Press', 'shoulders', 'reps_weight', 'full shoulder', 'dumbbells', 'gym,hybrid,home'),
('Upright Row', 'shoulders', 'reps_weight', 'traps,lateral delts', 'barbell,cable', 'gym,hybrid'),
('Pike Push-up', 'shoulders', 'reps_only', 'shoulders,triceps', 'bodyweight', 'home,calisthenics,hybrid'),
('Handstand Push-up', 'shoulders', 'reps_only', 'shoulders,triceps', 'bodyweight,wall', 'calisthenics,hybrid'),
('Weighted Handstand Push-up', 'shoulders', 'reps_weight', 'shoulders,triceps', 'bodyweight,belt', 'calisthenics'),
('Machine Shoulder Press', 'shoulders', 'reps_weight', 'shoulders', 'shoulder press machine', 'gym');

-- ARMS
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Barbell Curl', 'arms', 'reps_weight', 'biceps', 'barbell', 'gym,hybrid'),
('Dumbbell Curl', 'arms', 'reps_weight', 'biceps', 'dumbbells', 'gym,hybrid,home'),
('Hammer Curl', 'arms', 'reps_weight', 'biceps,brachialis', 'dumbbells', 'gym,hybrid,home'),
('Preacher Curl', 'arms', 'reps_weight', 'biceps', 'barbell,preacher bench', 'gym'),
('Cable Curl', 'arms', 'reps_weight', 'biceps', 'cable machine', 'gym'),
('Incline Dumbbell Curl', 'arms', 'reps_weight', 'long head biceps', 'dumbbells,incline bench', 'gym,hybrid'),
('Concentration Curl', 'arms', 'reps_weight', 'biceps', 'dumbbell', 'gym,hybrid,home'),
('Tricep Pushdown', 'arms', 'reps_weight', 'triceps', 'cable machine', 'gym'),
('Overhead Tricep Extension', 'arms', 'reps_weight', 'triceps', 'dumbbell,cable,barbell', 'gym,hybrid,home'),
('Skull Crusher', 'arms', 'reps_weight', 'triceps', 'barbell,EZ bar', 'gym,hybrid'),
('Tricep Dip', 'arms', 'reps_only', 'triceps,chest', 'parallel bars', 'gym,calisthenics,hybrid'),
('Close-Grip Bench Press', 'arms', 'reps_weight', 'triceps,chest', 'barbell', 'gym'),
('Diamond Push-up', 'arms', 'reps_only', 'triceps', 'bodyweight', 'home,calisthenics,hybrid'),
('Wrist Curl', 'arms', 'reps_weight', 'forearms', 'barbell,dumbbell', 'gym,hybrid');

-- LEGS
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Barbell Squat', 'legs', 'reps_weight', 'quads,glutes,hamstrings', 'barbell,squat rack', 'gym'),
('Front Squat', 'legs', 'reps_weight', 'quads,core', 'barbell', 'gym'),
('Goblet Squat', 'legs', 'reps_weight', 'quads,glutes', 'dumbbell,kettlebell', 'gym,hybrid,home'),
('Leg Press', 'legs', 'reps_weight', 'quads,glutes,hamstrings', 'leg press machine', 'gym'),
('Hack Squat', 'legs', 'reps_weight', 'quads', 'hack squat machine', 'gym'),
('Bulgarian Split Squat', 'legs', 'reps_weight', 'quads,glutes', 'dumbbells,bench', 'gym,hybrid,home'),
('Lunge', 'legs', 'reps_weight', 'quads,glutes', 'dumbbells,barbell', 'gym,hybrid,home'),
('Step-up', 'legs', 'reps_weight', 'quads,glutes', 'box,dumbbells', 'gym,hybrid,home'),
('Leg Extension', 'legs', 'reps_weight', 'quads', 'leg extension machine', 'gym'),
('Leg Curl', 'legs', 'reps_weight', 'hamstrings', 'leg curl machine', 'gym'),
('Nordic Hamstring Curl', 'legs', 'reps_only', 'hamstrings', 'anchored', 'gym,calisthenics,home'),
('Hip Thrust', 'legs', 'reps_weight', 'glutes', 'barbell,bench', 'gym,hybrid'),
('Calf Raise', 'legs', 'reps_weight', 'calves', 'barbell,smith machine', 'gym,hybrid'),
('Seated Calf Raise', 'legs', 'reps_weight', 'soleus', 'seated calf raise machine', 'gym'),
('Pistol Squat', 'legs', 'reps_only', 'quads,balance', 'bodyweight', 'calisthenics,hybrid,home'),
('Sumo Deadlift', 'legs', 'reps_weight', 'glutes,adductors,hamstrings', 'barbell', 'gym');

-- CORE
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Plank', 'core', 'time_only', 'core,transverse abdominis', 'bodyweight', 'gym,calisthenics,hybrid,home'),
('Side Plank', 'core', 'time_only', 'obliques,core', 'bodyweight', 'gym,calisthenics,hybrid,home'),
('Weighted Plank', 'core', 'time_weight', 'core', 'bodyweight,weight plate', 'gym,hybrid'),
('Ab Wheel Rollout', 'core', 'reps_only', 'core,lats', 'ab wheel', 'gym,home'),
('Hanging Leg Raise', 'core', 'reps_only', 'lower abs,hip flexors', 'pull-up bar', 'gym,calisthenics,hybrid'),
('Cable Crunch', 'core', 'reps_weight', 'abs', 'cable machine', 'gym'),
('Russian Twist', 'core', 'reps_weight', 'obliques', 'weight plate,med ball', 'gym,hybrid,home'),
('Dragon Flag', 'core', 'reps_only', 'full core', 'bench', 'gym,calisthenics'),
('L-Sit', 'core', 'time_only', 'core,hip flexors', 'parallel bars,rings', 'calisthenics,gym'),
('Hollow Body Hold', 'core', 'time_only', 'core', 'bodyweight', 'calisthenics,hybrid,home'),
('Dead Bug', 'core', 'reps_only', 'core,stability', 'bodyweight', 'gym,hybrid,home'),
('Crunch', 'core', 'reps_only', 'abs', 'bodyweight', 'gym,hybrid,home'),
('Bicycle Crunch', 'core', 'reps_only', 'obliques,abs', 'bodyweight', 'gym,hybrid,home'),
('Reverse Crunch', 'core', 'reps_only', 'lower abs', 'bodyweight', 'gym,hybrid,home'),
('Pallof Press', 'core', 'reps_weight', 'anti-rotation core', 'cable machine', 'gym');

-- CALISTHENICS SKILLS
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Front Lever', 'skill', 'time_only', 'lats,core,biceps', 'pull-up bar,rings', 'calisthenics'),
('Back Lever', 'skill', 'time_only', 'chest,lats,core', 'rings,bar', 'calisthenics'),
('Planche', 'skill', 'time_only', 'shoulders,chest,core', 'bodyweight', 'calisthenics'),
('Tuck Planche', 'skill', 'time_only', 'shoulders,core', 'bodyweight,parallettes', 'calisthenics'),
('Handstand', 'skill', 'time_only', 'shoulders,core,balance', 'bodyweight,wall', 'calisthenics,hybrid'),
('Muscle-up', 'skill', 'reps_only', 'lats,chest,triceps', 'pull-up bar,rings', 'calisthenics'),
('Ring Dip', 'skill', 'reps_only', 'triceps,chest,stability', 'rings', 'calisthenics'),
('Ring Push-up', 'skill', 'reps_only', 'chest,core,stability', 'rings', 'calisthenics'),
('Archer Pull-up', 'back', 'reps_only', 'lats,biceps (unilateral)', 'wide bar', 'calisthenics'),
('One-Arm Pull-up', 'back', 'reps_only', 'lats,biceps (unilateral)', 'pull-up bar', 'calisthenics'),
('Ring Rows', 'back', 'reps_only', 'lats,rhomboids', 'rings', 'calisthenics,hybrid');

-- FULL BODY
INSERT OR IGNORE INTO exercises (name, category, set_type, muscles, equipment, training_styles) VALUES
('Kettlebell Swing', 'full_body', 'reps_weight', 'glutes,hamstrings,core,shoulders', 'kettlebell', 'gym,hybrid,home'),
('Turkish Get-up', 'full_body', 'reps_weight', 'full body,shoulder stability', 'kettlebell', 'gym,hybrid'),
('Clean and Press', 'full_body', 'reps_weight', 'full body', 'barbell,dumbbell', 'gym'),
('Thruster', 'full_body', 'reps_weight', 'legs,shoulders,triceps', 'barbell,dumbbells', 'gym,hybrid'),
('Farmer Carry', 'full_body', 'time_weight', 'grip,traps,core,legs', 'dumbbells,trap bar', 'gym,hybrid'),
('Sled Push', 'full_body', 'time_weight', 'legs,core', 'weighted sled', 'gym'),
('Box Jump', 'full_body', 'reps_only', 'legs,explosiveness', 'plyometric box', 'gym,hybrid'),
('Burpee', 'full_body', 'reps_only', 'full body,conditioning', 'bodyweight', 'home,calisthenics,hybrid,gym');

-- SEED DATA — Chat Rooms
INSERT OR IGNORE INTO chat_rooms (name, description, room_type) VALUES
('General', 'Main community chat — talk training, ask questions, share wins.', 'public'),
('Gym Training', 'Dedicated to barbell lifting, machines, and gym-based strength.', 'public'),
('Calisthenics', 'Skills, progressions, and bodyweight training discussions.', 'public'),
('Progress & PRs', 'Share your personal records and weight milestones here!', 'public');

/*
English Summary:
This is the foundational database schema definition file. It contains the raw SQL commands 
to construct all the core tables, indexes, and relationships for the PeakForm application, 
including authentication, workouts, chat, notifications, and AI logs. It also seeds initial 
data for the exercise library and default chat rooms.

סיכום בעברית:
קובץ זה הוא התוכנית האדריכלית (השרטוט) של מסד הנתונים. כאן רשומות פקודות ה-SQL 
שבונות את כל ה"טבלאות" במערכת - החל מטבלת משתמשים, דרך אימונים ומטרות, ועד 
להודעות צ'אט. בנוסף, הקובץ מכניס מראש רשימה ענקית של עשרות תרגילי כושר (Seed Data)
כדי שכשהמערכת עולה בפעם הראשונה, לספריית התרגילים כבר יהיה תוכן עשיר להציע למתאמן!
*/
