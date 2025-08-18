"""Security scoring module for MCP servers."""

from typing import Dict, Any, Tuple
from ..models import Evidence


def score_server(evidence: Evidence) -> Tuple[int, Dict[str, Any]]:
    """
    Score a server based on security evidence.
    
    Returns:
        Tuple of (score, breakdown) where score is 0-100 and breakdown is detailed rubric
    """
    score = 0
    breakdown = {}
    
    def add_score(category: str, points: int, condition: bool = True):
        """Add points to score and record in breakdown."""
        nonlocal score
        if condition:
            score += points
            breakdown[category] = points
        else:
            breakdown[category] = 0
    
    # Signature/attestation present? (+25)
    add_score("signature_or_attestation", 25, evidence.hash_pinning)
    
    # HTTPS/mTLS documented? (+15)
    auth_model = evidence.auth_model or ""
    if auth_model.lower() in ["mtls", "oauth"]:
        add_score("https_or_mtls", 15)
    elif auth_model.lower() in ["api_key", "https_only", "https-only"]:
        add_score("https_or_mtls", 5)
    else:
        add_score("https_or_mtls", 0)
    
    # Hash pinning or artifact digest references? (+15)
    add_score("hash_pinning", 15, evidence.hash_pinning)
    
    # Update cadence (recent commits/releases)? (+10)
    activity_score = min(10, evidence.maintainer_activity or 0)
    add_score("update_cadence", activity_score)
    
    # Least-privilege/tool-scope clarity in docs? (+10)
    risk_notes = evidence.risk_notes or ""
    add_score("least_privilege_docs", 10, "scope" in risk_notes.lower())
    
    # SBOM/AI-BOM or dependency transparency? (+10)
    add_score("sbom_or_aibom", 10, evidence.sbom)
    
    # Known CVEs or red flags? (- up to 30)
    cve_penalty = 0
    rn = risk_notes.lower()
    negated_cve_phrases = [
        "no cve",
        "no known cve",
        "no known cves",
        "no vulnerabilities",
        "no known vulnerabilities",
        "without vulnerabilities",
        "no vulnerability",
        "no security issues",
        "no known security issues",
        "zero cves",
    ]
    has_negated_cve = any(phrase in rn for phrase in negated_cve_phrases)

    if not has_negated_cve:
        if "cve" in rn or "vulnerab" in rn:
            cve_penalty = 30
        elif any(kw in rn for kw in [
            "high risk",
            "critical risk",
            "known risk",
            "security risk",
            "severe risk",
        ]):
            cve_penalty = 15
    
    if cve_penalty > 0:
        breakdown["known_cves_or_redflags"] = -cve_penalty
        score -= cve_penalty
    
    # Rate limiting/abuse controls disclosed? (+5)
    summary = evidence.summary or ""
    add_score("rate_limiting", 5, "rate limit" in summary.lower())
    
    # Observability/traceability docs? (+5)
    add_score("observability_docs", 5, "trace" in summary.lower() or "log" in summary.lower())
    
    # Ensure score is within bounds
    final_score = max(0, min(100, score))
    
    return final_score, breakdown


def score_server_from_dict(evidence_dict: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """
    Score a server from a dictionary of evidence.
    
    Args:
        evidence_dict: Dictionary containing evidence fields
        
    Returns:
        Tuple of (score, breakdown)
    """
    # Create a mock Evidence object for scoring
    class MockEvidence:
        def __init__(self, data: Dict[str, Any]):
            self.hash_pinning = data.get("hash_pinning", False)
            self.auth_model = data.get("auth_model", "")
            self.maintainer_activity = data.get("maintainer_activity", 0)
            self.risk_notes = data.get("risk_notes", "")
            self.sbom = data.get("sbom", False)
            self.summary = data.get("summary", "")
    
    mock_evidence = MockEvidence(evidence_dict)
    return score_server(mock_evidence) 