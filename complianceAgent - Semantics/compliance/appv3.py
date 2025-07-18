# app.py v3 includes suggestions
import os
import streamlit as st
from kubernetes import client, config
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

# --- Load environment and setup ---
load_dotenv()
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
config.load_kube_config()
custom_api = client.CustomObjectsApi()

GROUP = "compliance.openshift.io"
VERSION = "v1alpha1"
NAMESPACE = "qsafe-engineers"

# --- Fetch data ---
def get_scans():
    return custom_api.list_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=NAMESPACE, plural="compliancescans"
    ).get("items", [])

def get_failed_checks(scan_name):
    check_results = custom_api.list_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=NAMESPACE, plural="compliancecheckresults"
    )
    failed = []
    for result in check_results.get("items", []):
        if result.get("status") != "FAIL":
            continue
        result_name = result["metadata"]["name"]
        owner_refs = result["metadata"].get("ownerReferences", [])
        result_scan_name = owner_refs[0]["name"] if owner_refs else ""
        if result_scan_name == scan_name:
            failed.append({
                "id": result_name,
                "description": result.get("description", "N/A"),
                "severity": result.get("severity", "unknown")
            })
    return failed

# --- Prompt builder ---
def build_prompt(user_question: str, scan_name: str, failed_checks: List[dict]) -> str:
    rules_text = "\n".join(
        f"{i+1}. {rule['id']} - {rule['description']} (Severity: {rule['severity']})"
        for i, rule in enumerate(failed_checks)
    )
    prompt = (
        f"Compliance scan '{scan_name}' failed the following rules:\n\n"
        f"{rules_text}\n\n"
        f"User's question: {user_question}\n"
        f"Provide a clear and helpful response based on the scan data."
    )
    return prompt

# --- Streamlit App UI ---
st.set_page_config(page_title="Compliance AI Agent", layout="centered")
st.title("🤖 Compliance Chat Agent")

# Load and select scan
scans = get_scans()
scan_names = [scan["metadata"]["name"] for scan in scans]
selected_scan = st.selectbox("📋 Select a ComplianceScan", scan_names)
failed_rules = get_failed_checks(selected_scan)

# Suggested quick questions
st.markdown("💡 **Try one of these:**")
cols = st.columns(3)
quick_questions = [
    "Show me all critical issues",
    "What are the top 3 failed rules?",
    "Summarize medium severity problems"
]
for i, q in enumerate(quick_questions):
    if cols[i].button(q):
        st.session_state.user_input = q

# Chat state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Text input
user_input = st.chat_input("Ask about this scan...")
if user_input:
    st.session_state.chat_history.append(("user", user_input))
    prompt = build_prompt(user_input, selected_scan, failed_rules)
    with st.spinner("Thinking..."):
        try:
            response = client_ai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a security compliance assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=700
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"⚠️ Error: {e}"
    st.session_state.chat_history.append(("ai", reply))

# Show chat
for role, msg in st.session_state.chat_history:
    with st.chat_message("👤" if role == "user" else "🤖"):
        st.markdown(msg)

# Expandable rule viewer
with st.expander("📄 View all failed rules"):
    for rule in failed_rules:
        with st.expander(f"🔸 {rule['id']} (Severity: {rule['severity']})"):
            st.write(rule["description"])
