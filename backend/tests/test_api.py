import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://example.com")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test")

import app.main as main  # noqa: E402


class DummyClient:
    def __init__(self):
        self._data = {
            "servers": [],
            "server_scores": [],
        }

    def rpc(self, *_args, **_kwargs):
        class R:
            def execute(self_inner):
                class Resp:
                    data = []
                return Resp()
        return R()

    def table(self, name):
        self._table = name
        return self

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def offset(self, *_args, **_kwargs):
        return self

    def execute(self):
        class Resp:
            data = []
        return Resp()


@pytest.fixture(autouse=True)
def patch_supabase(monkeypatch):
    monkeypatch.setattr(main, "get_supabase_client", lambda: DummyClient())


def test_servers_empty():
    client = TestClient(main.app)
    r = client.get("/servers?limit=10")
    assert r.status_code == 200
    assert r.json() == {"items": []}

