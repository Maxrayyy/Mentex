import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # ── 当前使用的 Provider ──
    # 可选: "agnes" | "deepseek"
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "agnes")
    )

    # ── Agnes AI ──
    agens_api_key: str = field(
        default_factory=lambda: os.getenv("AGENS_API_KEY", "")
    )
    agens_base_url: str = field(
        default_factory=lambda: os.getenv("AGENS_BASE_URL", "https://apihub.agnes-ai.com/v1")
    )
    agens_model: str = field(
        default_factory=lambda: os.getenv("AGENS_MODEL", "deepseek-v4-flash")
    )

    # ── DeepSeek ──
    deepseek_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    deepseek_model: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )

    # ── 动态属性：根据 llm_provider 返回对应的 key/url/model ──
    @property
    def api_key(self) -> str:
        if self.llm_provider == "deepseek":
            return self.deepseek_api_key
        return self.agens_api_key

    @property
    def base_url(self) -> str:
        if self.llm_provider == "deepseek":
            return self.deepseek_base_url
        return self.agens_base_url

    @property
    def model(self) -> str:
        if self.llm_provider == "deepseek":
            return self.deepseek_model
        return self.agens_model

    # ── 服务端口 ──
    api_host: str = field(
        default_factory=lambda: os.getenv("API_HOST", "0.0.0.0")
    )
    api_port: int = field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )
    streamlit_port: int = field(
        default_factory=lambda: int(os.getenv("STREAMLIT_PORT", "8501"))
    )


settings = Settings()
