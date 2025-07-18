# Fetch compliance scans via Kubernetes client
from kubernetes import client, config

GROUP = "compliance.openshift.io"
VERSION = "v1alpha1"
NAMESPACE = "qsafe-engineers"

config.load_kube_config()
custom_api = client.CustomObjectsApi()

#returns a list of scan names pulled from cluster resources (via command or API).
def list_all_scans(_: str = "") -> list[dict]:
    scans = custom_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural="compliancescans"
    )
    #result = scans.get("items", [])
    result = []
    for scan in scans.get("items", []):
        name = scan.get("metadata", {}).get("name", "unknown")
        # Adapt keys as needed—commonly 'phase' or 'state' or 'status'
        status = scan.get("status", {}).get("phase") or scan.get("status", {}).get("state") or "unknown"
        result_val = scan.get("status", {}).get("result", "unknown")
        result.append({
            "name": name,
            "status": status,
            "result": result_val
        })
    return result



def fetch_compliance_failures(scan_name: str = None):
    print(f"[TOOL DEBUG] Called: GetComplianceIssues with scan_name: {scan_name}")

    failed = []
    try:
        check_results = custom_api.list_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural="compliancecheckresults"
        )
    except Exception as e:
        print(f"[TOOL ERROR] Failed to fetch compliance check results: {e}")
        return failed

    for result in check_results.get("items", []):
        if result.get("status") != "FAIL":
            continue

        metadata = result.get("metadata", {})
        result_name = metadata.get("name", "unknown")
        owner_refs = metadata.get("ownerReferences", [])
        result_scan_name = owner_refs[0]["name"] if owner_refs else ""

        # If a specific scan is requested, filter by it
        if scan_name and result_scan_name != scan_name:
            continue

        failed.append({
            "id": result_name,
            "description": result.get("description", "N/A"),
            "instructions": result.get("instructions", "N/A"),
            "severity": result.get("severity", "unknown"),
            "rationale": result.get("rationale", "Not provided"),
            "remediation": result.get("instructions", "Not provided"),
            "scan": result_scan_name
        })

    print(f"[TOOL DEBUG] Found {len(failed)} failed check(s)")
    return failed

from kubernetes import client, config
from typing import Optional, List, Dict

def get_compliance_check_results(scan_name: Optional[str] = None,
                                  rule_name: Optional[str] = None) -> List[Dict]:
    """
    Fetches ComplianceCheckResult resources optionally filtered by scan name and/or rule name.

    :param scan_name: Name of the ComplianceScan (optional)
    :param rule_name: Rule ID or check name (e.g., 'ocp4-cis-api-server-audit-log-path') (optional)
    :param namespace: Namespace where compliance-operator is running
    :return: List of matching ComplianceCheckResult resources (as dicts)
    """
    # Load config
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    api = client.CustomObjectsApi()

    try:
        response = api.list_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural="compliancecheckresults"
        )

        items = response.get("items", [])

        # Apply filters based on presence of scan_name and/or rule_name
        results = [
            item for item in items
            if (scan_name is None or item.get("spec", {}).get("scanName") == scan_name) and
               (rule_name is None or item.get("spec", {}).get("check") == rule_name or
                item.get("metadata", {}).get("name", "").endswith(rule_name))
        ]

        return results

    except client.exceptions.ApiException as e:
        print(f"API error: {e}")
        return []

