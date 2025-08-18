"""SQLAlchemy models for the MCP Multi-Agent Selector."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Server(Base):
    """MCP server information."""
    
    __tablename__ = "servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False, unique=True, index=True)
    source = Column(String(100), nullable=False)  # registry, web, etc.
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    raw_json = Column(JSON, nullable=True)
    
    # Relationships
    evidence = relationship("Evidence", back_populates="server")
    scores = relationship("Score", back_populates="server")


class Evidence(Base):
    """Evidence collected about a server."""
    
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    summary = Column(Text, nullable=True)
    doc_quality = Column(Integer, nullable=True)  # 0-10
    maintainer_activity = Column(Integer, nullable=True)  # 0-10
    auth_model = Column(String(100), nullable=True)
    hash_pinning = Column(Boolean, default=False)
    sbom = Column(Boolean, default=False)
    risk_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server", back_populates="evidence")


class Score(Base):
    """Security scores for servers."""
    
    __tablename__ = "scores"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    score = Column(Integer, nullable=False)  # 0-100
    rubric = Column(JSON, nullable=True)  # Detailed breakdown
    computed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    server = relationship("Server", back_populates="scores")


class Run(Base):
    """Pipeline execution runs."""
    
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    user_task = Column(Text, nullable=False)
    max_candidates = Column(Integer, default=50)
    status = Column(String(50), default="running")  # running, completed, failed
    result = Column(JSON, nullable=True)  # Final ranked results 