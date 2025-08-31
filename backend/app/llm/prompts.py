from __future__ import annotations


def build_metadata_normalizer_prompt(summary_text: str) -> str:
    return (
        "You are a strict JSON generator. Normalize MCP server metadata from the provided summary.\n"
        "Respond with JSON only, matching this schema exactly:\n"
        "{\n  \"description\": string | null,\n  \"tags\": string[] | null,\n  \"tools\": {name:string,description?:string}[] | null,\n  \"prompts\": {name:string,description?:string}[] | null,\n  \"resources\": {name:string,description?:string,uri?:string}[] | null\n}\n"
        "No prose, no backticks.\n\n"
        f"Summary:\n{summary_text}\n"
    )


def build_risk_flags_prompt(summary_text: str) -> str:
    return (
        "You are a strict JSON generator. Extract advisory runtime risk signals from the summary.\n"
        "Respond with JSON only, matching this schema exactly:\n"
        "{\n  \"exec_shell\": boolean,\n  \"filesystem_unscoped\": boolean,\n  \"network_unscoped\": boolean,\n  \"has_auth\": boolean,\n  \"has_rate_limits\": boolean,\n  \"notes\": string | null\n}\n"
        "No prose, no backticks.\n\n"
        f"Summary:\n{summary_text}\n"
    )


def build_reputation_prompt(publisher: str, host: str) -> str:
    # Host is retained as context but we no longer ask for a hosting score
    return (
        "You are a strict JSON generator. Estimate company reputation using only widely known public knowledge.\n"
        "Respond with JSON only, matching this schema exactly:\n"
        "{\n  \"company_reputation\": number,\n  \"rationale\": string\n}\n"
        "Scale is 0-100 (higher is better). If unknown, use 50 and explain. No prose, no backticks.\n\n"
        f"Publisher: {publisher or 'unknown'}\n"
        f"Host (context only): {host or 'unknown'}\n"
    )


def build_enrichment_prompt(summary_text: str) -> str:
    return (
        "You are a strict JSON generator. Combine metadata normalization and risk flags in one response.\n"
        "Respond with JSON only, matching this schema exactly:\n"
        "{\n"
        "  \"description\": string | null,\n"
        "  \"tags\": string[] | null,\n"
        "  \"tools\": {name:string,description?:string}[] | null,\n"
        "  \"prompts\": {name:string,description?:string}[] | null,\n"
        "  \"resources\": {name:string,description?:string,uri?:string}[] | null,\n"
        "  \"risk_flags\": {\n"
        "    \"exec_shell\": boolean,\n"
        "    \"filesystem_unscoped\": boolean,\n"
        "    \"network_unscoped\": boolean,\n"
        "    \"has_auth\": boolean,\n"
        "    \"has_rate_limits\": boolean,\n"
        "    \"notes\": string | null\n"
        "  } | null\n"
        "}\n"
        "No prose, no backticks.\n\n"
        f"Summary:\n{summary_text}\n"
    )


def build_batch_enrichment_prompt(indexed_summaries: list[tuple[int, str]]) -> str:
    rows = "\n".join([f"- index={i}: {s}" for i, s in indexed_summaries])
    return (
        "You are a strict JSON generator. For each input item, normalize MCP server metadata and risk flags.\n"
        "Respond with JSON only, matching this schema exactly:\n"
        "{\n  \"items\": [\n"
        "    { \"index\": number, \"description\": string|null, \"tags\": string[]|null, \"tools\": {name:string,description?:string}[]|null, \"prompts\": {name:string,description?:string}[]|null, \"resources\": {name:string,description?:string,uri?:string}[]|null,\n"
        "      \"risk_flags\": { \"exec_shell\": boolean, \"filesystem_unscoped\": boolean, \"network_unscoped\": boolean, \"has_auth\": boolean, \"has_rate_limits\": boolean, \"notes\": string|null }|null }\n"
        "  ]\n}\n"
        "No prose, no backticks. Keep order by index.\n\n"
        f"Inputs (index: summary):\n{rows}\n"
    )


def build_batch_reputation_prompt(publishers: list[str]) -> str:
    rows = "\n".join([f"- publisher: {p or 'unknown'}" for p in publishers])
    return (
        "You are a strict JSON generator. For each publisher, estimate company reputation using widely known public knowledge only.\n"
        "Respond with JSON only, matching this schema exactly:\n"
        "{\n  \"items\": [ { \"publisher\": string, \"company_reputation\": number, \"rationale\": string } ]\n}\n"
        "Scale is 0-100. If unknown, use 50 and explain. No prose, no backticks.\n\n"
        f"Publishers:\n{rows}\n"
    )
