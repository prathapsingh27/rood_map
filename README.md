# AI Career Roadmap & Skill Gap Finder

Streamlit + Gemini app that compares your skills with a target job and builds
an 8-week learning plan plus 3 portfolio project ideas.

## Setup
1. `pip install -r requirements.txt`
2. Get a free key at https://aistudio.google.com
3. Open `.streamlit/secrets.toml` and replace the placeholder with your key
   (or paste the key into the app's sidebar).
4. `streamlit run app.py`

## Deploy on Streamlit Community Cloud
Push to GitHub (secrets.toml is git-ignored), create the app, then add
`GEMINI_API_KEY = "your-key"` under App settings > Secrets.
