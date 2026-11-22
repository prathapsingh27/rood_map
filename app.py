"""
AI Career Roadmap & Skill Gap Finder
Streamlit + Gemini API

Run:
    pip install streamlit google-genai pandas
    export GEMINI_API_KEY="your-key"      # or paste it in the sidebar
    streamlit run app.py
"""

import json
import os

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.8-flash"  # change here, in secrets.toml, or in the sidebar

st.set_page_config(page_title="Career Roadmap & Skill Gap Finder", page_icon="🧭", layout="wide")


# ---------- Gemini helpers ----------
def build_prompt(skills: str, role: str, hours: int) -> str:
    return f"""
You are an experienced career mentor for students entering tech.

Student's current skills: {skills}
Target job role: {role}
Study time available: {hours} hours per week

Compare the student's current skills with what an entry-level {role} needs.
Return ONLY valid JSON (no markdown, no commentary) in exactly this shape:

{{
  "skill_table": [
    {{
      "skill": "string",
      "status": "Have" | "Partial" | "Need to learn",
      "importance": "High" | "Medium" | "Low",
      "note": "one short sentence on why it matters or how it relates to what they know"
    }}
  ],
  "roadmap": [
    {{
      "week": 1,
      "theme": "short title",
      "topics": ["topic 1", "topic 2"],
      "activities": ["concrete hands-on task 1", "concrete hands-on task 2"],
      "resources": ["free resource name or search term"],
      "goal": "what the student can do by the end of this week"
    }}
  ],
  "projects": [
    {{
      "title": "string",
      "description": "2 sentences",
      "skills_practiced": ["skill 1", "skill 2"],
      "difficulty": "Beginner" | "Intermediate" | "Advanced",
      "tools": ["tool 1", "tool 2"]
    }}
  ]
}}

Rules:
- skill_table: 10 to 14 rows. Include skills the student already has that are relevant
  (status "Have"), and the key skills still missing. Do not list irrelevant skills.
- roadmap: exactly 8 entries, weeks 1 to 8, in a sensible learning order
  (prerequisites first). Size the workload to {hours} hours per week: fewer hours means
  fewer topics per week. Build on what the student already knows and skip it.
- projects: exactly 3, increasing in difficulty, each realistic for a portfolio and
  achievable within the 8 weeks.
- Be specific (name actual libraries, concepts, datasets) rather than generic.
"""


def get_client(api_key: str):
    return genai.Client(api_key=api_key)


def generate_plan(api_key: str, model: str, skills: str, role: str, hours: int) -> dict:
    client = get_client(api_key)
    response = client.models.generate_content(
        model=model,
        contents=build_prompt(skills, role, hours),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.6,
        ),
    )
    text = (response.text or "").strip()
    # Defensive: strip code fences if the model adds them anyway
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    return json.loads(text)


# ---------- UI helpers ----------
STATUS_ICON = {"Have": "✅ Have", "Partial": "🟡 Partial", "Need to learn": "❌ Need to learn"}


