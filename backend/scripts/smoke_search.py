from app.search import nl_to_filters, build_search_sql


def main() -> None:
    q = "official security stars glama postgres"
    filters, residual = nl_to_filters(q)
    sql, params = build_search_sql(residual or 'postgres', filters, limit=10, offset=0)
    print(sql)
    print(params)


if __name__ == "__main__":
    main()


