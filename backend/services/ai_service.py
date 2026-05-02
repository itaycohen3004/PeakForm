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

load_dotenv('config.env')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_SECONDARY_API_KEY = os.getenv("GEMINI_SECONDARY_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

print(f"[AICoach] API key loaded: {'YES ('+GEMINI_API_KEY[:8]+'...)' if GEMINI_API_KEY else 'NO — set GEMINI_API_KEY in .env'}")
print(f"[AICoach] Secondary API key loaded: {'YES' if GEMINI_SECONDARY_API_KEY else 'NO'}")
print(f"[AICoach] Preferred model: {GEMINI_MODEL}")

# Models to try in order — gemini-1.5-flash is the most reliable free-tier model
_FALLBACK_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash"
]

import google.generativeai as genai
import traceback

class AICoach:
    """
    OOP representation of a PeakForm AI Coach.
    Wraps Gemini API calls with athlete context building and fallback logic.
    Satisfies academic OOP requirement.
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key    = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.secondary_key = os.getenv("GEMINI_SECONDARY_API_KEY")
        
        self.active_key = self.api_key
        self.model_name = model_name or GEMINI_MODEL
        self._client    = None
        self._configured = False
        self._last_error = ""
        
        # Fallback tracking
        self.available_models = ["gemini-2.0-flash"] + [m for m in _FALLBACK_MODELS if m != "gemini-2.0-flash"]
        self.current_model_index = 0

        # As requested: check if GOOGLE_API_KEY or GEMINI_API_KEY is actually being loaded
        key_to_log = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if key_to_log:
            print(f"Using API Key: {key_to_log[:10]}...")
        else:
            print("Using API Key: None found in env! Using fallback.")

    def _initialize(self):
        """Lazy initialization — prepare the first available model."""
        if self._configured:
            return

        if not self.active_key or self.active_key == "your_gemini_api_key_here":
            print("[AICoach] ❌ No valid API key. Set GEMINI_API_KEY in .env")
            self._last_error = "No API key configured."
            return

        print(f"[AICoach] Initializing with key={self.active_key[:8]}... preferred={self.model_name}")
        try:
            genai.configure(api_key=self.active_key)
            self.model_name = self.available_models[self.current_model_index]
            self._client = genai.GenerativeModel(self.model_name)
            self._configured = True
            self._last_error = ""
            print(f"[AICoach] ✅ Configured with initial model: {self.model_name}")
        except Exception as e:
            print(f"[AICoach] ❌ Unexpected init error: {e}")
            print(traceback.format_exc())
            self._last_error = str(e)

    def _failover(self) -> bool:
        """Switch to next model or secondary API key. Returns True if failover successful."""
        # Try next model first
        self.current_model_index += 1
        if self.current_model_index < len(self.available_models):
            next_model = self.available_models[self.current_model_index]
            print(f"[AICoach] 🔄 Switching to fallback model: {next_model}")
            self.model_name = next_model
            self._client = genai.GenerativeModel(self.model_name)
            return True
            
        # If all models exhausted for this key, try secondary key
        if self.active_key == self.api_key and self.secondary_key:
            print("[AICoach] 🔄 Primary API key models exhausted. Switching to secondary API key.")
            self.active_key = self.secondary_key
            genai.configure(api_key=self.active_key)
            self.current_model_index = 0
            self.model_name = self.available_models[self.current_model_index]
            self._client = genai.GenerativeModel(self.model_name)
            return True
            
        return False

    def _generate_with_fallback(self, prompt: str):
        """Wrapper to handle 429 quotas by falling back to other models or a secondary API key."""
        if not self.is_ready:
            raise Exception(f"AI not configured: {self._last_error}")
            
        max_attempts = len(self.available_models) * (2 if self.secondary_key else 1)
        attempts = 0
        
        while attempts < max_attempts:
            try:
                response = self._client.generate_content(prompt)
                return response
            except Exception as e:
                err_str = str(e)
                attempts += 1
                if "429" in err_str or "quota" in err_str.lower() or "exhausted" in err_str.lower():
                    print(f"[AICoach] ⚠️ Quota exceeded on {self.model_name} (Key: {self.active_key[:8]}).")
                    if self._failover():
                        continue
                    else:
                        raise Exception("All fallback models and API keys have exhausted their quotas.")
                elif "403" in err_str or "400" in err_str:
                    print(f"[AICoach] 🚨 403/400 Error: {err_str}")
                    raise
                else:
                    raise
        raise Exception("Maximum fallback attempts reached.")

    @property
    def is_ready(self) -> bool:
        self._initialize()
        return self._client is not None

    def chat(self, user_message: str, context: str, history: list) -> str:
        """Multi-turn coaching conversation."""
        print(f"[AICoach] chat() called. is_ready={self._client is not None}")
        if not self.is_ready:
            msg = f"AI coaching failed to start. Internal Error: {self._last_error}"
            print(f"[AICoach] Not ready — returning fallback message")
            return msg

        msgs = [SYSTEM_PROMPT, f"\n{context}\n"]
        for h in history[-6:]:
            role = "Athlete" if h["role"] == "user" else "Coach"
            msgs.append(f"{role}: {h['message']}")
        msgs.append(f"Athlete: {user_message}\nCoach:")

        prompt = "\n".join(msgs)
        try:
            print(f"[AICoach] Sending prompt ({len(prompt)} chars)")
            response = self._generate_with_fallback(prompt)
            reply = response.text.strip()
            print(f"[AICoach] Got reply ({len(reply)} chars)")
            return reply
        except Exception as e:
            err_str = str(e)
            print(f"[AICoach] Chat error: {err_str}")
            print(traceback.format_exc())
            if "quota" in err_str.lower() or "exhausted" in err_str.lower():
                return f"I'm temporarily unavailable due to API quota limits across all backup models. Please try again later."
            elif "403" in err_str or "400" in err_str:
                return f"Region/Proxy Restriction Error (403/400): {err_str}"
            return f"I encountered an API issue. Error details: {err_str}"

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
            response = self._generate_with_fallback(prompt)
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
            response = self._generate_with_fallback(prompt)
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
            response = self._generate_with_fallback(prompt)
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
