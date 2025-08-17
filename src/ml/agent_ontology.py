from __future__ import annotations

CAPABILITY_SYNONYMS = {
    "email": ["email","gmail","smtp","imap","send mail","inbox","labels"],
    "files": ["drive","google drive","dropbox","box","storage","upload","download","files"],
    "calendar": ["calendar","events","scheduling","meeting","availability","reminder"],
    "chat": ["slack","discord","chat","webhook","channels","dm","message"],
    "docs": ["notion","confluence","docs","wiki","notes","pages"],
    "crm": ["salesforce","hubspot","crm","leads","contacts","pipeline"],
    "database": ["postgres","mysql","sql","query","db","sqlite","redshift"],
    "issues": ["jira","github issues","tickets","bug","kanban","epic"],
    "vector": ["vector store","embeddings","semantic search","faiss","opensearch","weaviate"],
    "cloud": ["aws","gcp","azure","s3","bucket","lambda","iam","k8s","kubernetes"],
    "webscraping": ["webscrapes","webscraping","scraping","crawler","crawling","scrape","scraper","web crawler","data extraction","html parsing","beautifulsoup","selenium","requests","puppeteer","playwright"],
}

CAPABILITY_HINTS = {
    "email": {"keywords":["gmail","smtp"], "category":"email"},
    "files": {"keywords":["drive","box","dropbox","s3"], "category":"files"},
    "calendar":{"keywords":["calendar","events"], "category":"calendar"},
    "chat":   {"keywords":["slack","discord"], "category":"chat"},
    "docs":   {"keywords":["notion","confluence"], "category":"docs"},
    "crm":    {"keywords":["salesforce","hubspot"], "category":"crm"},
    "database":{"keywords":["postgres","mysql","sql"], "category":"database"},
    "issues": {"keywords":["jira","issues"], "category":"issues"},
    "vector": {"keywords":["vector","embedding"], "category":"vector"},
    "cloud":  {"keywords":["aws","gcp","azure","s3"], "category":"cloud"},
    "webscraping": {"keywords":["webscraping","scraping","crawler"], "category":"webscraping"},
}

ALL_CAPABILITIES = list(CAPABILITY_SYNONYMS.keys())

