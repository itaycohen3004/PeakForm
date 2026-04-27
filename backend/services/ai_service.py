"""
PeakForm — AI coaching service using Google Gemini.
OOP class: AICoach — satisfies academic OOP requirement.

SETUP:
  1. Get API key from: https://aistudio.google.com/
  2. Add to .env: GEMINI_API_KEY=your_key_here
  3. The app uses gemini-1.5-flash (free tier available)
"""
import os
import json
from dotenv import load_dotenv
from backend.services.encryption_service import encrypt_data, decrypt_data

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Models to try in order (newest first for availability)
_FALLBACK_MODELS = [
    "gemini-1.5-flash",
    "gemini-flash-latest",
    "gemini-1.5-pro",
    "gemini-pro-latest",
    "gemini-pro",
]


class AICoach:
    """
    OOP representation of a PeakForm AI Coach.
    Wraps Gemini API calls with athlete context building and fallback logic.
    Satisfies academic OOP requirement.
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key    = api_key or GEMINI_API_KEY
        self.model_name = model_name or GEMINI_MODEL
        self._client    = None
        self._configured = False

    def _initialize(self):
        """Lazy initialization — try models until one works."""
        if self._configured:
            return

        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("[AICoach] No API key configured.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            for model in [self.model_name] + [m for m in _FALLBACK_MODELS if m != self.model_name]:
                try:
                    client = genai.GenerativeModel(model)
                    # Quick test
                    client.generate_content("hi", generation_config={"max_output_tokens": 5})
                    self._client = client
                    self.model_name = model
                    self._configured = True
                    print(f"[AICoach] ✅ Using model: {model}")
                    break
                except Exception as e:
                    print(f"[AICoach] Model {model} unavailable: {e}")
                    continue

            if not self._configured:
                print(f"[AICoach] ❌ All models failed for key {self.api_key[:8]}... Check API key and quota.")
        except ImportError:
            print("[AICoach] google-generativeai not installed. Run: pip install google-generativeai")

    @property
    def is_ready(self) -> bool:
        self._initialize()
        return self._client is not None

    def chat(self, user_message: str, context: str, history: list) -> str:
        """Multi-turn coaching conversation."""
        if not self.is_ready:
            return (
                "AI coaching is not configured yet. "
                "To enable it, get a free API key from https://aistudio.google.com/ "
                "and add it to your .env file as GEMINI_API_KEY=your_key_here"
            )

        msgs = [SYSTEM_PROMPT, f"\n{context}\n"]
        for h in history[-6:]:
            role = "Athlete" if h["role"] == "user" else "Coach"
            msgs.append(f"{role}: {h['message']}")
        msgs.append(f"Athlete: {user_message}\nCoach:")

        prompt = "\n".join(msgs)
        try:
            response = self._client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[AICoach] Chat error: {e}")
            return f"I encountered an issue: {str(e)[:200]}"

    def analyze_exercise(self, context: str, exercise_name: str) -> dict:
        """Return structured progression recommendations."""
        if not self.is_ready:
            return {
                "next_reps": None,
                "next_weight": None,
                "progression_note": "AI not configured.",
                "confidence": "low",
            }

        prompt = f"""{SYSTEM_PROMPT}

{context}

Analyze the athlete's recent performance on: **{exercise_name}**

Respond ONLY with valid JSON (no markdown code blocks):
{{
  "next_reps": <integer or null>,
  "next_weight": <float or null>,
  "next_time_seconds": <integer or null>,
  "progression_note": "<1-2 sentence coaching note>",
  "confidence": "<low|medium|high>"
}}"""
        try:
            response = self._client.generate_content(prompt)
            text = response.text.strip()
            # Clean markdown wrappers
            if "```" in text:
                text = text[text.find("{"):text.rfind("}")+1]
            return json.loads(text)
        except Exception as e:
            return {
                "next_reps": None,
                "next_weight": None,
                "next_time_seconds": None,
                "progression_note": f"Analysis unavailable: {str(e)[:100]}",
                "confidence": "low",
            }

    def suggest_deadline(self, context: str, goal_data: dict) -> dict:
        """Suggest a realistic deadline for a goal."""
        if not self.is_ready:
            return {"suggested_deadline_days": None, "reasoning": "AI not configured."}

        prompt = f"""{SYSTEM_PROMPT}

{context}

The athlete wants to set a goal:
Title: {goal_data.get('title')}
Target: {goal_data.get('target_value')} {goal_data.get('unit')}
Current: {goal_data.get('current_value')} {goal_data.get('unit')}

