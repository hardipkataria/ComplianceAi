# analyzer_agent.py

from tools.k8s_tools import fetch_compliance_failures, list_all_scans


def analyze_checks(severity: str, scan_name: str | None = None) -> str:
    """Filters failed checks by severity.

    Args:
        severity (str): Severity level to filter ("low", "medium", "high", "critical").
        scan_name (str | None): Optional scan name to filter within.

    Returns:
        str: Filtered list of failed rules.
    """
    print(f"[TOOL DEBUG] Called: analyze_checks with scan_name: {scan_name} and severity: {severity}")

    severity = severity.lower()
    failures = fetch_compliance_failures(scan_name)

    if not failures:
        return f"No failed checks found for scan '{scan_name}'." if scan_name else "No failed compliance checks found."

    filtered = [
        r for r in failures if r["severity"].lower() == severity
    ]

    if not filtered:
        return f"No '{severity}' severity issues found in scan '{scan_name}'." if scan_name else f"No '{severity}' severity issues found."

    return "\n".join(
        f"{r['id']} - {r['description']} (Severity: {r['severity']})"
        for r in filtered
    )


import re

def analyze_scan_list(user_input: str) -> str:
    user_input_lower = user_input.lower()

    # Define filters
    status_filter = None
    result_filter = None

    # Detect status (e.g., "status done", "only done scans")
    status_match = re.search(r'\bstatus\s*[:=]?\s*(\w+)', user_input_lower)
    if status_match:
        status_filter = status_match.group(1).upper()
    elif "done" in user_input_lower:
        status_filter = "DONE"
    elif "pending" in user_input_lower:
        status_filter = "PENDING"

    # Detect result (e.g., "result non-compliant", "show compliant", etc.)
    if "non-compliant" in user_input_lower:
        result_filter = "NON-COMPLIANT"
    elif "compliant" in user_input_lower:
        result_filter = "COMPLIANT"
    elif "not applicable" in user_input_lower or "not-applicable" in user_input_lower:
        result_filter = "NOT-APPLICABLE"

    # Filter scans
    filtered_scans = []
    scans = list_all_scans()
    for scan in scans:
        status = scan.get("status", "").upper()
        result = scan.get("result", "").upper()
        name = scan.get("name", "<unknown>")

        if status_filter and status != status_filter:
            continue
        if result_filter and result != result_filter:
            continue

        filtered_scans.append({
            "name": name,
            "status": status,
            "result": result
        })
    print("-------------")
    print(filtered_scans)
    if not filtered_scans:
        return f"No compliance scans found matching the given criteria: {user_input}"

    # Format output
    lines = ["📝 Matching Compliance Scans:\n"]
    for scan in filtered_scans:
        lines.append(
            f"• {scan['name']} — Status: {scan['status']} — Result: {scan['result']} "
        )

    return "\n".join(lines)

def parse_and_call_analyze_checks(input_text: str) -> str:
    """
    Extract severity and optional scan name from input string and call analyze_checks().
    Handles formats like:
        - "high"
        - "high severity"
        - "high severity from ocp4-cis"
        - "high ocp4-cis"
    """
    print(f"[TOOL DEBUG] Parsing AnalyzeChecks input: {input_text}")

    # Normalize input
    input_text = input_text.strip().lower()

    # Try to extract severity
    severity_match = re.search(r"\b(low|medium|high|critical)\b", input_text)
    severity = severity_match.group(1) if severity_match else None

    # Try to extract scan name with "from" or "in"
    scan_match = re.search(r"(?:from|in|of)\s+([\w\-]+)", input_text)
    scan_name = scan_match.group(1) if scan_match else None

    # Fallback: if not found via "from/in", assume the next word after severity is scan name
    if severity and not scan_name:
        tokens = input_text.split()
        sev_index = tokens.index(severity)
        # Search for next non-severity keyword after severity
        for i in range(sev_index + 1, len(tokens)):
            possible_scan = tokens[i]
            if possible_scan not in ("severity", "failed", "checks", "rules", "violations", "list", "all", "of"):
                scan_name = possible_scan
                break

    print(f"[TOOL DEBUG] Final parsed severity: {severity}, scan_name: {scan_name}")

    if not severity:
        return "Could not determine severity level from input. Please specify one of: low, medium, high, critical."

    return analyze_checks(severity, scan_name)