def render_skill_table(rows: list):
    df = pd.DataFrame(rows)
    df["status"] = df["status"].map(lambda s: STATUS_ICON.get(s, s))
    df = df.rename(
        columns={"skill": "Skill", "status": "Status", "importance": "Importance", "note": "Why it matters"}
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    have = sum(1 for r in rows if r["status"] == "Have")
    partial = sum(1 for r in rows if r["status"] == "Partial")
    need = sum(1 for r in rows if r["status"] == "Need to learn")
    c1, c2, c3 = st.columns(3)
    c1.metric("Already have", have)
    c2.metric("Partially have", partial)
    c3.metric("To learn", need)


def render_roadmap(weeks: list):
    for w in weeks:
        with st.expander(f"Week {w['week']}: {w['theme']}", expanded=(w["week"] == 1)):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Topics**")
                for t in w.get("topics", []):
                    st.markdown(f"- {t}")
                st.markdown("**Resources**")
                for r in w.get("resources", []):
                    st.markdown(f"- {r}")
            with col2:
                st.markdown("**Activities**")
                for a in w.get("activities", []):
                    st.markdown(f"- {a}")
            st.success(f"🎯 By the end of the week: {w.get('goal', '')}")


def render_projects(projects: list):
    cols = st.columns(len(projects))
    for col, p in zip(cols, projects):
        with col:
            with st.container(border=True):
                st.subheader(p["title"])
                st.caption(f"{p.get('difficulty', '')}")
                st.write(p["description"])
                st.markdown("**Skills practiced:** " + ", ".join(p.get("skills_practiced", [])))
                st.markdown("**Tools:** " + ", ".join(p.get("tools", [])))


def plan_to_markdown(plan: dict, role: str) -> str:
    md = [f"# 8-Week Roadmap to {role}\n", "## Skill gap\n", "| Skill | Status | Importance | Note |", "|---|---|---|---|"]
    for r in plan["skill_table"]:
        md.append(f"| {r['skill']} | {r['status']} | {r['importance']} | {r['note']} |")
    md.append("\n## Weekly plan\n")
    for w in plan["roadmap"]:
        md.append(f"### Week {w['week']}: {w['theme']}")
        md.append("**Topics:** " + ", ".join(w.get("topics", [])))
        md.append("**Activities:**")
        md += [f"- {a}" for a in w.get("activities", [])]
        md.append("**Resources:** " + ", ".join(w.get("resources", [])))
        md.append(f"**Goal:** {w.get('goal', '')}\n")
    md.append("## Portfolio projects\n")
    for p in plan["projects"]:
        md.append(f"### {p['title']} ({p.get('difficulty', '')})")
        md.append(p["description"])
        md.append("Skills: " + ", ".join(p.get("skills_practiced", [])))
        md.append("Tools: " + ", ".join(p.get("tools", [])) + "\n")
    return "\n".join(md)


# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    default_key = os.getenv("GEMINI_API_KEY", "")
    try:
        default_key = default_key or st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    api_key = st.text_input("Gemini API key", value=default_key, type="password",
                            help="Get a free key at aistudio.google.com")
    st.caption("Your key is only used for this session.")

    default_model = os.getenv("GEMINI_MODEL", "")
    try:
        default_model = default_model or st.secrets.get("GEMINI_MODEL", "")
    except Exception:
        pass
    model_name = st.text_input("Gemini model", value=default_model or DEFAULT_MODEL,
                               help="If you get a 404 model error, enter a currently available model name.")

# ---------- Main ----------
st.title("🧭 AI Career Roadmap & Skill Gap Finder")
st.write("Tell me what you know and where you want to go. I'll show you what's missing and "
         "build an 8-week plan to get there.")

with st.form("inputs"):
    skills = st.text_area(
        "Your current skills",
        placeholder="e.g. C, basic Python, HTML",
        help="Comma-separated is fine. Include tools, languages, and subjects you've studied.",
    )
    c1, c2 = st.columns([2, 1])
    role = c1.text_input("Target job role", placeholder="e.g. Data Scientist")
    hours = c2.slider("Hours per week to study", min_value=2, max_value=40, value=10)
    submitted = st.form_submit_button("Generate my roadmap 🚀", type="primary")

if submitted:
    if not api_key:
        st.error("Please add your Gemini API key in the sidebar.")
    elif not skills.strip() or not role.strip():
        st.warning("Please fill in both your current skills and your target role.")
    else:
        try:
            with st.spinner("Analyzing your skills and building your plan..."):
                st.session_state["plan"] = generate_plan(api_key, model_name.strip() or DEFAULT_MODEL, skills.strip(), role.strip(), hours)
                st.session_state["role"] = role.strip()
                st.session_state["hours"] = hours
        except json.JSONDecodeError:
            st.error("The AI returned something I couldn't read. Please try again.")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

plan = st.session_state.get("plan")
if plan:
    role_name = st.session_state["role"]
    st.divider()
    st.header(f"Your path to {role_name}")
    st.caption(f"Planned for {st.session_state['hours']} hours per week")

    tab1, tab2, tab3 = st.tabs(["📊 Skill gap", "🗓️ 8-week roadmap", "🛠️ Portfolio projects"])
    with tab1:
        render_skill_table(plan["skill_table"])
    with tab2:
        render_roadmap(plan["roadmap"])
    with tab3:
        render_projects(plan["projects"])

    st.download_button(
        "⬇️ Download plan (Markdown)",
        data=plan_to_markdown(plan, role_name),
        file_name="career_roadmap.md",
        mime="text/markdown",
    )
