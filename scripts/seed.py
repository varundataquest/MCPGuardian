"""Seed script for testing and demo purposes."""

import asyncio
from datetime import datetime

from mcp_multiagent_selector.db import SessionLocal
from mcp_multiagent_selector.models import Server, Evidence, Score, Run


async def seed_database():
    """Seed the database with test data."""
    db = SessionLocal()
    try:
        # Create test servers
        servers = [
            Server(
                name="test-calendar-server",
                endpoint="https://api.example.com/calendar",
                source="test",
                discovered_at=datetime.utcnow(),
                last_checked_at=datetime.utcnow()
            ),
            Server(
                name="test-webscraping-server",
                endpoint="https://api.example.com/scraper",
                source="test",
                discovered_at=datetime.utcnow(),
                last_checked_at=datetime.utcnow()
            ),
            Server(
                name="test-email-server",
                endpoint="https://api.example.com/email",
                source="test",
                discovered_at=datetime.utcnow(),
                last_checked_at=datetime.utcnow()
            )
        ]
        
        for server in servers:
            db.add(server)
        db.commit()
        
        # Create evidence for each server
        evidence_data = [
            {
                "summary": "Calendar management server with comprehensive scheduling capabilities",
                "doc_quality": 8,
                "maintainer_activity": 7,
                "auth_model": "oauth",
                "hash_pinning": True,
                "sbom": True,
                "risk_notes": "Well documented with clear scope"
            },
            {
                "summary": "Web scraping and data extraction server with rate limiting",
                "doc_quality": 9,
                "maintainer_activity": 8,
                "auth_model": "api_key",
                "hash_pinning": True,
                "sbom": False,
                "risk_notes": "Active development, good documentation"
            },
            {
                "summary": "Email management server with SMTP/IMAP support",
                "doc_quality": 6,
                "maintainer_activity": 5,
                "auth_model": "https_only",
                "hash_pinning": False,
                "sbom": False,
                "risk_notes": "Basic functionality, limited documentation"
            }
        ]
        
        for i, server in enumerate(servers):
            evidence = Evidence(
                server_id=server.id,
                **evidence_data[i]
            )
            db.add(evidence)
        db.commit()
        
        # Create scores for each server
        scores = [85, 92, 65]  # High, very high, medium scores
        
        for i, server in enumerate(servers):
            score = Score(
                server_id=server.id,
                score=scores[i],
                rubric={
                    "signature_or_attestation": 25,
                    "https_or_mtls": 15,
                    "hash_pinning": 15 if evidence_data[i]["hash_pinning"] else 0,
                    "update_cadence": evidence_data[i]["maintainer_activity"],
                    "least_privilege_docs": 10,
                    "sbom_or_aibom": 10 if evidence_data[i]["sbom"] else 0,
                    "rate_limiting": 5,
                    "observability_docs": 5
                }
            )
            db.add(score)
        db.commit()
        
        # Create a test run
        run = Run(
            user_task="I want to create an agent that can negotiate the best price for a gym membership",
            max_candidates=50,
            status="completed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            result={
                "ranked_servers": [
                    {
                        "name": "test-webscraping-server",
                        "endpoint": "https://api.example.com/scraper",
                        "score": 92,
                        "summary": "Web scraping and data extraction server with rate limiting",
                        "rubric_breakdown": {"signature_or_attestation": 25, "https_or_mtls": 15},
                        "source": "test",
                        "discovered_at": datetime.utcnow().isoformat()
                    },
                    {
                        "name": "test-calendar-server",
                        "endpoint": "https://api.example.com/calendar",
                        "score": 85,
                        "summary": "Calendar management server with comprehensive scheduling capabilities",
                        "rubric_breakdown": {"signature_or_attestation": 25, "https_or_mtls": 15},
                        "source": "test",
                        "discovered_at": datetime.utcnow().isoformat()
                    }
                ],
                "total_candidates": 2
            }
        )
        db.add(run)
        db.commit()
        
        print("Database seeded successfully!")
        print(f"Created {len(servers)} servers, {len(evidence_data)} evidence records, {len(scores)} scores, and 1 run")
        
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_database()) 