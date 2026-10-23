
import os
import uuid
import sqlite3
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


# =============== 1. Configuration ====================

st.set_page_config(
    page_title="JeevanRaksha AI",
    page_icon="🛟",
    layout="wide",
)

load_dotenv()

API_KEY = st.secrets.get("GNANI_API_KEY", os.getenv("GNANI_API_KEY"))
DB = "jeevanraksha.db"

LANGUAGES = {
    "Hindi": "hi-IN",
    "English": "en-IN",
    "Bengali": "bn-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Kannada": "kn-IN",
    "Marathi": "mr-IN",
    "Gujarati": "gu-IN",
    "Punjabi": "pa-IN",
    "Malayalam": "ml-IN",
}

CATEGORIES = ["Rescue", "Medical", "Food & Water", "Shelter", "Other"]
URGENCIES = ["Critical", "High", "Medium", "Low"]
STATUSES = ["Pending", "Assigned", "Resolved"]


# =============== 2. UI Styling ====================

st.markdown("""
<style>
.hero {
    position: relative;
    overflow: hidden;
    padding: 30px 32px;
    border-radius: 12px;
    margin-bottom: 24px;
    color: #f5f7f4;
    background-color: #244b40;
    background-image:
        radial-gradient(circle at 85% 30%,
            rgba(255,255,255,0.07) 0, transparent 35%),
        repeating-linear-gradient(0deg,
            rgba(255,255,255,0.018) 0px,
            rgba(255,255,255,0.018) 1px,
            transparent 1px, transparent 4px),
        linear-gradient(115deg, #203f36 0%, #2b5548 100%);
    border: 1px solid rgba(255,255,255,0.10);
    box-shadow: 0 2px 8px rgba(20,45,35,0.08);
}
.hero::after {
    content: "✚";
    position: absolute;
    right: 48px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 150px;
    font-weight: 300;
    line-height: 1;
    color: rgba(255,255,255,0.045);
    pointer-events: none;
}
.hero h1 {
    position: relative;
    z-index: 1;
    color: #f5f7f4;
    font-size: 30px;
    font-weight: 600;
    letter-spacing: -0.6px;
    margin: 0 0 8px 0;
}
.hero p {
    position: relative;
    z-index: 1;
    color: #d0ded6;
    font-size: 14px;
    margin: 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🛟 JeevanRaksha AI</h1>
    <p>Disaster relief coordination · Multilingual voice assistance 📞</p>
</div>
""", unsafe_allow_html=True)


# =============== 3. Database ====================

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                language TEXT NOT NULL,
                location TEXT NOT NULL,
                message TEXT NOT NULL,
                category TEXT NOT NULL,
                urgency TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)


def get_requests():
    with sqlite3.connect(DB) as con:
        return pd.read_sql_query(
            "SELECT * FROM requests ORDER BY created_at DESC",
            con,
        )


