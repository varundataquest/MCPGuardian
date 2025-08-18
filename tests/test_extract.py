"""Tests for extraction functionality."""

import pytest
from mcp_multiagent_selector.crawl.extract import (
    extract_capabilities,
    extract_auth_model,
    extract_maintainer_activity,
    extract_security_indicators,
    extract_risk_notes,
    extract_doc_quality,
    extract_all_metadata
)


def test_extract_capabilities():
    """Test capability extraction."""
    docs = [
        "This server provides calendar management and scheduling capabilities",
        "It also supports email notifications and web scraping features",
        "Database integration and API endpoints are available"
    ]
    
    capabilities = extract_capabilities(docs)
    
    assert "calendar" in capabilities
    assert "email" in capabilities
    assert "webscraping" in capabilities
    assert "database" in capabilities
    assert "api" in capabilities


def test_extract_auth_model():
    """Test authentication model extraction."""
    # Test OAuth
    docs = ["This server uses OAuth 2.0 for authentication"]
    auth_model = extract_auth_model(docs)
    assert auth_model == "oauth"
    
    # Test API key
    docs = ["Authentication requires an API key in the header"]
    auth_model = extract_auth_model(docs)
    assert auth_model == "api_key"
    
    # Test mTLS
    docs = ["Client certificates are required for mTLS authentication"]
    auth_model = extract_auth_model(docs)
    assert auth_model == "mtls"
    
    # Test HTTPS only
    docs = ["HTTPS is required for all connections"]
    auth_model = extract_auth_model(docs)
    assert auth_model == "https_only"
    
    # Test unknown
    docs = ["Basic server functionality"]
    auth_model = extract_auth_model(docs)
    assert auth_model == "unknown"


def test_extract_maintainer_activity():
    """Test maintainer activity extraction."""
    # High activity
    docs = [
        "Recently updated with new features",
        "Active development and regular commits",
        "Latest version 2.1.0 released",
        "Well maintained and supported"
    ]
    activity = extract_maintainer_activity(docs)
    assert activity >= 8
    
    # Low activity
    docs = ["Basic server functionality"]
    activity = extract_maintainer_activity(docs)
    assert activity == 5  # Default middle score


def test_extract_security_indicators():
    """Test security indicators extraction."""
    docs = [
        "Hash pinning is implemented for security",
        "SBOM (Software Bill of Materials) is available",
        "Rate limiting is configured",
        "Comprehensive logging and observability"
    ]
    
    indicators = extract_security_indicators(docs)
    
    assert indicators["hash_pinning"] == True
    assert indicators["sbom"] == True
    assert indicators["rate_limiting"] == True
    assert indicators["observability"] == True


def test_extract_risk_notes():
    """Test risk notes extraction."""
    # Test CVE
    docs = ["Known CVE-2024-1234 vulnerability"]
    risk_notes = extract_risk_notes(docs)
    assert "CVE-2024-1234" in risk_notes
    
    # Test deprecated
    docs = ["This version is deprecated"]
    risk_notes = extract_risk_notes(docs)
    assert "deprecated" in risk_notes
    
    # Test beta
    docs = ["Beta version with experimental features"]
    risk_notes = extract_risk_notes(docs)
    assert "beta" in risk_notes
    
    # Test no risks
    docs = ["Stable production server"]
    risk_notes = extract_risk_notes(docs)
    assert risk_notes == ""


def test_extract_doc_quality():
    """Test documentation quality extraction."""
    # High quality docs
    docs = [
        "API examples and sample code provided",
        "Comprehensive endpoint documentation",
        "Parameter descriptions and error handling",
        "Authentication and security guidelines",
        "Rate limiting and quota information",
        "Logging and debugging instructions"
    ]
    quality = extract_doc_quality(docs)
    assert quality >= 8
    
    # Low quality docs
    docs = ["Basic server"]
    quality = extract_doc_quality(docs)
    assert quality == 0


def test_extract_all_metadata():
    """Test complete metadata extraction."""
    docs = [
        "Calendar management server with OAuth authentication",
        "Hash pinning and SBOM available",
        "Rate limiting and comprehensive logging",
        "Active development with regular updates",
        "Clear scope and least privilege documented"
    ]
    
    metadata = extract_all_metadata(docs)
    
    assert "calendar" in metadata["capabilities"]
    assert metadata["auth_model"] == "oauth"
    assert metadata["security_indicators"]["hash_pinning"] == True
    assert metadata["security_indicators"]["sbom"] == True
    assert metadata["security_indicators"]["rate_limiting"] == True
    assert metadata["security_indicators"]["observability"] == True
    assert metadata["maintainer_activity"] >= 7
    assert metadata["doc_quality"] >= 5
    assert "scope" in metadata["risk_notes"] 