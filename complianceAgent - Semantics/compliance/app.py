# app.py
import os
import streamlit as st
from kubernetes import client, config
from typing import List
from dotenv import load_dotenv

MAX_ITEMS = 2
load_dotenv()

# --- Configuration ---
GROUP = "compliance.openshift.io"
VERSION = "v1alpha1"
NAMESPACE = "qsafe-engineers"

# --- Setup ---
config.load_kube_config()
custom_api = client.CustomObjectsApi()

# --- Helper functions ---
def get_scans():
    return custom_api.list_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=NAMESPACE, plural="compliancescans"
    ).get("items", [])


# 🔍 Function to get failed compliance check results
def get_failed_checks(scan_name):
    check_results = custom_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="compliancecheckresults"
    )

    failed = []

    # print(f"🔍 Checking scan result: {scan_name}")
    for result in check_results.get("items", []):
        status = result.get("status")

        if status != "FAIL":
            # print(f"⚠️ Skipping {result['metadata']['name']}: status: {status}")
            continue  # Skip NON FAILED items

        result_name = result["metadata"]["name"]
        owner_refs = result["metadata"].get("ownerReferences", [])
        result_scan_name = owner_refs[0]["name"]

        # print(f"🔍 Checking result: {result_name} | scanName: {result_scan_name} | result: {status}")

        if status == "FAIL" and result_scan_name == scan_name:
            failed.append({
                "id": result_name,
                "description": result.get("description", "N/A"),
                "severity": result.get("severity", "unknown"),
                "rationale": result.get("rationale", "Not provided"),
                "remediation": result.get("instructions", "Remediation not provided")
            })

    return failed


# 🧠 Prompt builder
def build_prompt(scan_name: str, failed_checks: List[dict]) -> str:
    prompt = f"The compliance scan '{scan_name}' failed the following rules:\n\n"
    # for i, rule in enumerate(failed_checks, 1):
    for i, rule in enumerate(failed_checks[:2], 1):  # Only take first 2 items, this is done for testing and reducing tokens
        prompt += f"{i}. {rule['id']}: {rule['description']} (Severity: {rule['severity']})\n"

    prompt += "\nPlease summarize the risks and suggest mitigation steps."
    print(prompt)
    return prompt


# 📡 AI Call using OpenAI GPT-4o-mini
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_ai(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes compliance scan reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=512
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[OpenAI Error] {e}"



# --- Streamlit UI ---
st.title("📋 Compliance AI Assistant")

scans = get_scans()
scan_names = [scan["metadata"]["name"] for scan in scans]

selected_scan = st.selectbox("Choose a ComplianceScan:", scan_names)

if st.button("Analyze Scan"):
    failed = get_failed_checks(selected_scan)

    if failed:
        st.subheader("⚠️ Failed Rules (Top 2)")
        for rule in failed[:MAX_ITEMS]:
            st.markdown(f"- **{rule['id']}**: {rule['description']} _(Severity: {rule['severity']})_")

        #prompt = build_prompt(selected_scan, failed)
        #with st.spinner("🤖 Asking AI..."):
        #    ai_response = call_ai(prompt)
        # st.subheader("🧠 AI Summary")
        #st.markdown(ai_response)
    else:
        st.success("✅ No failed rules in this scan.")
