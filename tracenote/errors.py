"""友好报错：把底层技术错误翻译成用户看得懂的人话。

为什么需要这一层：如果模型 API 超时、密钥失效、网络断掉，
直接甩给用户的是一长串英文报错堆栈（Traceback），完全看不懂。
真实的软件会告诉用户"网络有点问题，请稍后再试"。
"""

from __future__ import annotations


class TraceNoteError(Exception):
    """TraceNote 自己的异常类型：带用户可读的消息。"""

    def __init__(self, user_message: str, original: Exception | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.original = original


def to_friendly_message(error: Exception) -> str:
    """把任意异常翻译成给用户的友好提示。

    判断依据是错误信息里的关键词，按从最具体到最笼统的顺序匹配。
    """
    text = str(error).lower()

    if isinstance(error, KeyError) or "api_key" in text or "apikey" in text:
        return (
            "模型服务未正确配置：没有找到 API 密钥。"
            "请确认项目根目录的 .env 文件里填了 SILICONFLOW_API_KEY。"
        )
    if "401" in text or "unauthorized" in text or "invalid api key" in text:
        return "模型服务拒绝了请求：API 密钥可能已失效或填写错误，请检查 .env 里的密钥。"
    if "insufficient" in text or "balance" in text or "quota" in text or "429" in text:
        return "模型服务额度不足或请求太频繁，请稍后再试，或检查账户余额。"
    if "timeout" in text or "timed out" in text:
        return "模型服务响应超时了。网络可能不稳定，请稍后再试。"
    if "connect" in text or "network" in text or "name resolution" in text or "getaddrinfo" in text:
        return "无法连接模型服务。请检查网络连接是否正常。"
    if "model" in text and ("not exist" in text or "not found" in text or "invalid" in text):
        return "模型名称可能配置错了。请检查 .env 里的 SILICONFLOW_MODEL 是否正确。"

    return "出了点问题，处理不了你的请求。请稍后再试；如果一直失败，请检查网络和密钥配置。"
