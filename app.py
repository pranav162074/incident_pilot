"""
IncidentPilot - an incident-response copilot that gets smarter with every incident.
Memory layer: Vectorize Hindsight.  LLM: Groq.
"""
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from memory import IncidentMemory, MemoryUnavailable
from seed_data import DEMO_ALERTS, SEED_INCIDENTS

load_dotenv()

st.set_page_config(page_title="IncidentPilot", page_icon="🚨", layout="wide")

MODELS = ["openai/gpt-oss-120b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"]

MEMORY_SYSTEM = """You are IncidentPilot, a senior SRE copilot. You have access to this team's own
incident history, recalled from Hindsight memory and shown below.

RECALLED MEMORY:
{memory}

RULES:
1. If a recalled incident matches the alert, cite its incident ID and reuse the proven fix, adapting
   details (service names, values) to this alert.
2. If memory says a fix FAILED or only masked the problem, explicitly tell the engineer NOT to repeat it.
3. If nothing recalled is relevant, say so plainly. Never invent incident history.
4. Be concise. Exact commands over prose.

FORMAT (markdown):
### Likely root cause  (with confidence %)
### Do this now  (numbered steps, exact commands)
### Evidence from past incidents
### Do NOT do
"""

STATELESS_SYSTEM = """You are a senior SRE copilot with NO access to this team's incident history.
Give generic best-practice diagnosis for the alert. Be concise.

FORMAT (markdown):
### Likely root cause  (with confidence %)
### Do this now  (numbered steps, exact commands)
### Evidence from past incidents
Write exactly: "None - no team history available."
### Do NOT do
"""


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_memory() -> IncidentMemory:
    return IncidentMemory()


def ask_llm(client: Groq, system: str, user: str):
    """Try each model in order; fall back on any API / function-calling / rate-limit error."""
    last_err = None
    for model in MODELS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
                max_tokens=1500,
            )
            text = (r.choices[0].message.content or "").strip()
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            if text:
                return text, model
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"All Groq models failed. Last error: {last_err}")


def format_memories(mems) -> str:
    if not mems:
        return "(nothing relevant recalled)"
    return "\n".join(f"[{i + 1}] {m.text}" for i, m in enumerate(mems))


# ----------------------------------------------------------------------------
# state
# ----------------------------------------------------------------------------
st.session_state.setdefault("last", None)
st.session_state.setdefault("log", [])
st.session_state.setdefault("insight", "")
st.session_state.setdefault("alert_text", list(DEMO_ALERTS.values())[0]["alert"])


def on_preset_change():
    st.session_state.alert_text = DEMO_ALERTS[st.session_state.preset]["alert"]


# ----------------------------------------------------------------------------
# sidebar
# ----------------------------------------------------------------------------
mem = None
mem_error = None
try:
    mem = get_memory()
except MemoryUnavailable as e:
    mem_error = str(e)

groq_key = os.getenv("GROQ_API_KEY", "")

with st.sidebar:
    st.header("System status")
    if mem:
        st.success(f"Hindsight connected\n\nbank: `{mem.bank_id}`")
    else:
        st.error(f"Hindsight unavailable: {mem_error}")
    st.success("Groq key loaded") if groq_key else st.error("GROQ_API_KEY missing in .env")

    st.divider()
    st.header("Memory bank")
    st.caption(f"{len(SEED_INCIDENTS)} historical post-mortems available to load.")
    if st.button("Load historical incidents", disabled=mem is None):
        bar = st.progress(0.0, text="Retaining post-mortems into Hindsight...")
        try:
            for i, inc in enumerate(SEED_INCIDENTS):
                mem.retain_incident(**inc)
                bar.progress((i + 1) / len(SEED_INCIDENTS), text=f"Retained {inc['incident_id']}")
            st.success("Done. Give Hindsight ~30-60s to finish indexing.")
        except MemoryUnavailable as e:
            st.error(str(e))

    st.divider()
    if st.button("Clear session log"):
        st.session_state.log = []
        st.session_state.last = None
        st.rerun()

# ----------------------------------------------------------------------------
# header
# ----------------------------------------------------------------------------
st.title("🚨 IncidentPilot")
st.caption("An on-call copilot that remembers every incident your team has ever fought - powered by Vectorize Hindsight.")

tab_live, tab_ask, tab_log = st.tabs(["🚨 Live incident", "🧠 Ask the memory", "📈 Session log"])

