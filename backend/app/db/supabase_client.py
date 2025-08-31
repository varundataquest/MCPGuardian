from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from supabase import Client, create_client


class SupabaseNotConfigured(Exception):
    pass


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SupabaseNotConfigured("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


