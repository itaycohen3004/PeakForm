"""Reset admin password and fix profile."""
import sys
sys.path.insert(0, '.')
from backend.app import create_app
app = create_app()
with app.app_context():
    from backend.models.db import get_db
    from backend.services.auth_service import hash_password
    new_hash = hash_password('Admin@1234')
    db = get_db()
    db.execute(
        'UPDATE users SET password_hash=?, failed_attempts=0, is_locked=0 WHERE email=?',
        (new_hash, 'admin@peakform.app')
    )
    db.commit()
    profile = db.execute('SELECT * FROM athlete_profiles WHERE user_id=1').fetchone()
    if not profile:
        db.execute(
            'INSERT INTO athlete_profiles (user_id, display_name, training_type, experience_level, onboarding_complete) VALUES (?,?,?,?,?)',
            (1, 'PeakForm Admin', 'gym', 'advanced', 1)
        )
    else:
        db.execute('UPDATE athlete_profiles SET onboarding_complete=1 WHERE user_id=1')
    db.commit()
    print('Done. Admin password reset to Admin@1234')
