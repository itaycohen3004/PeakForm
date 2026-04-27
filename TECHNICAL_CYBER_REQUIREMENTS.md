# PeakForm Technical & Cyber Security Report

## 1. Object-Oriented Programming (OOP) Logic
The PeakForm backend implements a robust OOP architecture to manage complex lifting states and user lifecycles, satisfying academic and professional engineering standards.

### Key Models
- **`WorkoutSession` (`backend/models/workout.py`)**: Encapsulates the lifecycle of a training session. It manages exercise collections and set data. The `.finish()` method triggers a complex state transition where the system calculates total volume (kg), identifies targeted muscle groups, and updates athlete history.
- **`User` (`backend/models/user.py`)**: Handles account security, password reconciliation, and account locking logic.
- **`Athlete` (`backend/models/athlete.py`)**: Represents the physical profile and performance metrics of a specific user.

## 2. Cyber Security & Data Protection

### Password Security
- Passwords are never stored in plain text. PeakForm uses **Argon2/bcrypt-style hashing** via the `User` model to ensure that even a database breach does not expose user credentials.
- **Account Protection**: The system implements failed-attempt tracking to automatically lock accounts after multiple incorrect login attempts, preventing brute-force attacks.

### Data Encryption
- Sensitive personal data (Age, Height, Weight, Bio, etc.) is encrypted at rest using **AES-256 Symmetric Encryption** via the `encryption_service.py`.
- This ensures that personal athlete information is unreadable in the raw database export without the server's master key.

### Session Management
- Authentication is handled via **JWT (JSON Web Tokens)**.
- Secure, **HttpOnly, Secure, and SameSite=Lax** cookies prevent Cross-Site Scripting (XSS) and Cross-Site Request Forgery (CSRF) tokens from being stolen by malicious scripts.

## 3. Metric Calculations
- **Total Volume**: Calculated as `SUM(weight_kg * reps)` across all non-warmup sets.
- **Estimated 1RM**: Calculated using the Epley formula: `weight * (1 + reps / 30)`.
- **Muscle Targeting**: Workouts automatically tag muscle groups based on a many-to-many mapping in the `exercises` registry, visualized via a dynamic SVG HUD.

## 4. Infrastructure & Deployment
- **Port Strategy**: The application defaults to port **5001** to avoid common developer conflicts (e.g., Apple AirPlay, local DBs).
- **SSL/TLS**: The system supports `adhoc` SSL contexts for secure local development and production-ready `https` deployments.
- **Persistence**: SQLite-backed SQL persistence with automatic `migrate.py` logic for schema evolution.
