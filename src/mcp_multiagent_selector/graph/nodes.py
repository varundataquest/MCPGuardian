"""LangGraph nodes for the multi-agent MCP selector."""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Server, Evidence, Score, Run
from ..schemas import Candidate, EvidenceSummary
from ..crawl.registries import get_registry_crawler
from ..crawl.web import WebCrawler
from ..crawl.extract import extract_all_metadata
from ..security.scoring import score_server_from_dict
from .llm import llm


class ManagerAgent:
    """Manager agent that orchestrates the entire workflow."""
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the manager agent."""
        user_task = state.get("user_task", "")
        max_candidates = state.get("max_candidates", 50)
        
        print(f"Manager: Starting pipeline for task: {user_task}")
        
        # Create a new run record
        db = SessionLocal()
        try:
            run = Run(
                user_task=user_task,
                max_candidates=max_candidates,
                status="running"
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            state["run_id"] = run.id
        finally:
            db.close()
        
        # The workflow will be orchestrated by LangGraph
        return state


class CrawlerAgent:
    """Agent responsible for crawling MCP registries and web."""
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the crawler agent."""
        user_task = state.get("user_task", "")
        max_candidates = state.get("max_candidates", 50)
        
        print(f"Crawler: Discovering candidates for task: {user_task}")
        
        # Get registry crawler
        registry_crawler = get_registry_crawler()
        
        # Crawl registries
        candidates = await registry_crawler.crawl_registries()
        
        # Limit candidates
        candidates = candidates[:max_candidates]
        
        print(f"Crawler: Found {len(candidates)} candidates")
        
        # Add candidates to state
        state["candidates"] = [candidate.dict() for candidate in candidates]
        
        return state


class WriterAgent:
    """Agent responsible for summarizing and persisting evidence."""
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the writer agent."""
        candidates = state.get("candidates", [])
        user_task = state.get("user_task", "")
        
        print(f"Writer: Processing {len(candidates)} candidates")
        
        db = SessionLocal()
        try:
            server_ids = []
            
            for candidate_data in candidates:
                candidate = Candidate(**candidate_data)
                
                # Check if server already exists
                existing_server = db.query(Server).filter(
                    Server.endpoint == candidate.endpoint
                ).first()
                
                if existing_server:
                    server = existing_server
                    server.last_checked_at = datetime.utcnow()
                else:
                    # Create new server
                    server = Server(
                        name=candidate.name,
                        endpoint=candidate.endpoint,
                        source=candidate.source,
                        raw_json=candidate.registry_meta
                    )
                    db.add(server)
                    db.commit()
                    db.refresh(server)
                
                # Fetch documentation
                web_crawler = WebCrawler()
                doc_urls = web_crawler.extract_doc_urls(candidate.endpoint)
                docs = await web_crawler.fetch_docs(doc_urls)
                
                # Extract metadata
                metadata = extract_all_metadata(docs)
                
                # Use LLM to summarize
                llm_summary = await llm.summarize(candidate.dict(), user_task)
                
                # Create evidence record
                evidence = Evidence(
                    server_id=server.id,
                    summary=llm_summary.get("summary", ""),
                    doc_quality=llm_summary.get("doc_quality", metadata["doc_quality"]),
                    maintainer_activity=llm_summary.get("maintainer_activity", metadata["maintainer_activity"]),
                    auth_model=llm_summary.get("auth_model", metadata["auth_model"]),
                    hash_pinning=llm_summary.get("hash_pinning", metadata["security_indicators"]["hash_pinning"]),
                    sbom=llm_summary.get("sbom", metadata["security_indicators"]["sbom"]),
                    risk_notes=llm_summary.get("risk_notes", metadata["risk_notes"])
                )
                
                db.add(evidence)
                server_ids.append(server.id)
            
            db.commit()
            print(f"Writer: Processed {len(server_ids)} servers")
            
            state["server_ids"] = server_ids
            
        finally:
            db.close()
        
        return state


class SecurityAgent:
    """Agent responsible for security scoring."""
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the security agent."""
        server_ids = state.get("server_ids", [])
        
        print(f"Security: Scoring {len(server_ids)} servers")
        
        db = SessionLocal()
        try:
            for server_id in server_ids:
                # Get the latest evidence for this server
                evidence = db.query(Evidence).filter(
                    Evidence.server_id == server_id
                ).order_by(Evidence.created_at.desc()).first()
                
                if evidence:
                    # Score the server
                    score, rubric = score_server_from_dict({
                        "hash_pinning": evidence.hash_pinning,
                        "auth_model": evidence.auth_model,
                        "maintainer_activity": evidence.maintainer_activity,
                        "risk_notes": evidence.risk_notes,
                        "sbom": evidence.sbom,
                        "summary": evidence.summary
                    })
                    
                    # Create score record
                    score_record = Score(
                        server_id=server_id,
                        score=score,
                        rubric=rubric
                    )
                    db.add(score_record)
            
            db.commit()
            print(f"Security: Scored {len(server_ids)} servers")
            
        finally:
            db.close()
        
        return state


class FinalizerAgent:
    """Agent that finalizes the pipeline and returns results."""
    
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the finalizer agent."""
        run_id = state.get("run_id")
        
        print(f"Finalizer: Finalizing run {run_id}")
        
        db = SessionLocal()
        try:
            # Get ranked results
            results = db.query(Server, Score, Evidence).join(
                Score, Server.id == Score.server_id
            ).join(
                Evidence, Server.id == Evidence.server_id
            ).order_by(Score.score.desc()).all()
            
            # Format results
            ranked_servers = []
            for server, score, evidence in results:
                ranked_server = {
                    "name": server.name,
                    "endpoint": server.endpoint,
                    "score": score.score,
                    "summary": evidence.summary,
                    "rubric_breakdown": score.rubric,
                    "source": server.source,
                    "discovered_at": server.discovered_at.isoformat()
                }
                ranked_servers.append(ranked_server)
            
            # Update run record
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "completed"
                run.finished_at = datetime.utcnow()
                run.result = {
                    "ranked_servers": ranked_servers,
                    "total_candidates": len(ranked_servers)
                }
            
            db.commit()
            
            print(f"Finalizer: Completed with {len(ranked_servers)} ranked servers")
            
            state["ranked_servers"] = ranked_servers
            state["total_candidates"] = len(ranked_servers)
            
        finally:
            db.close()
        
        return state 