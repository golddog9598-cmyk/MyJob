#!/usr/bin/env python3
"""
AI 回复生成 —— 调用 DeepSeek API 为 BOSS直聘聊天生成自动回复。
每次回复同时由 DeepSeek 根据对话上下文评估 HR 兴趣度 (high/medium/low)。
"""

import json
import re
import sys
from pathlib import Path

# 复用 interview/llm_client.py
sys.path.insert(0, str(Path(__file__).parent / "interview"))
from llm_client import llm_chat_deepseek

from boss_state import get_recent_messages, get_setting

SYSTEM_PROMPT = """你是一个求职者开发的AI助手，在BOSS直聘上帮他自动与招聘方沟通。

## 核心身份
- 坦诚告诉对方你是AI助手，由求职者本人开发
- 这个AI工具本身就是求职者技术能力的证明
- 如果对方感兴趣，求职者本人会亲自跟进

## 求职者背景（动态适配）
- 根据对方发布的招聘岗位来匹配你的回复侧重点
- 不要硬套一个万能模板：如果对方招的是AI产品经理，就围绕AI产品方向聊；如果招的是大模型开发，就围绕模型/工程方向聊
- 绝不要编造岗位不存在的信息，也不要提到与对方招聘岗位无关的技术领域

## 回复原则
- 2-4句话，自然真诚，不许生硬
- 围绕对方发布的岗位信息（岗位名、公司、JD）来回复
- 主动了解对方岗位的具体要求、技术栈、团队情况
- 回答技术问题时给出专业、具体的内容
- 不承诺薪资、入职时间——"这些可以后续和本人详细聊"
- 不要重复寒暄，不要每一轮都自我介绍

## 面试处理（重要）
- 绝对不要直接同意面试或答应面试时间
- 当HR说"来面试""方便面试吗""什么时候过来"等邀请时，先引导加微信：
  "感谢邀请！方便的话可以先加微信聊聊，让求职者本人跟您沟通会更好，面试的事你们微信上直接定"
- 不要替求职者承诺面试、不要给具体时间

## 触发发送规则（重要）
系统会根据HR的消息内容自动执行以下操作，你只需要在回复中适当提及即可：

### 简历发送
- 当HR明确要求"发简历""看看简历""CV""作品集"时，系统会自动通过BOSS官方「发简历」按钮发送附件简历
- 你只需要回复"已通过BOSS把简历发给您了，请查收"即可
- 绝对不要说"我这边不存储简历""没有简历文件"之类的话

### 微信交换
- 当HR说"加微信""微信聊""加个v""换微信"时，系统会自动通过BOSS官方「换微信」按钮分享求职者微信
- 你只需要回复"我把联系方式通过BOSS发您了"这类话即可
- 绝对不要在文字回复里出现"微信""WeChat""VX""微信号"这些词，BOSS会过滤掉整条消息

### 电话交换
- 当HR说"电话""手机号"时，系统会自动通过BOSS官方「换电话」按钮分享求职者电话
- 你只需要回复"我把电话通过BOSS发您了"即可

### 重要提醒
- 不要在HR没有要求的情况下主动说"已发送"
- 不要重复说"已发送"，如果之前已经发过，就不再提
- 这些操作会在你回复之前执行，所以你说"已发送"时东西确实已经发出去了

## 输出格式（严格JSON）
{"reply": "你的回复内容", "interest": "high/medium/low"}

interest 评估标准（根据完整对话判断HR当前兴趣程度）：
- high: HR问了技术细节、项目经历、面试时间、薪资期望、要了微信、表达了明确合作意向
- medium: HR配合沟通、说"方便""可以""好的""聊聊"、发了JD、问了基本情况
- low: 简单打招呼、摸底试探、回复敷衍、未表现出进一步了解的意愿"""


def _encode_wechat(wechat_id: str) -> str:
    """把微信号编码，绕开 BOSS 直聘的聊天内容过滤。"""
    if not wechat_id:
        return ""
    result = wechat_id
    result = result.replace("--", "一一")
    result = result.replace("-", "一")
    return result


