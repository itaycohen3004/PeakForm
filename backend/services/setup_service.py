"""
setup_service.py — Automatic system initialization.
Handles auto-admin creation on first run.
"""
import os
from backend.models.db import get_db_direct
from backend.services.auth_service import hash_password
from backend.models.user import find_user_by_email, create_user
from backend.models.athlete import create_athlete_profile

def ensure_admin_exists():
    """Checks if any admin exists. If not, creates the default one from .env."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@peakform.app")
    admin_pass  = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    user = find_user_by_email(admin_email)
    if not user:
        print(f"🛠  No admin found. Creating default admin: {admin_email}")
        try:
            user_id = create_user(admin_email, hash_password(admin_pass), "admin")
            create_athlete_profile(
                user_id, 
                "System Admin", 
                training_type="gym"
            )
            # Mark onboarding as complete for admin
            db = get_db_direct()
            db.execute("UPDATE athlete_profiles SET onboarding_complete = 1 WHERE user_id = ?", (user_id,))
            db.commit()
            print(f"✅ Default admin created successfully.")
        except Exception as e:
            print(f"❌ Error creating default admin: {e}")
    else:
        # Ensure it has admin role if it already exists (e.g. from previous run)
        if user["role"] != "admin":
             print(f"⚠️ User {admin_email} exists but is not an admin. Updating role...")
             db = get_db_direct()
             db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user["id"],))
             db.commit()
