-- Servers and scores schema with FTS support

CREATE TABLE IF NOT EXISTS servers (
  id BIGSERIAL PRIMARY KEY,
  registry TEXT NOT NULL,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  homepage_url TEXT NOT NULL,
  repo_url TEXT,
  description TEXT,
  tags TEXT[] DEFAULT '{}',
  metadata_json JSONB,
  github_stars INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS servers_homepage_url_key ON servers (homepage_url);
CREATE INDEX IF NOT EXISTS servers_registry_idx ON servers (registry);
CREATE INDEX IF NOT EXISTS servers_slug_idx ON servers (slug);
CREATE INDEX IF NOT EXISTS servers_tags_gin_idx ON servers USING GIN (tags);

-- FTS
ALTER TABLE servers ADD COLUMN IF NOT EXISTS search_tsv tsvector;

CREATE INDEX IF NOT EXISTS servers_search_tsv_idx ON servers USING GIN (search_tsv);

CREATE OR REPLACE FUNCTION servers_search_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.search_tsv := 
    setweight(to_tsvector('english', coalesce(NEW.name,'')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.description,'')), 'B') ||
    setweight(to_tsvector('english', array_to_string(coalesce(NEW.tags, '{}'), ' ')), 'C');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_servers_search_tsv ON servers;
CREATE TRIGGER trg_servers_search_tsv BEFORE INSERT OR UPDATE ON servers
FOR EACH ROW EXECUTE FUNCTION servers_search_tsv_update();


-- Scores
CREATE TABLE IF NOT EXISTS server_scores (
  id BIGSERIAL PRIMARY KEY,
  server_id BIGINT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  score_overall NUMERIC NOT NULL,
  breakdown_json JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS server_scores_server_id_created_at_idx ON server_scores (server_id, created_at DESC);

-- FTS search RPCs  
CREATE OR REPLACE FUNCTION public.search_servers(
  query TEXT,
  registry_in TEXT[] DEFAULT NULL,
  tags_any TEXT[] DEFAULT NULL,
  limit_count INT DEFAULT 20,
  offset_count INT DEFAULT 0,
  sort_key TEXT DEFAULT 'rank'
) RETURNS SETOF servers
LANGUAGE sql STABLE AS $$
  WITH q AS (
    SELECT CASE WHEN query IS NULL OR btrim(query) = ''
                THEN NULL
                ELSE websearch_to_tsquery('english', query) END AS tsq
  ),
  latest_scores AS (
    SELECT DISTINCT ON (server_id) server_id, score_overall
    FROM server_scores 
    ORDER BY server_id, created_at DESC
  )
  SELECT s.*
  FROM servers s, q
  LEFT JOIN latest_scores ls ON s.id = ls.server_id
  WHERE (q.tsq IS NULL OR s.search_tsv @@ q.tsq)
    AND (registry_in IS NULL OR s.registry = ANY(registry_in))
    AND (tags_any IS NULL OR s.tags && tags_any)
  ORDER BY
    CASE WHEN sort_key = 'score' THEN ls.score_overall END DESC NULLS LAST,
    CASE WHEN sort_key = 'stars' THEN s.github_stars END DESC NULLS LAST,
    CASE WHEN sort_key = 'recent' THEN s.updated_at END DESC NULLS LAST,
    CASE WHEN sort_key = 'rank' AND q.tsq IS NOT NULL THEN ts_rank(s.search_tsv, q.tsq) END DESC NULLS LAST,
    s.updated_at DESC NULLS LAST
  LIMIT limit_count OFFSET offset_count;
$$;

CREATE OR REPLACE FUNCTION public.search_servers_count(
  query TEXT,
  registry_in TEXT[] DEFAULT NULL,
  tags_any TEXT[] DEFAULT NULL
) RETURNS BIGINT
LANGUAGE sql STABLE AS $$
  WITH q AS (
    SELECT CASE WHEN query IS NULL OR btrim(query) = ''
                THEN NULL
                ELSE websearch_to_tsquery('english', query) END AS tsq
  ),
  latest_scores AS (
    SELECT DISTINCT ON (server_id) server_id, score_overall
    FROM server_scores 
    ORDER BY server_id, created_at DESC
  )
  SELECT count(*)::bigint
  FROM servers s, q
  LEFT JOIN latest_scores ls ON s.id = ls.server_id
  WHERE (q.tsq IS NULL OR s.search_tsv @@ q.tsq)
    AND (registry_in IS NULL OR s.registry = ANY(registry_in))
    AND (tags_any IS NULL OR s.tags && tags_any);
$$;


