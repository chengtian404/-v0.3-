"""Guarded intent recognition for chat routing.

The router never converts user text to SQL. It only returns a small allowlisted
intent and subject consumed by trusted application code.
"""

import re
from dataclasses import dataclass


class UnsafeInputError(ValueError):
    pass


@dataclass(frozen=True)
class IntentDecision:
    intent: str
    subject: str = ""
    employee_id: int | None = None
    employee_name: str = ""
    prompt: str = ""


class IntentRouter:
    MAX_INPUT_LENGTH = 4000
    PROMPT_INJECTION_PATTERNS = (
        r"忽略.{0,8}(之前|以上|系统|所有).{0,8}(指令|规则|提示)",
        r"(显示|泄露|输出|告诉我).{0,8}(系统提示词|开发者消息|隐藏指令|内部规则)",
        r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions?",
        r"reveal\s+(the\s+)?(system\s+prompt|developer\s+message|hidden\s+instructions?)",
        r"jailbreak|prompt\s*injection",
    )
    SQL_PATTERNS = (
        r"```\s*sql",
        r"\bselect\s+.+\s+from\b",
        r"\b(insert\s+into|update\s+\w+\s+set|delete\s+from)\b",
        r"\b(drop|alter|truncate|create)\s+(table|database|index)\b",
        r"\b(union\s+select|pragma|attach\s+database|detach\s+database)\b",
        r"执行\s*sql|运行\s*sql|sql\s*语句",
    )
    REPORT_WORDS = ("图表", "报表", "可视化", "柱状图", "饼图", "折线图", "趋势图", "分布图")
    DATA_WORDS = ("多少", "数量", "统计", "占比", "分布", "趋势", "概览", "汇总", "数据")
    SUBJECT_WORDS = {
        "users": ("用户", "注册", "账号", "角色"),
        "warehouse": ("仓库", "入库", "深度采集", "采集数据"),
        "sources": ("瞭源", "数据源", "采集源", "规则"),
        "models": ("模型", "token", "令牌", "调用量"),
        "employees": ("数字员工", "员工类型", "员工状态"),
    }

    @classmethod
    def validate(cls, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            raise UnsafeInputError("请输入对话内容。")
        if len(cleaned) > cls.MAX_INPUT_LENGTH:
            raise UnsafeInputError("单次输入不能超过 4000 个字符。")
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL):
                raise UnsafeInputError("检测到试图覆盖系统规则的内容，本次请求已拒绝。")
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL):
                raise UnsafeInputError("系统不接收或执行 SQL。请直接描述需要查询的数据指标。")
        return cleaned

    @classmethod
    def recognize(cls, text: str, employees: list) -> IntentDecision:
        cleaned = cls.validate(text)
        mention = re.match(r"^@([^\s，,：:]+)\s*[，,：:]?\s*(.*)$", cleaned, flags=re.DOTALL)
        if mention:
            name = mention.group(1).strip()
            prompt = mention.group(2).strip() or "请介绍你可以完成的工作。"
            for employee in employees:
                if employee["name"].lower() == name.lower():
                    return IntentDecision(
                        intent="digital_employee",
                        employee_id=employee["id"],
                        employee_name=employee["name"],
                        prompt=prompt,
                    )
            return IntentDecision(
                intent="employee_not_found", employee_name=name, prompt=prompt
            )

        matched_subjects = []
        for candidate, keywords in cls.SUBJECT_WORDS.items():
            if any(keyword.lower() in cleaned.lower() for keyword in keywords):
                matched_subjects.append(candidate)
        if len(matched_subjects) > 1:
            subject = "overview"
        elif matched_subjects:
            subject = matched_subjects[0]
        elif any(word in cleaned for word in ("系统概览", "数据概览", "业务概览")):
            subject = "overview"
        else:
            subject = ""

        wants_report = any(word in cleaned for word in cls.REPORT_WORDS)
        looks_like_data = bool(subject) and (
            wants_report or any(word in cleaned for word in cls.DATA_WORDS)
        )
        if wants_report:
            return IntentDecision(intent="data_report", subject=subject or "overview", prompt=cleaned)
        if looks_like_data:
            return IntentDecision(intent="database_query", subject=subject, prompt=cleaned)
        return IntentDecision(intent="general_chat", prompt=cleaned)
