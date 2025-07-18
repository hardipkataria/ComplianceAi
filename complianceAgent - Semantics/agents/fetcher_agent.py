# fetcher_agent.py

from tools.k8s_tools import fetch_compliance_failures

def get_failed_checks(scan_name: str | None = None) -> str:
    """Returns a formatted list of failed compliance rules.

    Args:
        scan_name (str | None): Optional scan name to filter by.

    Returns:
        str: List of failed checks.
    """
    failures = fetch_compliance_failures(scan_name)
    if not failures:
        return f"No failed checks found for scan '{scan_name}'." if scan_name else "No failed compliance checks found."

    return "\n".join(
        f"{r['id']} - {r['description']} (Severity: {r['severity']})"
        for r in failures
    )