def save_request(language, location, message, category, urgency):
    request_id = "JR-" + uuid.uuid4().hex[:8].upper()

    with sqlite3.connect(DB) as con:
        con.execute("""
            INSERT INTO requests
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            datetime.now().isoformat(timespec="seconds"),
            language,
            location.strip(),
            message.strip(),
            category,
            urgency,
            "Pending",
        ))

    return request_id


init_db()


# =============== 4. Gnani Speech-to-Text ====================

def transcribe_audio(audio_bytes, language_code):
    response = requests.post(
        "https://api.vachana.ai/stt/v3",
        headers={"X-API-Key-ID": API_KEY},
        files={
            "audio_file": ("emergency.wav", audio_bytes, "audio/wav")
        },
        data={"language_code": language_code},
        timeout=90,
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("success") or not result.get("transcript"):
        raise RuntimeError(f"Transcription failed: {result}")

    return result["transcript"]


# =============== 5. Gnani Text-to-Speech ====================

def generate_speech(text, language_code):
    response = requests.post(
        "https://api.vachana.ai/api/v1/tts/inference",
        headers={
            "X-API-Key-ID": API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "voice": "Nalini",
            "model": "timbre-v2.5",
            "language": language_code,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": 48000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        },
        timeout=90,
    )
    response.raise_for_status()
    return response.content


# =============== 6. Request Classification ====================

def classify_request(message):
    text = message.lower()

    category_rules = {
        "Rescue": [
            "trapped", "stranded", "drowning", "rescue", "save us",
            "बचाओ", "फंसा", "फंसी", "बाढ़ में", "बाढ़", "फंस चुका हूँ",
        ],
        "Medical": [
            "bleeding", "injured", "unconscious", "medicine",
            "hospital", "can't breathe", "घायल", "खून",
            "अस्पताल", "सांस नहीं",
        ],
        "Food & Water": [
            "food", "hungry", "thirsty", "drinking water",
            "no water", "भूख", "खाना", "पानी",
        ],
        "Shelter": [
            "shelter", "homeless", "roof", "tent",
            "आश्रय", "बेघर", "घर टूट",
        ],
    }

    category = "Other"

    for name, keywords in category_rules.items():
        if any(word in text for word in keywords):
            category = name
            break

    critical_keywords = [
        "trapped", "drowning", "bleeding", "unconscious",
        "can't breathe", "cannot breathe", "बचाओ",
        "सांस नहीं", "खून बह",
    ]

    high_keywords = [
        "injured", "stranded", "urgent", "मौत",
        "no food", "no water", "घायल", "death",
    ]

    if any(word in text for word in critical_keywords):
        urgency = "Critical"
    elif any(word in text for word in high_keywords):
        urgency = "High"
    elif category != "Other":
        urgency = "Medium"
    else:
        urgency = "Low"

    return category, urgency


# =============== 7. API Key Check ====================

if not API_KEY:
    st.error("GNANI_API_KEY is missing. Configure it in Streamlit Secrets or your .env file.")


# =============== 8. Main Application ====================

intake_tab, dashboard_tab = st.tabs([
    "🎙️ Emergency Intake",
    "📊 Relief Dashboard",
])


# =============== 9. Public Emergency Intake ====================

with intake_tab:
    st.subheader("Register an emergency request")
    st.caption(
        "Record a request, verify its transcription, "
        "and register it for relief coordination."
    )

    language = st.selectbox(
        "Select request language",
        list(LANGUAGES.keys()),
    )
    language_code = LANGUAGES[language]

    audio = st.audio_input("Record the emergency request")

    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button(
            "Transcribe with Gnani",
            disabled=audio is None or not API_KEY,
            use_container_width=True,
        ):
            try:
                with st.spinner("Transcribing audio..."):
                    transcript = transcribe_audio(
                        audio.getvalue(), language_code
                    )
                st.session_state["message"] = transcript
                st.success("Transcription complete.")
            except Exception as e:
                st.error(f"STT error: {e}")

    with col2:
        st.caption("Review the transcript before submitting.")

    message = st.text_area(
        "Emergency message",
        key="message",
        height=130,
        placeholder="Example: We are trapped in flood water...",
    )

    location = st.text_input(
        "Location",
        placeholder="Village, district, or nearby landmark",
    )

    if message.strip():
        category, urgency = classify_request(message)

        c1, c2 = st.columns(2)
        c1.info(f"**Category:** {category}")

        if urgency == "Critical":
            c2.error(f"**Urgency:** {urgency}")
        elif urgency == "High":
            c2.warning(f"**Urgency:** {urgency}")
        else:
            c2.info(f"**Urgency:** {urgency}")

    if st.button(
        "🚨 Submit Relief Request",
        type="primary",
        use_container_width=True,
    ):
        if not message.strip() or not location.strip():
            st.warning("Enter the emergency message and location.")
        else:
            category, urgency = classify_request(message)

            request_id = save_request(
                language, location, message, category, urgency
            )

            st.success(f"Request recorded successfully: {request_id}")

            confirmation = (
                f"Your request ID is {request_id}. "
                f"Your request is categorized as {category}. "
                f"The assessed urgency is {urgency}. "
                "Your request has been recorded for review. "
                "This does not mean rescue or aid has been dispatched."
            )

            st.info(confirmation)

            if API_KEY:
                try:
                    with st.spinner("Generating spoken confirmation..."):
                        audio_bytes = generate_speech(
                            confirmation, language_code
                        )
                    st.audio(audio_bytes, format="audio/wav")
                except Exception as e:
                    st.warning(
                        "The request was saved, but speech generation failed. "
                        f"Error: {e}"
                    )

            st.caption(
                "This prototype records requests; it does not contact "
                "emergency services."
            )


# =============== 10. Protected Relief Dashboard ====================

with dashboard_tab:
    if not st.session_state.get("dashboard_authenticated", False):
        st.subheader("🔒 Coordinator Login")
        st.caption("Authorized relief coordinators only.")

        with st.form("dashboard_login"):
            password = st.text_input("Dashboard password", type="password")
            submitted = st.form_submit_button("Sign in")

            if submitted:
                dashboard_password = st.secrets.get("DASHBOARD_PASSWORD", "")

                if dashboard_password and password == dashboard_password:
                    st.session_state["dashboard_authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password or dashboard password not configured.")

    else:
        top_col, logout_col = st.columns([5, 1])

        with top_col:
            st.subheader("Relief coordination dashboard")

        with logout_col:
            if st.button("Log out"):
                st.session_state["dashboard_authenticated"] = False
                st.rerun()

        df = get_requests()

        if df.empty:
            st.info("No requests recorded yet. Submit a test request first.")
        else:
            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Total requests", len(df))
            c2.metric("Critical", int((df["urgency"] == "Critical").sum()))
            c3.metric("Pending", int((df["status"] == "Pending").sum()))
            c4.metric("Resolved", int((df["status"] == "Resolved").sum()))

            st.divider()
            st.subheader("Filter requests")

            f1, f2, f3 = st.columns(3)

            category_filter = f1.selectbox(
                "Category", ["All"] + CATEGORIES
            )
            urgency_filter = f2.selectbox(
                "Urgency", ["All"] + URGENCIES
            )
            status_filter = f3.selectbox(
                "Status", ["All"] + STATUSES
            )

            filtered = df.copy()

            if category_filter != "All":
                filtered = filtered[
                    filtered["category"] == category_filter
                ]

            if urgency_filter != "All":
                filtered = filtered[
                    filtered["urgency"] == urgency_filter
                ]

            if status_filter != "All":
                filtered = filtered[
                    filtered["status"] == status_filter
                ]

            display_columns = [
                "id", "created_at", "location", "category",
                "urgency", "status", "message",
            ]

            st.dataframe(
                filtered[display_columns],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("Update request status")

            if not filtered.empty:
                selected_id = st.selectbox(
                    "Select request",
                    filtered["id"].tolist(),
                )

                current_status = filtered.loc[
                    filtered["id"] == selected_id, "status"
                ].iloc[0]

                new_status = st.selectbox(
                    "New status",
                    STATUSES,
                    index=STATUSES.index(current_status),
                )

                if st.button("Save status update"):
                    with sqlite3.connect(DB) as con:
                        con.execute(
                            "UPDATE requests SET status = ? WHERE id = ?",
                            (new_status, selected_id),
                        )

                    st.success("Request status updated.")
                    st.rerun()
            else:
                st.info("No requests match these filters.")

            if st.button("🔄 Refresh dashboard"):
                st.rerun()


# =============== 11. Footer ====================

st.divider()
st.caption(
    "JeevanRaksha AI MVP | Gnani Prisma STT + Timbre TTS | "
    "Streamlit + SQLite | Prototype for demonstration only"
)