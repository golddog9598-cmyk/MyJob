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
import os
from typing import List, Optional

# Ollama配置
OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:14b"

# DeepSeek配置（从.env文件读取，避免shell变量截断）
def _load_deepseek_key() -> str:
    """从 ~/.hermes/.env 中读取完整的 DEEPSEEK_API_KEY"""
    # 优先从环境变量
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key and "..." not in env_key and env_key.count("*") < 5:
        return env_key
    # 从 .env 文件读取
    env_paths = [
        os.path.expanduser("~/.hermes/.env"),
        os.path.join(os.path.dirname(__file__), ".env"),
    ]
    for path in env_paths:
        if os.path.exists(path):
            with open(path) as f:
                m = re.search(r'DEEPSEEK_API_KEY=(\S+)', f.read())
                if m:
                    key = m.group(1).strip().strip("'\"")
                    if key and "..." not in key:
                        return key
    return env_key or ""

DEEPSEEK_API_KEY = _load_deepseek_key()
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


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


def llm_chat_ollama(messages: list, system_prompt: Optional[str] = None,
                    temperature: float = 0.7) -> str:
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


def llm_chat_deepseek(messages: list, system_prompt: Optional[str] = None,
                      temperature: float = 0.3) -> str:
    """调用DeepSeek API（批改用）"""
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    resp = httpx.post(
        f"{DEEPSEEK_BASE}/v1/chat/completions",
        json=payload,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def parse_json_from_llm(text: str) -> Optional[dict]:
    """从LLM返回文本中提取JSON"""
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None
