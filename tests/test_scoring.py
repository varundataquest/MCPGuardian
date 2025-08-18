"""Tests for security scoring functionality."""

import pytest
from mcp_multiagent_selector.security.scoring import score_server_from_dict


def test_perfect_score():
    """Test a server with perfect security score."""
    evidence = {
        "hash_pinning": True,
        "auth_model": "mtls",
        "maintainer_activity": 10,
        "risk_notes": "Clear scope and least privilege documented",
        "sbom": True,
        "summary": "Comprehensive rate limiting and observability features"
    }
    
    score, breakdown = score_server_from_dict(evidence)
    
    assert score == 100
    assert breakdown["signature_or_attestation"] == 25
    assert breakdown["https_or_mtls"] == 15
    assert breakdown["hash_pinning"] == 15
    assert breakdown["update_cadence"] == 10
    assert breakdown["least_privilege_docs"] == 10
    assert breakdown["sbom_or_aibom"] == 10
    assert breakdown["rate_limiting"] == 5
    assert breakdown["observability_docs"] == 5


def test_minimal_score():
    """Test a server with minimal security score."""
    evidence = {
        "hash_pinning": False,
        "auth_model": "none",
        "maintainer_activity": 0,
        "risk_notes": "",
        "sbom": False,
        "summary": "Basic functionality"
    }
    
    score, breakdown = score_server_from_dict(evidence)
    
    assert score == 0
    assert breakdown["signature_or_attestation"] == 0
    assert breakdown["https_or_mtls"] == 0
    assert breakdown["hash_pinning"] == 0
    assert breakdown["update_cadence"] == 0
    assert breakdown["least_privilege_docs"] == 0
    assert breakdown["sbom_or_aibom"] == 0


def test_cve_penalty():
    """Test CVE penalty in scoring."""
    evidence = {
        "hash_pinning": True,
        "auth_model": "https",
        "maintainer_activity": 5,
        "risk_notes": "Known CVE-2024-1234 vulnerability",
        "sbom": False,
        "summary": "Server with security issues"
    }
    
    score, breakdown = score_server_from_dict(evidence)
    
    assert score < 50  # Should be penalized
    assert breakdown["known_cves_or_redflags"] == -30


def test_https_only_auth():
    """Test HTTPS-only authentication scoring."""
    evidence = {
        "hash_pinning": False,
        "auth_model": "https_only",
        "maintainer_activity": 5,
        "risk_notes": "",
        "sbom": False,
        "summary": "HTTPS only server"
    }
    
    score, breakdown = score_server_from_dict(evidence)
    
    assert breakdown["https_or_mtls"] == 15


def test_api_key_auth():
    """Test API key authentication scoring."""
    evidence = {
        "hash_pinning": False,
        "auth_model": "api_key",
        "maintainer_activity": 5,
        "risk_notes": "",
        "sbom": False,
        "summary": "API key server"
    }
    
    score, breakdown = score_server_from_dict(evidence)
    
    assert breakdown["https_or_mtls"] == 5  # Partial credit for API key


def test_score_bounds():
    """Test that scores are properly bounded."""
    evidence = {
        "hash_pinning": True,
        "auth_model": "mtls",
        "maintainer_activity": 15,  # Over 10
        "risk_notes": "",
        "sbom": True,
        "summary": "Rate limiting and observability"
    }
    
    score, breakdown = score_server_from_dict(evidence)
    
    assert 0 <= score <= 100
    assert breakdown["update_cadence"] == 10  # Capped at 10 