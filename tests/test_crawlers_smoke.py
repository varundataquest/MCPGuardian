from __future__ import annotations

from mcp_harvest.storage.io import ensure_data_files


def test_data_files_initialized():
    ensure_data_files()
    # If no exception is raised, headers were ensured
    assert True