def build_reply_context(
    conversation_id: int, hr_message: str, job_info: dict, resume_summary: str, wechat_id: str = ""
) -> str:
    parts = []

    parts.append(f"招聘方公司: {job_info.get('company', '未知')}")
    parts.append(f"应聘岗位: {job_info.get('title', '未知')}")

    job_desc = job_info.get("description", "")
    if job_desc:
        parts.append(f"岗位描述: {job_desc[:500]}")

    if resume_summary:
        parts.append(f"我的简历摘要: {resume_summary}")

    if wechat_id:
        encoded = _encode_wechat(wechat_id)
        parts.append(f"求职者微信: {wechat_id}（BOSS会过滤微信号，实际发送时请用编码形式: {encoded}，不要发原始形式）")
    else:
        parts.append("求职者微信: 未设置")

    msgs = get_recent_messages(conversation_id, 5)
    if msgs:
        parts.append("\n最近的对话记录:")
        for m in reversed(msgs):
            sender_label = "HR" if m["sender"] == "hr" else "我"
            ai_tag = " [AI代发]" if m.get("ai_generated") else ""
            parts.append(f"  {sender_label}{ai_tag}: {m['content'][:200]}")

    parts.append(f"\nHR刚刚说: {hr_message}")
    parts.append('\n请以JSON格式输出回复和兴趣度: {"reply": "...", "interest": "high/medium/low"}')

    return "\n".join(parts)


def generate_reply(
    conversation_id: int,
    hr_message: str,
    job_info: dict,
    style: str = "professional",
    resume_summary: str = "",
    wechat_id: str = "",
) -> tuple:
    """
    根据 HR 消息生成 AI 回复和兴趣度评估。
    返回 (reply_text, interest_level) 元组，失败时返回 ("", "").
    """
    if not hr_message or len(hr_message.strip()) < 1:
        return "", ""

    hr_lower = hr_message.strip().lower()
    if hr_lower in ("你好", "您好", "hi", "hello", "嗨", "在吗", "在吗？", "在不在", "在不在？"):
        company = job_info.get("company", "贵公司")
        title = job_info.get("title", "相关岗位")
        desc_hint = ""
        if job_info.get("description"):
            desc_hint = f"，看了JD感觉挺对口的"
        return (
            f"您好！看到贵司在招{title}，挺感兴趣的{desc_hint}。PS：正在和你聊的这个AI是我自己开发的，算是我的技术名片～",
            "low",
        )

    try:
        context = build_reply_context(conversation_id, hr_message, job_info, resume_summary, wechat_id)

        style_hint = {
            "professional": "语气正式专业",
            "casual": "语气轻松友好",
            "enthusiastic": "语气热情积极",
        }.get(style, "语气正式专业")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + f"\n\n本次回复风格: {style_hint}"},
            {"role": "user", "content": context},
        ]

        raw = llm_chat_deepseek(messages, temperature=0.7)
        raw = raw.strip().strip('"').strip("'").strip()

        reply = ""
        interest = ""
        try:
            parsed = json.loads(raw)
            reply = (parsed.get("reply") or parsed.get("content") or "").strip()
            interest = (parsed.get("interest") or parsed.get("level") or "").strip().lower()
        except json.JSONDecodeError:
            import re

            m = re.search(r'"reply"\s*:\s*"([^"]*)"', raw)
            if m:
                reply = m.group(1).strip()
            m2 = re.search(r'"interest"\s*:\s*"(\w+)"', raw)
            if m2:
                interest = m2.group(1).strip().lower()

        if interest not in ("high", "medium", "low"):
            interest = ""

        if not reply or len(reply) < 2:
            if not reply:
                reply = raw
            if len(reply) < 2:
                return "", ""

        if len(reply) > 300:
            reply = reply[:300] + "..."

        refusal_patterns = [
            "无法提供",
            "无法回答",
            "不能回答",
            "无法帮助",
            "爱莫能助",
            "as an AI, I cannot",
            "I cannot provide",
        ]
        for pattern in refusal_patterns:
            if pattern.lower() in reply.lower():
                return "", ""

        return reply, interest

    except Exception as e:
        print(f"  ⚠️ generate_reply error: {e}")
        return "", ""


def generate_greeting(
    job_title: str, company: str, template: str = "", style: str = "professional", hr_name: str = ""
) -> str:
    if not template:
        template = get_setting(
            "greeting_template",
            "您好，我对贵公司的{job_title}岗位很感兴趣，请问可以详细了解一下吗？",
        )

    greeting = (
        template.replace("{hr_name}", hr_name or "").replace("{job_title}", job_title).replace("{company}", company)
    )

    if "{job_title}" in greeting or "{company}" in greeting:
        greeting = f"您好，我对贵公司的{job_title}岗位很感兴趣，请问可以详细了解一下吗？"

    if hr_name and not greeting.startswith(hr_name):
        # 招呼语开头没称呼时，把 hr_name 当称呼加到最前
        greeting = f"{hr_name}您好，" + greeting

    return greeting