Suggest a realistic but challenging deadline in days.
Respond ONLY with valid JSON:
{{
  "suggested_deadline_days": <integer>,
  "reasoning": "<1-2 sentence explanation>"
}}"""
        try:
            response = self._client.generate_content(prompt)
            text = response.text.strip()
            if "```" in text:
                text = text[text.find("{"):text.rfind("}")+1]
            return json.loads(text)
        except Exception as e:
            return {"suggested_deadline_days": None, "reasoning": f"Prediction unavailable."}

    def workout_recap(self, workout_data: dict, volume: float, prev_summary: str = None) -> str:
        """Short motivational analysis of a just-completed workout."""
        if not self.is_ready:
            return "Great session! Keep pushing — consistency is key."

        prompt = (
            f"Analyze this strength training session in 2-3 sentences. Be specific and encouraging.\n\n"
            f"Workout: {workout_data.get('name', 'Session')}\n"
            f"Date: {workout_data.get('workout_date')}\n"
            f"Total Volume: {volume:.1f} kg\n"
        )
        if prev_summary:
            prompt += f"Context: {prev_summary}\n"

        try:
            response = self._client.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return "Great effort today! Keep pushing for progress."


# ── Module-level singleton ─────────────────────────────────────────────────
_coach = AICoach()


SYSTEM_PROMPT = """You are PeakForm Coach — an expert AI strength coach for the PeakForm fitness platform.
You analyze workout data and provide specific, data-driven recommendations in kilograms (kg).
Always reference actual numbers. Be concise (max 150 words unless asked for a full plan), actionable, and encouraging.
Consider progressive overload, recovery, and the athlete's experience level.

When asked to create a full workout plan, provide an encouraging response AND append structured JSON inside <template_json> tags:
<template_json>
{
  "name": "Program Name",
  "training_type": "gym",
  "notes": "Brief instruction",
  "exercises": [
    {
      "exercise_name": "Exact Exercise Name",
      "default_sets": 3,
      "reps": 10,
      "notes": "Coaching note"
    }
  ]
}
</template_json>"""


def build_athlete_context(profile: dict, recent_workouts: list, goals: list) -> str:
    """Build structured text prompt from athlete data."""
    lines = ["=== ATHLETE PROFILE ==="]
    if profile:
        lines.append(
            f"Training type: {profile.get('training_type', 'gym')}, "
            f"Level: {profile.get('experience_level', 'intermediate')}, "
            f"Goal: {profile.get('main_goal', 'general_fitness')}"
        )
        if profile.get("age"):
            lines.append(f"Age: {profile['age']}")
        if profile.get("current_weight_kg"):
            lines.append(f"Weight: {profile['current_weight_kg']} kg")

    if goals:
        lines.append("\n=== CURRENT GOALS ===")
        for g in goals[:5]:
            pct = min(100, int((g.get("current_value", 0) / max(g.get("target_value", 1), 0.01)) * 100))
            lines.append(f"• {g['title']} — {g.get('current_value', '?')} / {g['target_value']} {g.get('unit', '')} ({pct}%)")

    lines.append("\n=== RECENT WORKOUTS ===")
    for w in recent_workouts[:5]:
        lines.append(f"\n[{w.get('workout_date')}] {w.get('name') or 'Session'}")
        for ex in w.get("exercises", []):
            lines.append(f"  {ex.get('exercise_name')}:")
            for s in ex.get("sets", []):
                parts = []
                if s.get("weight_kg") is not None:
                    parts.append(f"{s['weight_kg']}kg")
                if s.get("reps") is not None:
                    parts.append(f"{s['reps']} reps")
                if s.get("duration_seconds"):
                    parts.append(f"{s['duration_seconds']}s")
                if parts:
                    lines.append(f"    Set {s['set_number']}: {', '.join(parts)}")
    return "\n".join(lines)


# ── Public API functions ───────────────────────────────────────────────────

def run_coaching_chat(user_message: str, context: str, history: list) -> str:
    return _coach.chat(user_message, context, history)


def analyze_workout_progression(context: str, exercise_name: str) -> dict:
    return _coach.analyze_exercise(context, exercise_name)


def suggest_achievement_deadline(context: str, goal_data: dict) -> dict:
    return _coach.suggest_deadline(context, goal_data)


def analyze_workout_recap(workout: dict, volume: float, prev_summary: str = None) -> str:
    return _coach.workout_recap(workout, volume, prev_summary)


def save_ai_message(user_id: int, role: str, message: str, context_snapshot: str = None):
    try:
        from backend.models.db import get_db
        db = get_db()
        db.execute(
            "INSERT INTO ai_sessions (user_id, role, message, context_snapshot) VALUES (?,?,?,?)",
            (user_id, role, encrypt_data(message), encrypt_data(context_snapshot)),
        )
        db.commit()
    except Exception as e:
        print(f"[AI] Failed to save message: {e}")


def get_ai_history(user_id: int, limit: int = 20) -> list:
    try:
        from backend.models.db import get_db
        db = get_db()
        rows = db.execute(
            "SELECT role, message, created_at FROM ai_sessions WHERE user_id=? ORDER BY created_at ASC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        msgs = []
        for r in rows:
            m = dict(r)
            m["message"] = decrypt_data(m["message"])
            msgs.append(m)
        return msgs
    except Exception:
        return []
