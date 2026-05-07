import importlib


def test_format_memory_empty_when_disabled(monkeypatch):
    monkeypatch.setenv("CHATBI_MEMORY_DISABLED", "1")
    import backend.memory_service as ms

    importlib.reload(ms)
    assert ms.format_memory_for_prompt(1) == ""
    monkeypatch.delenv("CHATBI_MEMORY_DISABLED", raising=False)
    importlib.reload(ms)
