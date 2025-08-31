"""
Shared core engine for both web UI and MCP server modes.
Provides unified access to server discovery, security analysis, and crawling functionality.
"""

import asyncio
from typing import Dict, List, Optional, AsyncIterator, Any
from dataclasses import dataclass
import json
import time

from .search import nl_to_filters
from .main import _sanitize_name
from .db.supabase_client import get_supabase_client, SupabaseNotConfigured
from .crew.pipeline import run_pipeline, CrawlConfig
from .security.scoring_agent import score_enriched_server


@dataclass
class SearchResult:
    """Unified search result format"""
    items: List[Dict]
    total: int
    offset: int
    limit: int


@dataclass
class SecurityAnalysis:
    """Security analysis result"""
    server_id: str
    score_overall: float
    breakdown: Dict[str, Any]
    recommendations: List[str]
    risk_factors: List[str]


@dataclass
class ServerRecommendation:
    """Server recommendation with reasoning"""
    server: Dict
    security_score: float
    match_score: float
    reasoning: str


class MCPGuardEngine:
    """Shared engine for both web and MCP server modes"""
    
    def __init__(self):
        self.active_crawl_id = None
    
    async def search_servers(
        self, 
        query: str = "", 
        limit: int = 20, 
        offset: int = 0, 
        sort: str = "rank",
        registry_filter: Optional[List[str]] = None,
        min_security_score: Optional[float] = None
    ) -> SearchResult:
        """
        Search MCP servers with optional filtering.
        Used by both FastAPI /search endpoint and MCP search_mcp_servers tool.
        """
        try:
            sb = get_supabase_client()
        except SupabaseNotConfigured:
            return SearchResult(items=[], total=0, offset=offset, limit=limit)
        
        # Parse query filters
        filters, residual = nl_to_filters(query)
        
        # Apply registry filter if provided
        if registry_filter:
            filters.registry_in = registry_filter
        
        # Clamp parameters
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        
        allowed_sorts = {"rank", "stars", "recent", "score"}
        if sort not in allowed_sorts:
            sort = "rank"
        
        try:
            # Search using RPC
            rpc_params = {
                "query": residual,
                "registry_in": filters.registry_in,
                "tags_any": filters.tags_any,
                "limit_count": limit,
                "offset_count": offset,
                "sort_key": filters.sort or sort,
            }
            items_resp = sb.rpc("search_servers", rpc_params).execute()
            count_resp = sb.rpc("search_servers_count", {
                "query": residual,
                "registry_in": filters.registry_in,
                "tags_any": filters.tags_any,
            }).execute()
            
            items = items_resp.data or []
            for item in items:
                item["name"] = _sanitize_name(item.get("name") or "")
            
            # Attach latest scores
            items = await self._attach_latest_scores(sb, items)
            
            # Filter by minimum security score if specified
            if min_security_score is not None:
                items = [
                    item for item in items 
                    if (item.get("latest_score", {}).get("score_overall", 0) or 0) >= min_security_score
                ]
            
            total = (count_resp.data or [0])[0] if isinstance(count_resp.data, list) else count_resp.data or 0
            
            return SearchResult(items=items, total=total, offset=offset, limit=limit)
            
        except Exception as e:
            # Fallback to direct table query
            print(f"RPC search failed, using fallback: {e}")
            return await self._fallback_search(sb, query, limit, offset, sort)
    
    async def get_server_details(self, server_id: str) -> Optional[Dict]:
        """Get comprehensive server details by ID"""
        try:
            sb = get_supabase_client()
            result = sb.table("servers").select("*").eq("id", server_id).execute()
            if result.data:
                server = result.data[0]
                server["name"] = _sanitize_name(server.get("name") or "")
                # Attach latest score
                servers_with_scores = await self._attach_latest_scores(sb, [server])
                return servers_with_scores[0] if servers_with_scores else server
            return None
        except Exception as e:
            print(f"Error fetching server details: {e}")
            return None
    
    async def get_server_by_url(self, homepage_url: str) -> Optional[Dict]:
        """Get server details by homepage URL"""
        try:
            sb = get_supabase_client()
            result = sb.table("servers").select("*").eq("homepage_url", homepage_url).execute()
            if result.data:
                server = result.data[0]
                server["name"] = _sanitize_name(server.get("name") or "")
                servers_with_scores = await self._attach_latest_scores(sb, [server])
                return servers_with_scores[0] if servers_with_scores else server
            return None
        except Exception as e:
            print(f"Error fetching server by URL: {e}")
            return None
    
    async def analyze_server_security(self, server_id: str) -> Optional[SecurityAnalysis]:
        """Get security analysis for a server"""
        server = await self.get_server_details(server_id)
        if not server:
            return None
        
        try:
            sb = get_supabase_client()
            # Get latest score
            score_result = sb.table("server_scores").select("*").eq("server_id", server_id).order("created_at", desc=True).limit(1).execute()
            
            if score_result.data:
                score_data = score_result.data[0]
                breakdown = score_data.get("breakdown_json", {})
                
                # Generate recommendations based on score breakdown
                recommendations = self._generate_security_recommendations(breakdown)
                risk_factors = self._identify_risk_factors(breakdown)
                
                return SecurityAnalysis(
                    server_id=server_id,
                    score_overall=float(score_data["score_overall"]),
                    breakdown=breakdown,
                    recommendations=recommendations,
                    risk_factors=risk_factors
                )
            
            return None
        except Exception as e:
            print(f"Error analyzing server security: {e}")
            return None
    
    async def recommend_servers(
        self, 
        use_case: str, 
        min_security_score: float = 0.5,
        limit: int = 10
    ) -> List[ServerRecommendation]:
        """Get AI-curated server recommendations based on use case"""
        
        # Keywords mapping for different use cases
        use_case_keywords = {
            "file operations": ["file", "filesystem", "files", "directory", "path"],
            "github": ["github", "git", "repository", "repo", "version control"],
            "code analysis": ["code", "ast", "syntax", "analysis", "parser", "lint"],
            "web scraping": ["web", "scraping", "html", "http", "requests", "crawler"],
            "database": ["database", "sql", "postgres", "sqlite", "db", "storage"],
            "ai": ["ai", "llm", "openai", "anthropic", "model", "completion"],
            "security": ["security", "auth", "encryption", "safe", "secure", "vulnerability"],
        }
        
        # Find relevant keywords
        query_terms = []
        use_case_lower = use_case.lower()
        for case, keywords in use_case_keywords.items():
            if case in use_case_lower or any(keyword in use_case_lower for keyword in keywords):
                query_terms.extend(keywords[:3])  # Take top 3 keywords
        
        # If no specific keywords found, use the use case directly
        if not query_terms:
            query_terms = [use_case]
        
        # Search for relevant servers
        search_query = " ".join(query_terms[:5])  # Limit to 5 terms
        result = await self.search_servers(
            query=search_query,
            limit=limit * 2,  # Get more to filter
            sort="score",
            min_security_score=min_security_score
        )
        
        recommendations = []
        for server in result.items[:limit]:
            # Calculate match score based on relevance
            match_score = self._calculate_match_score(server, use_case, query_terms)
            
            # Generate reasoning
            reasoning = self._generate_recommendation_reasoning(server, use_case, match_score)
            
            recommendations.append(ServerRecommendation(
                server=server,
                security_score=server.get("latest_score", {}).get("score_overall", 0) or 0,
                match_score=match_score,
                reasoning=reasoning
            ))
        
        # Sort by combination of match score and security score
        recommendations.sort(
            key=lambda r: (r.match_score * 0.6 + r.security_score * 0.4), 
            reverse=True
        )
        
        return recommendations
    
    async def analyze_custom_server(self, url: str) -> Dict:
        """Analyze any MCP server URL on-demand"""
        # Check if already in database
        existing = await self.get_server_by_url(url)
        if existing:
            return {
                "status": "found_existing",
                "server": existing,
                "message": "Server already analyzed and in database"
            }
        
        # Perform basic analysis
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=10)
                if response.status_code >= 400:
                    return {
                        "status": "error",
                        "message": f"Server returned HTTP {response.status_code}",
                        "url": url
                    }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to connect: {str(e)}",
                "url": url
            }
        
        # Create temporary server entry for analysis
        temp_server = {
            "name": url.split("/")[-1] or "Custom Server",
            "homepage_url": url,
            "repo_url": None,
            "description": "Custom server analyzed on-demand",
            "registry": "custom",
            "tags": []
        }
        
        # Perform security scoring
        try:
            score_result = await score_enriched_server(temp_server)
            return {
                "status": "analyzed",
                "server": temp_server,
                "security_analysis": score_result,
                "message": "Server analyzed successfully"
            }
        except Exception as e:
            return {
                "status": "partial_analysis",
                "server": temp_server,
                "message": f"Basic connectivity confirmed, but security analysis failed: {str(e)}"
            }
    
    async def start_discovery_crawl(
        self,
        max_servers_per_registry: Optional[Dict[str, int]] = None
    ) -> str:
        """Start server discovery crawl and return crawl ID"""
        if max_servers_per_registry is None:
            max_servers_per_registry = {"registry_1": 100, "registry_2": 100}
            
        config = CrawlConfig(
            enabled_registries=list(max_servers_per_registry.keys()),
            max_pages_per_registry={k: 9999 for k in max_servers_per_registry.keys()},
            max_items_per_registry=max_servers_per_registry
        )
        
        crawl_id = f"mcp_crawl_{int(time.time())}"
        self.active_crawl_id = crawl_id
        
        # Start crawl in background
        asyncio.create_task(self._run_crawl_background(config, crawl_id))
        
        return crawl_id
    
    async def get_crawl_status(self) -> Dict:
        """Get current crawl status"""
        return {
            "active": self.active_crawl_id is not None,
            "crawl_id": self.active_crawl_id
        }
    
    # Private helper methods
    async def _attach_latest_scores(self, sb, items: List[Dict]) -> List[Dict]:
        """Attach latest security scores to server items"""
        if not items:
            return items
        
        server_ids = [str(item["id"]) for item in items if item.get("id") is not None]

        # Step 1: Try RPC to fetch latest stored scores (fast path)
        scores_map: Dict[str, Dict] = {}
        try:
            scores_result = sb.rpc("get_latest_scores", {"server_ids": server_ids}).execute()
            for score in (scores_result.data or []):
                sid = str(score.get("server_id"))
                if sid and sid not in scores_map:
                    scores_map[sid] = score
        except Exception as e:
            # RPC not available; fall back to direct table query below
            print(f"RPC get_latest_scores failed, falling back: {e}")

        # Step 2: For any missing, fetch from server_scores table directly
        missing_ids = [sid for sid in server_ids if sid not in scores_map]
        if missing_ids:
            try:
                direct = sb.table("server_scores").select("server_id,score_overall,breakdown_json,created_at") \
                    .in_("server_id", missing_ids).order("created_at", desc=True).execute()
                for row in (direct.data or []):
                    sid = str(row.get("server_id"))
                    if sid and sid not in scores_map:
                        scores_map[sid] = {
                            "server_id": row.get("server_id"),
                            "score_overall": row.get("score_overall"),
                            "breakdown_json": row.get("breakdown_json"),
                            "created_at": row.get("created_at"),
                        }
            except Exception as e:
                print(f"Direct server_scores lookup failed: {e}")

        # Step 3: Compute on-demand for any still-missing IDs
        still_missing_ids = [sid for sid in server_ids if sid not in scores_map]
        if still_missing_ids:
            try:
                srv_resp = sb.table("servers").select("id,homepage_url,repo_url,description,tags,updated_at,metadata_json") \
                    .in_("id", still_missing_ids).execute()
                for server in (srv_resp.data or []):
                    try:
                        enriched = {
                            "homepage_url": server.get("homepage_url"),
                            "repo_url": server.get("repo_url"),
                            "description": server.get("description"),
                            "tags": server.get("tags") or [],
                        }
                        meta = server.get("metadata_json") or {}
                        if isinstance(meta, dict):
                            enriched.update(meta)
                        newscore = await score_enriched_server(enriched)
                        scores_map[str(server["id"])] = {
                            "server_id": server.get("id"),
                            "score_overall": newscore.get("overall"),
                            "breakdown_json": newscore.get("breakdown"),
                            "created_at": server.get("updated_at"),
                        }
                    except Exception as se:
                        # Leave as missing; UI/tooling can show N/A
                        print(f"On-demand scoring failed for {server.get('id')}: {se}")
            except Exception as e:
                print(f"Fetching servers for on-demand scoring failed: {e}")

        # Step 4: Attach to items
        for item in items:
            sid = str(item.get("id"))
            item["latest_score"] = scores_map.get(sid)

        return items
    
    async def _fallback_search(self, sb, query: str, limit: int, offset: int, sort: str) -> SearchResult:
        """Fallback search using direct table queries"""
        qh = sb.table("servers").select("*")
        
        if query.strip():
            # Simple text search as fallback
            qh = qh.or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
        
        # Simple sorting
        if sort == "stars":
            qh = qh.order("github_stars", desc=True)
        elif sort == "recent":
            qh = qh.order("updated_at", desc=True)
        else:
            qh = qh.order("updated_at", desc=True)
        
        result = qh.range(offset, offset + limit - 1).execute()
        items = result.data or []
        
        for item in items:
            item["name"] = _sanitize_name(item.get("name") or "")
        
        items = await self._attach_latest_scores(sb, items)
        
        # Estimate total (rough)
        total_result = sb.table("servers").select("id", count="exact").execute()
        total = total_result.count or len(items)
        
        return SearchResult(items=items, total=total, offset=offset, limit=limit)
    
    def _generate_security_recommendations(self, breakdown: Dict) -> List[str]:
        """Generate security recommendations based on score breakdown"""
        recommendations = []
        
        if breakdown.get("has_security_txt", False) is False:
            recommendations.append("Add security.txt file for vulnerability disclosure")
        
        if breakdown.get("https_score", 0) < 1.0:
            recommendations.append("Ensure HTTPS is properly configured")
        
        if breakdown.get("github_score", 0) < 0.5:
            recommendations.append("Consider hosting source code on GitHub for transparency")
        
        if breakdown.get("documentation_score", 0) < 0.5:
            recommendations.append("Improve documentation and README")
        
        return recommendations
    
    def _identify_risk_factors(self, breakdown: Dict) -> List[str]:
        """Identify risk factors from security breakdown"""
        risks = []
        
        if breakdown.get("https_score", 0) == 0:
            risks.append("No HTTPS support detected")
        
        if breakdown.get("github_score", 0) == 0:
            risks.append("No public source code repository")
        
        if breakdown.get("has_security_txt", False) is False:
            risks.append("No security contact information")
        
        return risks
    
    def _calculate_match_score(self, server: Dict, use_case: str, keywords: List[str]) -> float:
        """Calculate how well a server matches the use case"""
        score = 0.0
        text_to_check = " ".join([
            server.get("name", ""),
            server.get("description", ""),
            " ".join(server.get("tags", []))
        ]).lower()
        
        # Keyword matching
        matched_keywords = sum(1 for keyword in keywords if keyword in text_to_check)
        keyword_score = matched_keywords / max(len(keywords), 1)
        
        # Use case direct matching
        use_case_score = 1.0 if use_case.lower() in text_to_check else 0.0
        
        # Combine scores
        score = keyword_score * 0.7 + use_case_score * 0.3
        
        return min(1.0, score)
    
    def _generate_recommendation_reasoning(self, server: Dict, use_case: str, match_score: float) -> str:
        """Generate reasoning for why this server is recommended"""
        name = server.get("name", "Unknown")
        security_score = server.get("latest_score", {}).get("score_overall", 0) or 0
        github_stars = server.get("github_stars", 0)
        
        reasons = []
        
        if match_score > 0.7:
            reasons.append(f"highly relevant to {use_case}")
        elif match_score > 0.4:
            reasons.append(f"relevant to {use_case}")
        
        if security_score > 0.8:
            reasons.append("excellent security score")
        elif security_score > 0.6:
            reasons.append("good security score")
        
        if github_stars and github_stars > 50:
            reasons.append(f"popular with {github_stars} GitHub stars")
        
        if not reasons:
            reasons.append("matches your search criteria")
        
        return f"{name} is {', '.join(reasons)}."
    
    async def _run_crawl_background(self, config: CrawlConfig, crawl_id: str):
        """Run crawl in background"""
        try:
            await run_pipeline(config)
        except Exception as e:
            print(f"Crawl {crawl_id} failed: {e}")
        finally:
            self.active_crawl_id = None


# Global engine instance
_engine_instance = None

def get_engine() -> MCPGuardEngine:
    """Get shared engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MCPGuardEngine()
    return _engine_instance
