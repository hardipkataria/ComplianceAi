# tools/semantic_matcher.py
#The goal of this module is to allow users to ask natural language questions
# or request remediation without knowing the exact compliance rule ID or phrasing.
import os

import dotenv
import faiss
import numpy as np
from langchain.embeddings import OpenAIEmbeddings
from tools.k8s_tools import fetch_compliance_failures

#load env
dotenv.load_dotenv()

# Load OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize embedding model
embedding_model = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Global cache for FAISS index and rule mapping
_index = None
_rule_texts = []

def build_index():
    global _index, _rule_texts

    failed_checks = fetch_compliance_failures()
    if not failed_checks:
        return

    _rule_texts = [f"{r['id']}: {r['description']}" for r in failed_checks]
    embeddings = embedding_model.embed_documents(_rule_texts)

    dim = len(embeddings[0])
    _index = faiss.IndexFlatL2(dim)
    _index.add(np.array(embeddings).astype("float32"))

#searches the pre-indexed compliance rules using vector similarity.
def find_best_matching_rule(user_query: str) -> str:
    global _index, _rule_texts

    if _index is None or not _rule_texts:
        build_index()
        if _index is None:
            return "❌ Could not build index from failed checks."

    query_vector = embedding_model.embed_query(user_query)
    D, I = _index.search(np.array([query_vector]).astype("float32"), k=1)

    if not I[0].size or I[0][0] >= len(_rule_texts):
        return "❌ No matching rule found."

    best_match = _rule_texts[I[0][0]]
    return f"🔎 Best Match:\n{best_match}"

def find_best_matching_rule(input_text: str) -> str:
    print(f"[TOOL DEBUG] Called: find_best_matching_rule with input: {input_text}")

    # Optional: extract scan name from input
    scan_name = None
    tokens = input_text.split()
    for i, token in enumerate(tokens):
        if token in ("of", "for") and i + 1 < len(tokens):
            scan_name = tokens[i + 1]

    # Extract the rule portion (remove 'explain', 'of', etc.)
    rule_candidate = input_text
    for skip_word in ["explain", "rule", "of", "for", scan_name]:
        if skip_word:
            rule_candidate = rule_candidate.replace(skip_word, "")
    rule_candidate = rule_candidate.strip()

    print(f"[TOOL DEBUG] Parsed rule: {rule_candidate}, scan: {scan_name}")

    # Now call your semantic match logic
    try:
        failures = fetch_compliance_failures(scan_name)
    except Exception as e:
        return f"❌ Failed to fetch failures for scan '{scan_name}': {e}"

    # Match rule ID (exact or partial)
    for failure in failures:
        rule_id = failure.get("id", "")
        description = failure.get("description", "")
        if rule_candidate.lower() in rule_id.lower():
            return f"🔍 **Rule:** {rule_id}\n📝 **Description:** {description}"

    return f"❓ Could not find rule matching '{rule_candidate}' in scan '{scan_name}'."

