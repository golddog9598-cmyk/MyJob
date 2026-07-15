"""
面试问答Agent - LLM客户端模块
- Embedding: Ollama nomic-embed-text
- 出题: Ollama qwen2.5:14b
- 批改: DeepSeek API
"""

import httpx
import numpy as np
import json
import re
from typing import List, Optional

try:
    from .ai_config import load_ai_config
except ImportError:  # Support direct execution from the interview directory.
    from ai_config import load_ai_config

# Ollama配置
OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:14b"


# AI配置只从环境变量读取，避免接触任何招聘平台数据库。
def _load_ai_config():
    return load_ai_config()


def get_embedding(text: str) -> List[float]:
    """获取文本的embedding向量"""
    resp = httpx.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"][0]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """计算余弦相似度"""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def llm_chat_ollama(messages: list, system_prompt: Optional[str] = None, temperature: float = 0.7) -> str:
    """调用Ollama大模型（出题用）"""
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    resp = httpx.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def llm_chat_deepseek(messages: list, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
    """调用AI API（每次从环境变量读取配置）。"""
    cfg = _load_ai_config()
    if not cfg["api_key"]:
        raise RuntimeError("AI API Key未配置，请设置 MYJOB_AI_API_KEY 环境变量")

    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    resp = httpx.post(
        f"{cfg['base_url']}/chat/completions",
        json=payload,
        headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def parse_json_from_llm(text: str) -> Optional[dict]:
    """从LLM返回文本中提取JSON"""
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None
