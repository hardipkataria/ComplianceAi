# app.py v4 — Enhanced with remediation and focused rule context memory
import os
import re
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
                "severity": result.get("severity", "unknown"),
                "rationale": result.get("rationale", "Not provided"),
                "remediation": result.get("instructions", "Not provided")
            })
    return failed

# --- Prompt builder ---
def build_prompt(user_question: str, scan_name: str, failed_checks: List[dict], focused_rule_id=None) -> str:
    if focused_rule_id:
        matched = [rule for rule in failed_checks if rule["id"] == focused_rule_id]
        if not matched:
            return f"User asked: {user_question} but rule ID '{focused_rule_id}' not found."
        rule = matched[0]
        rules_text = (
            f"Rule ID: {rule['id']}\n"
            f"Description: {rule['description']}\n"
            f"Severity: {rule['severity']}\n"
            f"Rationale: {rule['rationale']}\n"
            f"Remediation: {rule['remediation']}"
        )
    else:
        rules_text = "\n".join(
            f"{i+1}. {rule['id']} - {rule['description']} (Severity: {rule['severity']})"
            for i, rule in enumerate(failed_checks)
        )

    return (
        f"Compliance scan '{scan_name}' failed with the following rule(s):\n\n"
        f"{rules_text}\n\n"
        f"User's question: {user_question}\n"
        f"Answer clearly, referencing only what's asked."
    )

# --- Streamlit App UI ---
st.set_page_config(page_title="Compliance AI Agent", layout="centered")
st.title("🤖 Compliance Chat Agent")

# --- Session state ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = None
if "focused_rule_id" not in st.session_state:
    st.session_state.focused_rule_id = None

# --- Load scans ---
scans = get_scans()
scan_names = [scan["metadata"]["name"] for scan in scans]
selected_scan = st.selectbox("📋 Select a ComplianceScan", scan_names)
failed_rules = get_failed_checks(selected_scan)

# --- Suggested quick questions (auto-hide after interaction) ---
if not st.session_state.chat_history and not st.session_state.user_input:
    st.markdown("💡 **Try one of these:**")
    cols = st.columns(4)
    quick_questions = [
        "Show me all critical issues",
        "View all failed checks",
        "What are the top 3 failed rules?",
        "Summarize medium severity problems"
    ]
    for i, q in enumerate(quick_questions):
        if cols[i].button(q):
            st.session_state.user_input = q

# --- Chat input ---
typed_input = st.chat_input("Ask about this scan...")
if typed_input:
    st.session_state.user_input = typed_input

# --- AI Interaction ---
if st.session_state.user_input:
    user_input = st.session_state.user_input.strip()
    lower_input = user_input.lower()

    # 👁 Detect rule ID
    rule_id_match = re.search(r"(ocp4-[\w\-]+)", lower_input)
    if rule_id_match:
        st.session_state.focused_rule_id = rule_id_match.group(1)

    # 🧠 If it's a follow-up (e.g., "remediation"), use last focused rule
    elif any(keyword in lower_input for keyword in ["remediation", "how to fix", "mitigation", "fix", "remedy"]):
        if st.session_state.focused_rule_id:
            user_input += f" (about rule {st.session_state.focused_rule_id})"

    st.session_state.chat_history.append(("user", user_input))

    prompt = build_prompt(user_input, selected_scan, failed_rules, focused_rule_id=st.session_state.focused_rule_id)
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
    st.session_state.user_input = None  # reset after processing

# --- Display chat ---
for role, msg in st.session_state.chat_history:
    with st.chat_message("👤" if role == "user" else "🤖"):
        st.markdown(msg)
