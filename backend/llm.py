from openai import OpenAI
from backend.config import settings

_client = None


def get_client() -> OpenAI:
    """获取 LLM 客户端（惰性初始化，根据 LLM_PROVIDER 自动切换）"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=120.0,  # 2 分钟超时
        )
    return _client


def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> tuple[str, dict]:
    """同步调用 LLM，返回 (文本内容, token用量)

    token用量格式: {"prompt": int, "completion": int, "total": int}
    """
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=model or settings.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        usage = {
            "prompt": response.usage.prompt_tokens if response.usage else 0,
            "completion": response.usage.completion_tokens if response.usage else 0,
            "total": response.usage.total_tokens if response.usage else 0,
        }
        return content, usage
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        raise


def chat_stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """流式调用 LLM，yield 文本片段"""
    client = get_client()
    stream = client.chat.completions.create(
        model=model or settings.model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
