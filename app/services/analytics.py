"""Allowlisted database analytics used by the user-side question answering tool."""

from app.models.db import get_connection


class AnalyticsService:
    @staticmethod
    def answer(subject: str, prompt: str, include_report: bool = False) -> dict:
        handlers = {
            "users": AnalyticsService._users,
            "warehouse": AnalyticsService._warehouse,
            "sources": AnalyticsService._sources,
            "models": AnalyticsService._models,
            "employees": AnalyticsService._employees,
            "overview": AnalyticsService._overview,
        }
        handler = handlers.get(subject, AnalyticsService._overview)
        return handler(prompt, include_report)

    @staticmethod
    def _users(prompt: str, include_report: bool) -> dict:
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            active = conn.execute("SELECT COUNT(*) AS count FROM users WHERE status=1").fetchone()["count"]
            disabled = total - active
            roles = conn.execute("""
                SELECT COALESCE(r.name, '未分配') AS name, COUNT(u.id) AS count
                FROM users u LEFT JOIN roles r ON r.id=u.role_id
                GROUP BY u.role_id ORDER BY count DESC
            """).fetchall()
            trend = conn.execute("""
                SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count
                FROM users GROUP BY day ORDER BY day DESC LIMIT 7
            """).fetchall()
        role_text = "、".join(f"{row['name']} {row['count']} 人" for row in roles) or "暂无角色数据"
        content = f"当前共有 {total} 名用户，其中启用 {active} 名、禁用 {disabled} 名。角色分布：{role_text}。"
        report = None
        if include_report:
            if "趋势" in prompt or "折线" in prompt:
                points = list(reversed(trend))
                report = AnalyticsService._axis_report(
                    "近 7 个有注册记录日期的用户增长", "line",
                    [row["day"] for row in points], [row["count"] for row in points], "注册人数",
                )
            elif "角色" in prompt:
                report = AnalyticsService._pie_report(
                    "用户角色分布", [{"name": row["name"], "value": row["count"]} for row in roles]
                )
            else:
                report = AnalyticsService._pie_report(
                    "用户状态分布",
                    [{"name": "启用", "value": active}, {"name": "禁用", "value": disabled}],
                )
        return {"content": content, "report": report}

    @staticmethod
    def _warehouse(prompt: str, include_report: bool) -> dict:
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM warehouse_items").fetchone()["count"]
            deep = conn.execute(
                "SELECT COUNT(*) AS count FROM warehouse_items WHERE deep_collected=1"
            ).fetchone()["count"]
            sources = conn.execute("""
                SELECT CASE WHEN source_name='' THEN '未知来源' ELSE source_name END AS name,
                       COUNT(*) AS count
                FROM warehouse_items GROUP BY source_name ORDER BY count DESC LIMIT 8
            """).fetchall()
            trend = conn.execute("""
                SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count
                FROM warehouse_items GROUP BY day ORDER BY day DESC LIMIT 7
            """).fetchall()
        pending = total - deep
        source_text = "、".join(f"{row['name']} {row['count']} 条" for row in sources) or "暂无来源数据"
        content = f"数据仓库共有 {total} 条数据，已深度采集 {deep} 条，待深度采集 {pending} 条。主要来源：{source_text}。"
        report = None
        if include_report:
            if "趋势" in prompt or "折线" in prompt:
                points = list(reversed(trend))
                report = AnalyticsService._axis_report(
                    "近 7 个有入库记录日期的数据趋势", "line",
                    [row["day"] for row in points], [row["count"] for row in points], "入库数量",
                )
            elif "来源" in prompt or "分布" in prompt:
                report = AnalyticsService._axis_report(
                    "仓库数据来源分布", "bar",
                    [row["name"] for row in sources], [row["count"] for row in sources], "数据量",
                )
            else:
                report = AnalyticsService._pie_report(
                    "深度采集状态",
                    [{"name": "已深度采集", "value": deep}, {"name": "待深度采集", "value": pending}],
                )
        return {"content": content, "report": report}

    @staticmethod
    def _sources(_prompt: str, include_report: bool) -> dict:
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM data_sources").fetchone()["count"]
            enabled = conn.execute(
                "SELECT COUNT(*) AS count FROM data_sources WHERE enabled=1"
            ).fetchone()["count"]
            tested = conn.execute("""
                SELECT last_test_status AS name, COUNT(*) AS count
                FROM data_sources GROUP BY last_test_status
            """).fetchall()
        content = f"当前配置 {total} 个瞭源，其中启用 {enabled} 个、停用 {total - enabled} 个。"
        report = AnalyticsService._pie_report(
            "瞭源启用状态",
            [{"name": "启用", "value": enabled}, {"name": "停用", "value": total - enabled}],
        ) if include_report else None
        return {"content": content, "report": report, "details": [dict(row) for row in tested]}

    @staticmethod
    def _models(prompt: str, include_report: bool) -> dict:
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM ai_models").fetchone()["count"]
            enabled = conn.execute("SELECT COUNT(*) AS count FROM ai_models WHERE enabled=1").fetchone()["count"]
            types = conn.execute("""
                SELECT model_type AS name, COUNT(*) AS count
                FROM ai_models GROUP BY model_type ORDER BY count DESC
            """).fetchall()
            usage = conn.execute("""
                SELECT m.name, COALESCE(SUM(u.total_tokens), 0) AS count
                FROM ai_models m LEFT JOIN model_usage u ON u.model_id=m.id
                GROUP BY m.id ORDER BY count DESC LIMIT 8
            """).fetchall()
        total_tokens = sum(row["count"] for row in usage)
        content = f"模型引擎配置 {total} 个模型，其中启用 {enabled} 个；累计记录令牌 {total_tokens}。"
        report = None
        if include_report:
            rows = usage if ("token" in prompt.lower() or "令牌" in prompt or "调用" in prompt) else types
            title = "模型令牌使用量" if rows is usage else "模型类型分布"
            report = AnalyticsService._axis_report(
                title, "bar", [row["name"] for row in rows], [row["count"] for row in rows], "数量",
            )
        return {"content": content, "report": report}

    @staticmethod
    def _employees(_prompt: str, include_report: bool) -> dict:
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS count FROM digital_employees").fetchone()["count"]
            enabled = conn.execute(
                "SELECT COUNT(*) AS count FROM digital_employees WHERE enabled=1"
            ).fetchone()["count"]
            types = conn.execute("""
                SELECT emp_type AS name, COUNT(*) AS count
                FROM digital_employees GROUP BY emp_type ORDER BY count DESC
            """).fetchall()
        type_text = "、".join(
            f"{'LLM 型' if row['name'] == 'llm' else 'API 型'} {row['count']} 个" for row in types
        ) or "暂无类型数据"
        content = f"当前配置 {total} 个数字员工，启用 {enabled} 个、停用 {total - enabled} 个。类型分布：{type_text}。"
        report = AnalyticsService._pie_report(
            "数字员工类型分布",
            [{"name": "LLM 型" if row["name"] == "llm" else "API 型", "value": row["count"]} for row in types],
        ) if include_report else None
        return {"content": content, "report": report}

    @staticmethod
    def _overview(_prompt: str, include_report: bool) -> dict:
        with get_connection() as conn:
            counts = {
                "用户": conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
                "仓库数据": conn.execute("SELECT COUNT(*) c FROM warehouse_items").fetchone()["c"],
                "瞭源": conn.execute("SELECT COUNT(*) c FROM data_sources").fetchone()["c"],
                "模型": conn.execute("SELECT COUNT(*) c FROM ai_models").fetchone()["c"],
                "数字员工": conn.execute("SELECT COUNT(*) c FROM digital_employees").fetchone()["c"],
            }
        content = "系统概览：" + "、".join(f"{name} {value}" for name, value in counts.items()) + "。"
        report = AnalyticsService._axis_report(
            "系统数据概览", "bar", list(counts.keys()), list(counts.values()), "数量"
        ) if include_report else None
        return {"content": content, "report": report}

    @staticmethod
    def _axis_report(title: str, chart_type: str, labels: list, values: list, series_name: str) -> dict:
        return {
            "title": title,
            "type": chart_type,
            "labels": labels,
            "series": [{"name": series_name, "data": values}],
        }

    @staticmethod
    def _pie_report(title: str, data: list) -> dict:
        return {"title": title, "type": "pie", "data": data}
