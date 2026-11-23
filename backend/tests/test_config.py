from backend.config import Settings


def test_defaults(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    s = Settings(_env_file=None)
    assert s.llm_provider == "github"
    assert s.llm_model == "openai/gpt-4.1-mini"
    assert s.llm_timeout_seconds == 60.0


def test_env_override(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "other-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "5")
    s = Settings(_env_file=None)
    assert s.llm_model == "other-model"
    assert s.llm_timeout_seconds == 5.0


def test_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    f = tmp_path / ".env"
    f.write_text("LLM_API_KEY=abc123\n", encoding="utf-8")
    assert Settings(_env_file=f).llm_api_key == "abc123"
