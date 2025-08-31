from app.search import simple_heuristic_nl_to_filters, nl_to_filters, build_search_sql


def test_simple_heuristic_keywords():
    f = simple_heuristic_nl_to_filters("official security stars glama")
    assert f.sort == "stars"
    assert "Official" in (f.tags_any or [])
    assert "Security" in (f.tags_any or [])
    assert "glama" in (f.registry_in or [])


def test_nl_to_filters_residual():
    f, residual = nl_to_filters("official my cool server recent")
    assert f.sort == "recent"
    assert residual == "my cool server"


def test_build_search_sql_clamps_and_sorts():
    sql, params = build_search_sql("hello", limit=1000, offset=-5)
    assert "LIMIT %(limit)s" in sql
    assert params["limit"] == 100
    assert params["offset"] == 0
    assert "ts_rank(" in sql