# ----------------------------------------------------------------------------
# tab 1: live incident
# ----------------------------------------------------------------------------
with tab_live:
    st.selectbox("Demo alerts", list(DEMO_ALERTS.keys()), key="preset", on_change=on_preset_change)
    alert = st.text_area("Production alert / error log", key="alert_text", height=110)

    if st.button("Diagnose", type="primary", disabled=not (mem and groq_key)):
        client = Groq(api_key=groq_key)
        try:
            t0 = time.time()
            recalled = mem.recall(alert)
            recall_ms = int((time.time() - t0) * 1000)

            with st.spinner("Running both agents in parallel..."):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    f_plain = pool.submit(ask_llm, client, STATELESS_SYSTEM, alert)
                    f_mem = pool.submit(ask_llm, client, MEMORY_SYSTEM.format(memory=format_memories(recalled)), alert)
                    plain_text, plain_model = f_plain.result()
                    mem_text, mem_model = f_mem.result()

            st.session_state.last = {
                "alert": alert, "recalled": recalled, "recall_ms": recall_ms,
                "plain": plain_text, "mem": mem_text, "model": mem_model,
                "preset": st.session_state.preset,
            }
            st.session_state.log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "alert": alert[:70] + ("..." if len(alert) > 70 else ""),
                "memories_recalled": len(recalled),
                "recall_ms": recall_ms,
            })
        except MemoryUnavailable as e:
            st.error(f"Memory error: {e}")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))

    last = st.session_state.last
    if last:
        m1, m2, m3 = st.columns(3)
        m1.metric("Memories recalled", len(last["recalled"]))
        m2.metric("Hindsight recall latency", f"{last['recall_ms']} ms")
        m3.metric("Model", last["model"])

        left, right = st.columns(2)
        with left:
            st.markdown("### ❌ Without memory")
            st.markdown(last["plain"])
        with right:
            st.markdown("### ✅ With Hindsight memory")
            st.markdown(last["mem"])

        with st.expander(f"🧠 What Hindsight recalled ({len(last['recalled'])})", expanded=False):
            if not last["recalled"]:
                st.info("Nothing relevant in memory yet. Resolve this incident below and teach it.")
            for i, m in enumerate(last["recalled"], 1):
                st.markdown(f"**{i}.** `{m.kind}` {m.text}")

        # ---- teach loop ----
        st.divider()
        st.subheader("Resolved it? Teach IncidentPilot")
        st.caption("This is the learning loop: what you enter is retained in Hindsight and used on the next similar alert.")
        res = DEMO_ALERTS.get(last["preset"], {}).get("resolution") or {}
        k = last["preset"]
        with st.form("teach"):
            c1, c2 = st.columns(2)
            inc_id = c1.text_input("Incident ID", value=f"INC-{datetime.now().strftime('%m%d%H%M')}", key=f"id_{k}")
            service = c2.text_input("Service", value=res.get("service", ""), key=f"svc_{k}")
            root = st.text_area("Root cause", value=res.get("root_cause", ""), key=f"rc_{k}")
            fix = st.text_area("Fix that was applied", value=res.get("fix_applied", ""), key=f"fx_{k}")
            c3, c4 = st.columns(2)
            outcome = c3.selectbox("Outcome", ["resolved", "fix_failed"], key=f"oc_{k}")
            mins = c4.number_input("Minutes to resolve", 0, 1000, value=res.get("minutes_to_resolve", 30), key=f"mn_{k}")
            if st.form_submit_button("Retain in Hindsight memory"):
                if not (root.strip() and fix.strip()):
                    st.warning("Root cause and fix are required.")
                else:
                    try:
                        mem.retain_incident(
                            incident_id=inc_id, summary=last["alert"], root_cause=root, fix_applied=fix,
                            outcome=outcome, service=service, minutes_to_resolve=int(mins) or None,
                        )
                        st.success(f"Retained {inc_id}. Wait ~20s for indexing, then re-run Diagnose (try demo alert #4).")
                    except MemoryUnavailable as e:
                        st.error(str(e))

# ----------------------------------------------------------------------------
# tab 2: ask the memory (reflect)
# ----------------------------------------------------------------------------
with tab_ask:
    st.write("Hindsight doesn't just search - it **reasons** over everything it has retained.")
    qs = [
        "Which services fail most often, and what usually fixes them?",
        "What fixes have failed in the past that we should never repeat?",
        "What are the recurring root-cause patterns across our incidents?",
    ]
    cols = st.columns(len(qs))
    for c, q in zip(cols, qs):
        if c.button(q, disabled=mem is None):
            st.session_state.insight = q
    question = st.text_input("Or ask your own", value=st.session_state.insight)
    if st.button("Ask Hindsight", disabled=mem is None or not question):
        try:
            with st.spinner("Hindsight is reflecting on your incident history..."):
                st.markdown(mem.reflect(question))
        except MemoryUnavailable as e:
            st.error(str(e))

# ----------------------------------------------------------------------------
# tab 3: session log
# ----------------------------------------------------------------------------
with tab_log:
    if st.session_state.log:
        df = pd.DataFrame(st.session_state.log)
        st.dataframe(df)
        st.bar_chart(df["memories_recalled"])
        st.caption("Memories recalled per diagnosis in this session.")
    else:
        st.info("Run a diagnosis to start the log.")