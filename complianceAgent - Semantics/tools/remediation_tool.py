import re
from tools.k8s_tools import fetch_compliance_failures

def render_playbook_block(playbook: str) -> str:
    "Format playbook as markdown code block if not empty."
    if not playbook or not playbook.strip():
        return "_No Ansible playbook available._"
    # Optionally check YAML structure here if needed
    playbook = playbook.strip()
    if not playbook.startswith("---"):
        playbook = "---\n" + playbook
    return f"``````"

def user_wants_playbook(user_input: str) -> bool:
    """Return True if user input asks for playbook (by common keywords)."""
    keywords = ["playbook", "ansible", "yaml"]
    user_input = user_input.lower()
    return any(word in user_input for word in keywords)

def get_all_scan_names() -> list[str]:
    # You can later enhance this to fetch dynamically from the cluster or DB
    return ["ocp4-cis", "ocp4-e8", "ocp4-stig"]

def user_wants_playbook(text: str) -> bool:
    return "playbook" in text or "ansible" in text

def parse_rule_and_scan(input_text: str) -> tuple[str, str | None]:
    input_text = input_text.strip()
    match = re.match(r"(.*?)(?:\s+(?:of|from)\s+(.*))?$", input_text, re.IGNORECASE)
    if match:
        rule = match.group(1).strip()
        scan = match.group(2).strip() if match.group(2) else None
        return rule, scan
    return input_text, None

def generate_playbook(input_text: str) -> str:
    """
    Show remediation for a specific failed rule (by ID or description),
    or all failed rules if requested. If user asks for playbook, include it.
    Else, just remediation.
    """
    rule_query, scan_name = parse_rule_and_scan(input_text)
    input_lower = input_text.lower()
    wants_playbook = user_wants_playbook(input_lower)

    # Remediate ALL rules for a specific scan
    if "all" in input_lower or "remediate all" in input_lower:
        if not scan_name:
            return "⚠️ Please specify the scan name to remediate all rules."

        failed = fetch_compliance_failures(scan_name)
        items = []
        for rule in failed:
            text = (
                f"🔧 **{rule['id']}**\n"
                f"_{rule['description'].strip()}_\n\n"
                f"**Remediation Steps:**\n{rule.get('remediation', 'No remediation available.').strip()}"
            )
            if wants_playbook:
                ansible = rule.get("ansible_playbook") or ""
                text += f"\n\n**Ansible Playbook:**\n{render_playbook_block(ansible)}"
            items.append(text)
        return "\n\n---\n\n".join(items) if items else "✅ No failed rules found to remediate."

    # Try matching a specific rule from provided scan
    if scan_name:
        failed = fetch_compliance_failures(scan_name)
        for rule in failed:
            if rule_query.lower() in rule["id"].lower() or rule_query.lower() in rule["description"].lower():
                text = (
                    f"🔧 **Remediation for {rule['id']}**\n"
                    f"_{rule['description'].strip()}_\n\n"
                    f"**Remediation Steps:**\n{rule.get('remediation', 'No remediation available.').strip()}"
                )
                if wants_playbook:
                    ansible = rule.get("ansible_playbook") or ""
                    text += f"\n\n**Ansible Playbook:**\n{render_playbook_block(ansible)}"
                return text

    # Fallback: search all scans
    for scan in get_all_scan_names():
        failed = fetch_compliance_failures(scan)
        for rule in failed:
            if rule_query.lower() in rule["id"].lower() or rule_query.lower() in rule["description"].lower():
                text = (
                    f"🔧 **Remediation for {rule['id']}** (from scan `{scan}`)\n"
                    f"_{rule['description'].strip()}_\n\n"
                    f"**Remediation Steps:**\n{rule.get('remediation', 'No remediation available.').strip()}"
                )
                if wants_playbook:
                    ansible = rule.get("ansible_playbook") or ""
                    text += f"\n\n**Ansible Playbook:**\n{render_playbook_block(ansible)}"
                return text

    return (
        "⚠️ Could not find a specific failed rule matching your request.\n\n"
        "Try including a rule ID or a more exact description from the compliance scan."
    )
