# app.py includes user input
import os
import streamlit as st
from kubernetes import client, config
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

# Load .env variables
load_dotenv()

# Set up OpenAI
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Kubernetes Config
GROUP = "compliance.openshift.io"
VERSION = "v1alpha1"
NAMESPACE = "qsafe-engineers"
config.load_kube_config()
custom_api = client.CustomObjectsApi()

# --- Data Fetching ---
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
        status = result.get("status")
        if status != "FAIL":
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
    base = f"The compliance scan '{scan_name}' failed the following rules:\n\n"
    for i, rule in enumerate(failed_checks, 1):
        base += f"{i}. {rule['id']}: {rule['description']} (Severity: {rule['severity']})\n"
    base += f"\nUser's question: {user_question}\n"
    base += "Please answer the question using only the scan information above."
    return base

# --- Streamlit Chat UI ---
st.set_page_config(page_title="Compliance AI Chat", layout="centered")
st.title("💬 Compliance Chat Agent")

# Load scans
scans = get_scans()
scan_names = [scan["metadata"]["name"] for scan in scans]
selected_scan = st.selectbox("📋 Select ComplianceScan", scan_names)

# Session state for chat
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

failed_rules = get_failed_checks(selected_scan)

# User input
user_input = st.chat_input("Ask a question about the scan...")
if user_input:
    prompt = build_prompt(user_input, selected_scan, failed_rules)
    with st.spinner("🤖 Thinking..."):
        try:
            response = client_ai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a compliance analyst assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=600
            )
            ai_reply = response.choices[0].message.content
        except Exception as e:
            ai_reply = f"❌ Error: {e}"

    # Save history
    st.session_state.chat_history.append(("user", user_input))
    st.session_state.chat_history.append(("ai", ai_reply))

# Render history
for role, msg in st.session_state.chat_history:
    with st.chat_message("🧑‍💻" if role == "user" else "🤖"):
        st.markdown(msg)
