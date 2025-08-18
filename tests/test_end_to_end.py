"""End-to-end tests for the MCP selector."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from mcp_multiagent_selector.graph import run_pipeline
from mcp_multiagent_selector.crawl.registries import MockRegistryCrawler
from mcp_multiagent_selector.crawl.web import MockWebCrawler


@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    """Test the complete pipeline end-to-end."""
    user_task = "I want to create an agent that can negotiate the best price for a gym membership"
    max_candidates = 10
    
    # Mock the registry crawler to return test data
    with patch('mcp_multiagent_selector.crawl.registries.get_registry_crawler') as mock_get_crawler:
        mock_crawler = MockRegistryCrawler()
        mock_get_crawler.return_value = mock_crawler
        
        # Mock the web crawler
        with patch('mcp_multiagent_selector.crawl.web.WebCrawler') as mock_web_crawler_class:
            mock_web_crawler = MockWebCrawler()
            mock_web_crawler_class.return_value = mock_web_crawler
            
            # Mock the LLM provider
            with patch('mcp_multiagent_selector.graph.llm') as mock_llm:
                mock_llm.summarize.return_value = {
                    "summary": "Test server for gym membership negotiation",
                    "doc_quality": 8,
                    "maintainer_activity": 7,
                    "auth_model": "oauth",
                    "hash_pinning": True,
                    "sbom": True,
                    "risk_notes": "Well documented with clear scope"
                }
                
                # Run the pipeline
                result = await run_pipeline(user_task, max_candidates)
                
                # Verify the result structure
                assert "ranked_servers" in result
                assert "total_candidates" in result
                assert "run_id" in result
                
                # Verify we got some results
                assert len(result["ranked_servers"]) > 0
                assert result["total_candidates"] > 0
                
                # Verify server structure
                server = result["ranked_servers"][0]
                assert "name" in server
                assert "endpoint" in server
                assert "score" in server
                assert "summary" in server
                assert "rubric_breakdown" in server
                assert "source" in server
                assert "discovered_at" in server
                
                # Verify score is within bounds
                assert 0 <= server["score"] <= 100


@pytest.mark.asyncio
async def test_pipeline_with_empty_registry():
    """Test pipeline behavior with empty registry."""
    user_task = "Test task with no servers"
    max_candidates = 10
    
    # Mock empty registry
    with patch('mcp_multiagent_selector.crawl.registries.get_registry_crawler') as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.crawl_registries.return_value = []
        mock_get_crawler.return_value = mock_crawler
        
        # Run the pipeline
        result = await run_pipeline(user_task, max_candidates)
        
        # Should still complete successfully
        assert "ranked_servers" in result
        assert "total_candidates" in result
        assert result["total_candidates"] == 0
        assert len(result["ranked_servers"]) == 0


@pytest.mark.asyncio
async def test_pipeline_error_handling():
    """Test pipeline error handling."""
    user_task = "Test task"
    max_candidates = 10
    
    # Mock registry crawler to raise an exception
    with patch('mcp_multiagent_selector.crawl.registries.get_registry_crawler') as mock_get_crawler:
        mock_crawler = MagicMock()
        mock_crawler.crawl_registries.side_effect = Exception("Registry error")
        mock_get_crawler.return_value = mock_crawler
        
        # Pipeline should handle the error gracefully
        with pytest.raises(Exception):
            await run_pipeline(user_task, max_candidates)


def test_mock_registry_crawler():
    """Test the mock registry crawler."""
    crawler = MockRegistryCrawler()
    
    # Test that it returns the expected mock data
    candidates = asyncio.run(crawler.crawl_registries())
    
    assert len(candidates) == 3
    assert candidates[0].name == "mock-calendar-server"
    assert candidates[1].name == "mock-webscraping-server"
    assert candidates[2].name == "mock-email-server"
    
    # Verify candidate structure
    for candidate in candidates:
        assert candidate.name
        assert candidate.endpoint
        assert candidate.source == "mock_registry"


def test_mock_web_crawler():
    """Test the mock web crawler."""
    crawler = MockWebCrawler()
    
    # Test that it returns mock documentation
    docs = asyncio.run(crawler.fetch_docs(["https://example.com"]))
    
    assert len(docs) == 4
    assert any("mock documentation" in doc for doc in docs)
    assert any("HTTPS authentication" in doc for doc in docs)
    assert any("rate limiting" in doc for doc in docs)
    assert any("SBOM" in doc for doc in docs) 