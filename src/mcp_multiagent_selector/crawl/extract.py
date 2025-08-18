"""Extraction utilities for parsing capabilities and metadata from documentation."""

import re
from typing import Dict, Any, List, Optional


def extract_capabilities(docs: List[str]) -> List[str]:
    """Extract capability keywords from documentation."""
    capabilities = []
    
    # Common capability keywords
    capability_patterns = [
        r'\b(calendar|scheduling|appointment)\b',
        r'\b(email|mail|smtp|imap)\b',
        r'\b(webscraping|scraping|crawling|extraction)\b',
        r'\b(database|sql|nosql|storage)\b',
        r'\b(file|document|pdf|image)\b',
        r'\b(api|rest|graphql|rpc)\b',
        r'\b(authentication|auth|oauth|jwt)\b',
        r'\b(notification|alert|push|sms)\b',
        r'\b(analytics|metrics|logging|monitoring)\b',
        r'\b(integration|connector|plugin)\b'
    ]
    
    for doc in docs:
        doc_lower = doc.lower()
        for pattern in capability_patterns:
            matches = re.findall(pattern, doc_lower)
            capabilities.extend(matches)
    
    return list(set(capabilities))  # Remove duplicates


def extract_auth_model(docs: List[str]) -> str:
    """Extract authentication model from documentation."""
    auth_keywords = {
        'api_key': ['api key', 'apikey', 'x-api-key', 'authorization'],
        'oauth': ['oauth', 'oauth2', 'openid connect'],
        'mtls': ['mtls', 'mTLS', 'mutual tls', 'client certificate'],
        'https_only': ['https only', 'ssl', 'tls'],
        'none': ['no auth', 'public', 'anonymous']
    }
    
    for doc in docs:
        doc_lower = doc.lower()
        for auth_type, keywords in auth_keywords.items():
            if any(keyword in doc_lower for keyword in keywords):
                return auth_type
    
    return 'unknown'


def extract_maintainer_activity(docs: List[str]) -> int:
    """Extract maintainer activity score from documentation."""
    activity_indicators = [
        r'\b(updated|recent|latest|new)\b',
        r'\b(commit|version|release)\b',
        r'\b(active|maintained|supported)\b',
        r'\b(star|fork|contribution)\b'
    ]
    
    score = 5  # Default middle score
    
    for doc in docs:
        doc_lower = doc.lower()
        for pattern in activity_indicators:
            matches = re.findall(pattern, doc_lower)
            if matches:
                score += 1
    
    return min(10, max(0, score))


def extract_security_indicators(docs: List[str]) -> Dict[str, bool]:
    """Extract security indicators from documentation."""
    indicators = {
        'hash_pinning': False,
        'sbom': False,
        'rate_limiting': False,
        'observability': False
    }
    
    for doc in docs:
        doc_lower = doc.lower()
        
        # Hash pinning
        if any(term in doc_lower for term in ['hash', 'digest', 'checksum', 'fingerprint']):
            indicators['hash_pinning'] = True
        
        # SBOM
        if any(term in doc_lower for term in ['sbom', 'bom', 'bill of materials', 'dependency']):
            indicators['sbom'] = True
        
        # Rate limiting
        if any(term in doc_lower for term in ['rate limit', 'throttle', 'quota']):
            indicators['rate_limiting'] = True
        
        # Observability
        if any(term in doc_lower for term in ['log', 'trace', 'monitor', 'observability']):
            indicators['observability'] = True
    
    return indicators


def extract_risk_notes(docs: List[str]) -> str:
    """Extract risk notes from documentation."""
    risk_indicators = []
    
    risk_patterns = [
        r'\b(cve|cve-\d{4}-\d+)\b',
        r'\b(vulnerability|security issue|bug)\b',
        r'\b(deprecated|deprecation|legacy)\b',
        r'\b(beta|alpha|experimental)\b',
        r'\b(unsupported|discontinued)\b'
    ]
    
    for doc in docs:
        doc_lower = doc.lower()
        for pattern in risk_patterns:
            matches = re.findall(pattern, doc_lower)
            risk_indicators.extend(matches)
    
    if risk_indicators:
        return f"Found risk indicators: {', '.join(set(risk_indicators))}"
    
    return ""


def extract_doc_quality(docs: List[str]) -> int:
    """Extract documentation quality score."""
    if not docs:
        return 0
    
    quality_indicators = [
        r'\b(example|sample|demo)\b',
        r'\b(api|endpoint|method)\b',
        r'\b(parameter|argument|option)\b',
        r'\b(error|exception|status)\b',
        r'\b(authentication|auth|security)\b',
        r'\b(rate limit|quota|throttle)\b',
        r'\b(log|trace|debug)\b'
    ]
    
    score = 0
    
    for doc in docs:
        doc_lower = doc.lower()
        for pattern in quality_indicators:
            matches = re.findall(pattern, doc_lower)
            if matches:
                score += 1
    
    # Normalize score to 0-10 range
    return min(10, max(0, score // 2))


def extract_all_metadata(docs: List[str]) -> Dict[str, Any]:
    """Extract all metadata from documentation."""
    return {
        'capabilities': extract_capabilities(docs),
        'auth_model': extract_auth_model(docs),
        'maintainer_activity': extract_maintainer_activity(docs),
        'security_indicators': extract_security_indicators(docs),
        'risk_notes': extract_risk_notes(docs),
        'doc_quality': extract_doc_quality(docs)
    } 