import os

import requests
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

from db import (
    get_daily_devotionals,
    get_journal_entries,
    get_prayer_requests,
    save_daily_devotional,
    save_journal_entry,
    save_prayer_request,
)

load_dotenv()

app = Flask(__name__, static_folder="public/static", static_url_path="/static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
app.config["ADMIN_EMAIL"] = os.getenv("ADMIN_EMAIL", "").strip().lower()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def is_admin_user() -> bool:
    user = session.get("user") or {}
    email = user.get("email", "").strip().lower()
    return bool(app.config["ADMIN_EMAIL"] and email == app.config["ADMIN_EMAIL"])


def is_supabase_configured() -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False

    url = SUPABASE_URL.lower()
    key = SUPABASE_KEY.lower()

    if "your-project.supabase.co" in url:
        return False
    if "your-" in key or "change-me" in key:
        return False

    return True


def supabase_auth_request(method: str, path: str, payload: dict | None = None, access_token: str | None = None):
    if not is_supabase_configured():
        return {"ok": False, "message": "Supabase is not configured yet. Add SUPABASE_URL and SUPABASE_KEY to your .env file."}

    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        response = requests.request(method, f"{SUPABASE_URL}{path}", headers=headers, json=payload, timeout=30)
        data = response.json() if response.content else {}

        if response.status_code >= 400:
            error_message = data.get("error", {}).get("message") or data.get("msg") or "Authentication failed."
            return {"ok": False, "message": error_message}

        return {"ok": True, "data": data}
    except Exception as exc:  # pragma: no cover - external API dependency
        return {"ok": False, "message": str(exc)}


def generate_gemini_reply(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini is not configured yet. Add GEMINI_API_KEY to your .env file to enable AI chat."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:  # pragma: no cover - external API dependency
        return f"I couldn't reach Gemini right now. Please check your API key and network connection. Details: {exc}"


@app.route("/")
def index():
    devotional_rows = get_daily_devotionals(limit=1)
    if devotional_rows:
        row = devotional_rows[0]
        devotional = {
            "title": row.get("title") or "Grace Daily",
            "verse": row.get("verse") or "Let the morning bring me word of your unfailing love, for I have put my trust in you.",
            "reference": row.get("date") or "Daily reflection",
            "message": row.get("body") or "Start the day with quiet faith, gratitude, and one courageous step toward the life God is calling you to live.",
        }
    else:
        devotional = {
            "title": "Grace Daily",
            "verse": "Let the morning bring me word of your unfailing love, for I have put my trust in you.",
            "reference": "Psalm 143:8",
            "message": "Start the day with quiet faith, gratitude, and one courageous step toward the life God is calling you to live.",
        }

    entries = get_journal_entries(limit=5)
    prayers = get_prayer_requests(limit=5)
    return render_template("index.html", devotional=devotional, entries=entries, prayers=prayers)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user"):
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("auth.html", mode="signup")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("auth.html", mode="signup")

        result = supabase_auth_request("POST", "/auth/v1/signup", {"email": email, "password": password})
        if not result["ok"]:
            flash(result["message"], "error")
            return render_template("auth.html", mode="signup")

        session["user"] = {"email": email}
        session["access_token"] = result["data"].get("access_token")
        session["refresh_token"] = result["data"].get("refresh_token")
        flash("Your account has been created. Welcome!", "success")
        return redirect(url_for("index"))

    return render_template("auth.html", mode="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("auth.html", mode="login")

        result = supabase_auth_request(
            "POST",
            "/auth/v1/token",
            {"email": email, "password": password, "grant_type": "password"},
        )

        if not result["ok"]:
            flash(result["message"], "error")
            return render_template("auth.html", mode="login")

        session["user"] = {"email": email}
        session["access_token"] = result["data"].get("access_token")
        session["refresh_token"] = result["data"].get("refresh_token")
        flash("You are now logged in.", "success")
        return redirect(url_for("index"))

    return render_template("auth.html", mode="login")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/journal", methods=["GET", "POST"])
def journal():
    if request.method == "POST":
        name = request.form.get("name", "Anonymous").strip()
        reflection = request.form.get("reflection", "").strip()

        if not reflection:
            flash("Please write a reflection before submitting.", "error")
            return redirect(url_for("journal"))

        save_journal_entry(name=name, reflection=reflection)
        flash("Your reflection was saved.", "success")
        return redirect(url_for("journal"))

    entries = get_journal_entries()
    return render_template("journal.html", entries=entries)


@app.route("/prayer", methods=["GET", "POST"])
def prayer():
    if request.method == "POST":
        name = request.form.get("name", "Anonymous").strip()
        request_text = request.form.get("request", "").strip()

        if not request_text:
            flash("Please share your prayer request.", "error")
            return redirect(url_for("prayer"))

        save_prayer_request(name=name, request=request_text)
        flash("Your prayer request was shared.", "success")
        return redirect(url_for("prayer"))

    prayers = get_prayer_requests()
    return render_template("prayer.html", prayers=prayers)


@app.route("/ai-chat", methods=["GET", "POST"])
def ai_chat():
    if "chat_history" not in session:
        session["chat_history"] = []

    if request.method == "POST":
        user_message = request.form.get("message", "").strip()
        if not user_message:
            flash("Please type a message before sending.", "error")
            return redirect(url_for("ai_chat"))

        session["chat_history"].append({"role": "user", "text": user_message})
        ai_response = generate_gemini_reply(
            "You are a warm, faith-centered devotional assistant. Respond with pastoral and philosophical encouragement and a short devotional tone. User message: "
            + user_message
        )
        session["chat_history"].append({"role": "assistant", "text": ai_response})
        session.modified = True
        return redirect(url_for("ai_chat"))

    history = session.get("chat_history", [])
    return render_template("ai_chat.html", history=history)


@app.route("/admin/devotionals", methods=["GET", "POST"])
def admin_devotionals():
    if not is_admin_user():
        flash("Admin access is not configured for this account.", "error")
        return redirect(url_for("login" if not session.get("user") else "index"))

    if request.method == "POST":
        date_value = request.form.get("date", "").strip()
        title = request.form.get("title", "").strip()
        verse = request.form.get("verse", "").strip()
        body = request.form.get("body", "").strip()

        if not all([date_value, title, verse, body]):
            flash("Please fill in date, title, verse, and body.", "error")
            return redirect(url_for("admin_devotionals"))

        save_daily_devotional(title=title, verse=verse, body=body, date=date_value)
        flash("Devotional post saved successfully.", "success")
        return redirect(url_for("admin_devotionals"))

    devotionals = get_daily_devotionals(limit=10)
    return render_template("admin_devotionals.html", devotionals=devotionals)


if __name__ == "__main__":
    app.run(debug=True)
