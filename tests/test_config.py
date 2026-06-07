from backend.config import Settings


def test_settings_agnes_provider(monkeypatch):
    """LLM_PROVIDER=agnes 时，动态属性返回 Agnes 的配置"""
    monkeypatch.setenv("LLM_PROVIDER", "agnes")
    monkeypatch.setenv("AGENS_API_KEY", "sk-agnes-test")
    monkeypatch.setenv("AGENS_BASE_URL", "https://apihub.agnes-ai.com/v1")
    monkeypatch.setenv("AGENS_MODEL", "agnes-2.0-flash")

    settings = Settings()
    assert settings.api_key == "sk-agnes-test"
    assert settings.base_url == "https://apihub.agnes-ai.com/v1"
    assert settings.model == "agnes-2.0-flash"


def test_settings_deepseek_provider(monkeypatch):
    """LLM_PROVIDER=deepseek 时，动态属性返回 DeepSeek 的配置"""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-ds-test")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

    settings = Settings()
    assert settings.api_key == "sk-ds-test"
    assert settings.base_url == "https://api.deepseek.com"
    assert settings.model == "deepseek-v4-flash"


def test_settings_defaults(monkeypatch):
    """默认 provider 是 agnes"""
    monkeypatch.setenv("AGENS_API_KEY", "sk-agnes-test")
    settings = Settings()
    assert settings.llm_provider == "agnes"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
