# JeevanRaksha AI 🇮🇳

**A voice-based disaster-relief assistant built to help people report emergency needs during floods and cyclones.**

JeevanRaksha AI lets people report their needs by voice, get a spoken confirmation, and helps relief teams manage requests in one place.

### Features
- Voice input using Gnani AI Prisma STT
- Spoken responses using Gnani AI Timbre TTS
- Emergency categorisation and urgency flags
- Request tracking with unique IDs
- Simple dashboard for relief teams

### Tech Stack
Python · Streamlit · Gnani AI APIs · SQLite

### How it works
Voice input → Speech-to-text → Classify request → Save request → Spoken confirmation

### Run locally
```bash
git clone https://github.com/aasutoshsony/jeevanraksha-ai.git
cd jeevanraksha-ai
pip install -r requirements.txt
streamlit run app.py
```

*JeevanRaksha AI is an MVP prototype. It is not connected to live emergency services.*