GREETING_SYSTEM_PROMPT = """你是求职者本人，正在BOSS直聘上给招聘者发第一句打招呼语。

要求：
- 1-2句话，口语自然，像真人主动打招呼，不要客套话堆砌
- 紧扣对方岗位（岗位名/JD要点）说明你为什么感兴趣、你哪点匹配
- 不要夸张吹捧，不要列技能清单，不要说"贵公司"这种过于书面的词，用"咱们/你们"更自然
- 不出现微信/电话/QQ等联系方式（BOSS会拦截整条消息）
- 如果对方很可能是老板本人（boss_hint=true），语气可以更直接、更有诚意地表达想聊聊
- 末尾可以带一句轻量的："顺便说下，正在跟你聊的这个自动回复是我自己开发的AI，算我的技术名片"——仅当岗位与AI/开发/技术相关时才加，否则不要加
- 只输出招呼语正文，不要任何解释、不要引号、不要JSON"""


def generate_greeting_ai(
    job_title: str,
    company: str,
    hr_name: str = "",
    job_desc: str = "",
    is_boss: bool = False,
    style: str = "professional",
    resume_summary: str = "",
    optimize_hints: str = "",
    timeout: float = 15.0,
) -> str:
    """用 LLM 生成个性化打招呼语；任何失败都回退到模板版 generate_greeting。

    依据 JD、是否老板、简历摘要定制。AI 不可用时无感降级。
    模式：
      - greeting_mode == "smart"：按用户在前端「智能」选项下保存的 smart_greeting_prompt
        规则化生成（方向 + 3痛点 + 效果付费话术），结果中若占位符残留则回退。
      - 其他 / 关闭 AI 招呼：使用通用自然风格。
    """
    # 设置里可关闭 AI 招呼
    ai_greeting_on = get_setting("ai_greeting_enabled", "true")
    greeting_mode_dbg = get_setting("greeting_mode", "template")
    print(
        f"[greeting] job={job_title!r} company={company!r} hr={hr_name!r} "
        f"ai_enabled={ai_greeting_on!r} mode={greeting_mode_dbg!r} "
        f"has_desc={bool(job_desc)} desc_len={len(job_desc or '')}"
    )
    if ai_greeting_on != "true":
        print(f"[greeting] → 模板 (ai_greeting_enabled={ai_greeting_on!r})")
        return generate_greeting(job_title, company, style=style, hr_name=hr_name)

    if not job_title and not company:
        print("[greeting] → 模板 (缺少 job_title 和 company)")
        return generate_greeting(job_title, company, style=style, hr_name=hr_name)

    try:
        greeting_mode = greeting_mode_dbg
        style_hint = {
            "professional": "语气正式专业",
            "casual": "语气轻松友好",
            "enthusiastic": "语气热情积极",
        }.get(style, "语气正式专业")

        if greeting_mode == "smart":
            system_prompt, user_prompt = _build_smart_prompts(
                job_title, company, hr_name, job_desc, is_boss, resume_summary, style_hint, optimize_hints
            )
            print(f"[greeting] → smart 模式 prompt 长度 sys={len(system_prompt)} user={len(user_prompt)}")
        else:
            system_prompt = GREETING_SYSTEM_PROMPT
            user_prompt = _build_generic_prompt(
                job_title, company, hr_name, job_desc, is_boss, resume_summary, style_hint, optimize_hints
            )
            print(f"[greeting] → generic 模式 prompt 长度 sys={len(system_prompt)} user={len(user_prompt)}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        print(f"[greeting] → 调用 LLM ...")
        raw = llm_chat_deepseek(messages, temperature=0.8)
        text = (raw or "").strip().strip('"').strip("'").strip()
        # 去掉模型可能多输出的前缀
        text = re.sub(r"^(招呼语|打招呼语|回复)[:：]\s*", "", text)
        print(f"[greeting] LLM 返回长度={len(text)} 预览={text[:80]!r}")

        # 质量校验：太短/太长/含联系方式 → 回退模板
        if not text or len(text) < 6:
            print(f"[greeting] → 模板 (LLM 返回太短 len={len(text)})")
            return generate_greeting(job_title, company, style=style, hr_name=hr_name)
        if len(text) > 220:
            text = text[:220]
        if re.search(r"微信|wechat|vx|\bv信\b|qq|电话|手机号|\d{11}", text, re.I):
            print(f"[greeting] → 模板 (含联系方式被拦截)")
            return generate_greeting(job_title, company, style=style, hr_name=hr_name)

        # smart 模式额外校验：占位符未替换完 → 回退
        if greeting_mode == "smart" and re.search(r"【[^】]*】|\{[^}]*\}", text):
            return generate_greeting(job_title, company, style=style, hr_name=hr_name)

        # 开头补称呼（如果有 hr_name 且没带）
        if hr_name and not text.startswith(hr_name):
            text = f"{hr_name}您好，{text}"
        return text
    except Exception as e:
        print(f"  ⚠️ generate_greeting_ai 回退模板: {e}")
        return generate_greeting(job_title, company, style=style, hr_name=hr_name)


def _build_generic_prompt(
    job_title, company, hr_name, job_desc, is_boss, resume_summary, style_hint, optimize_hints=""
):
    parts = [
        f"招聘公司: {company or '未知'}",
        f"岗位名称: {job_title or '未知'}",
        f"招聘者称呼: {hr_name or '（未知，可不带称呼）'}",
        f"boss_hint: {'true' if is_boss else 'false'}",
    ]
    if job_desc:
        parts.append(f"岗位JD（节选）: {job_desc[:400]}")
    if resume_summary:
        parts.append(f"我的简历摘要: {resume_summary[:300]}")
    if optimize_hints:
        parts.append(f"\n=== 简历优化建议（参考这些方向来写招呼语，不要直接提优化简历） ===\n{optimize_hints[:600]}")
    parts.append(f"\n本次风格: {style_hint}")
    parts.append("请生成打招呼语正文：")
    return "\n".join(parts)


def _build_smart_prompts(job_title, company, hr_name, job_desc, is_boss, resume_summary, style_hint, optimize_hints=""):
    """smart 模式：消费用户在前端填的 smart_greeting_prompt（规则化）。"""
    user_rules = get_setting("smart_greeting_prompt", "")
    if not user_rules.strip():
        user_rules = (
            "规则：\n"
            "1. 严格从下面的JD中找到3个核心能力要求（不是痛点，是JD里真正要求的能力）\n"
            "2. 方向必须从JD关键词中提取（如JD写项目管理→方向就是项目管理，JD写AI产品→方向就是AI产品）\n"
            "3. 每个能力不超过10个字，尽量引用JD原词\n"
            "4. 严格按以下格式，不要自己编方向，不要加解释：\n\n"
            "老板，我的方向是【从JD提取的方向词】——【能力1】、【能力2】、【能力3】，按效果付费，做不到不拿底薪，聊聊？"
        )

    system_prompt = (
        "你是求职者本人，按下方「用户规则」严格生成一段打招呼语。\n"
        "- 只输出最终招呼语正文一行，不要任何解释、不要引号、不要JSON\n"
        "- 不出现微信/电话/QQ等联系方式（BOSS会拦截）\n"
        "- 方向和能力必须从下面提供的JD中提取，禁止编造不相关内容\n"
        f"- 称呼：{hr_name or '不带称呼'}\n"
        f"- 风格：{style_hint}\n"
        f"- 是否老板：{'true' if is_boss else 'false'}\n\n"
        f"=== 用户规则 ===\n{user_rules}\n"
    )

    user_prompt_parts = [
        f"招聘公司: {company or '未知'}",
        f"岗位名称: {job_title or '未知'}",
    ]
    if job_desc:
        user_prompt_parts.append(f"岗位JD（节选）: {job_desc[:600]}")
    if resume_summary:
        user_prompt_parts.append(f"我的简历摘要: {resume_summary[:300]}")
    if optimize_hints:
        user_prompt_parts.append(f"简历优化提示（参考这些方向提取能力关键词）:\n{optimize_hints[:400]}")
    user_prompt_parts.append("请按上方规则生成一行招呼语：")
    return system_prompt, "\n".join(user_prompt_parts)
