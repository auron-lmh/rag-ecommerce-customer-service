"""管理员界面 — 人工介入管理 + 系统监控

功能：
- 查看待处理的人工介入请求
- 处理人工介入（标记已处理/转交/备注）
- 系统监控（查询量、成本、幻觉率）
- 知识库管理

启动: python -m src.admin.admin_ui
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import gradio as gr
import requests

logger = logging.getLogger(__name__)

# API 地址
API_BASE_URL = "http://localhost:8000"

# 人工介入数据库
HITL_DB = Path(__file__).parent.parent.parent / "data" / "hitl_requests.db"


def init_hitl_db():
    """初始化人工介入数据库"""
    HITL_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(HITL_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hitl_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT DEFAULT '',
                user_query TEXT NOT NULL,
                intent TEXT DEFAULT '',
                confidence REAL DEFAULT 0,
                human_reason TEXT DEFAULT '',
                priority TEXT DEFAULT 'low',
                status TEXT DEFAULT 'pending',
                assigned_to TEXT DEFAULT '',
                resolution TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                resolved_at TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.commit()


def get_pending_requests() -> list[dict]:
    """获取待处理的人工介入请求"""
    with sqlite3.connect(HITL_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT * FROM hitl_requests
               WHERE status = 'pending'
               ORDER BY
                 CASE priority
                   WHEN 'high' THEN 1
                   WHEN 'medium' THEN 2
                   WHEN 'low' THEN 3
                 END,
                 created_at DESC""").fetchall()
        return [dict(r) for r in rows]


def get_all_requests(limit: int = 50) -> list[dict]:
    """获取所有请求"""
    with sqlite3.connect(HITL_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM hitl_requests ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_hitl_request(
    session_id: str,
    user_query: str,
    intent: str,
    confidence: float,
    human_reason: str,
    priority: str,
):
    """添加人工介入请求"""
    with sqlite3.connect(HITL_DB) as conn:
        conn.execute(
            """INSERT INTO hitl_requests
               (session_id, user_query, intent, confidence, human_reason, priority, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                user_query,
                intent,
                confidence,
                human_reason,
                priority,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()


def resolve_request(request_id: int, resolution: str, assigned_to: str = ""):
    """处理人工介入请求"""
    with sqlite3.connect(HITL_DB) as conn:
        conn.execute(
            """UPDATE hitl_requests
               SET status = 'resolved',
                   resolution = ?,
                   assigned_to = ?,
                   resolved_at = ?
               WHERE id = ?""",
            (resolution, assigned_to, datetime.now().isoformat(), request_id),
        )
        conn.commit()


def get_system_stats() -> dict:
    """获取系统统计"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/stats/daily", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def format_requests_table(requests: list[dict]) -> str:
    """格式化请求表格"""
    if not requests:
        return "暂无待处理请求"

    lines = [
        "| ID | 优先级 | 用户问题 | 意图 | 原因 | 状态 | 创建时间 |",
        "|---|--------|----------|------|------|------|----------|",
    ]

    for r in requests:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            r["priority"], "⚪"
        )
        lines.append(
            f"| {r['id']} | {priority_icon} {r['priority']} | {r['user_query'][:30]}... | "
            f"{r['intent']} | {r['human_reason'][:20]}... | {r['status']} | "
            f"{r['created_at'][:16]} |"
        )

    return "\n".join(lines)


def create_admin_ui() -> gr.Blocks:
    """创建管理员界面"""

    init_hitl_db()

    with gr.Blocks(
        title="管理员控制台",
        theme=gr.themes.Soft(),
    ) as app:
        gr.Markdown("# 🎛️ 管理员控制台")

        with gr.Tabs():
            # Tab 1: 人工介入管理
            with gr.Tab("📋 人工介入管理"):
                gr.Markdown("### 待处理请求")

                refresh_btn = gr.Button("🔄 刷新", variant="secondary")
                requests_display = gr.Markdown(
                    value=format_requests_table(get_pending_requests())
                )

                gr.Markdown("### 处理请求")

                with gr.Row():
                    request_id_input = gr.Number(
                        label="请求 ID",
                        precision=0,
                    )
                    resolution_input = gr.Textbox(
                        label="处理结果",
                        placeholder="输入处理结果...",
                    )
                    assigned_input = gr.Textbox(
                        label="处理人",
                        placeholder="客服姓名",
                    )

                resolve_btn = gr.Button("✅ 标记已处理", variant="primary")
                resolve_status = gr.Textbox(label="状态", interactive=False)

                def refresh_requests():
                    return format_requests_table(get_pending_requests())

                def resolve(request_id, resolution, assigned):
                    if not request_id:
                        return "请输入请求 ID"
                    if not resolution:
                        return "请输入处理结果"
                    resolve_request(int(request_id), resolution, assigned)
                    return f"✅ 请求 {request_id} 已处理"

                refresh_btn.click(
                    refresh_requests,
                    outputs=[requests_display],
                )

                resolve_btn.click(
                    resolve,
                    inputs=[request_id_input, resolution_input, assigned_input],
                    outputs=[resolve_status],
                ).then(
                    refresh_requests,
                    outputs=[requests_display],
                )

            # Tab 2: 系统监控
            with gr.Tab("📊 系统监控"):
                gr.Markdown("### 系统状态")

                stats_refresh_btn = gr.Button("🔄 刷新统计", variant="secondary")
                stats_display = gr.JSON(label="系统统计")

                gr.Markdown("### 快捷操作")

                with gr.Row():
                    health_btn = gr.Button("检查健康状态", variant="secondary")
                    cache_btn = gr.Button("清空缓存", variant="secondary")

                action_result = gr.Textbox(label="操作结果", interactive=False)

                def refresh_stats():
                    return get_system_stats()

                def check_health():
                    try:
                        resp = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
                        resp.raise_for_status()
                        return json.dumps(resp.json(), indent=2, ensure_ascii=False)
                    except Exception as e:
                        return f"错误: {str(e)}"

                def clear_cache():
                    try:
                        resp = requests.delete(f"{API_BASE_URL}/api/cache", timeout=5)
                        resp.raise_for_status()
                        return "✅ 缓存已清空"
                    except Exception as e:
                        return f"错误: {str(e)}"

                stats_refresh_btn.click(
                    refresh_stats,
                    outputs=[stats_display],
                )

                health_btn.click(
                    check_health,
                    outputs=[action_result],
                )

                cache_btn.click(
                    clear_cache,
                    outputs=[action_result],
                )

            # Tab 3: 历史记录
            with gr.Tab("📜 历史记录"):
                gr.Markdown("### 最近处理记录")

                history_refresh_btn = gr.Button("🔄 刷新", variant="secondary")
                history_display = gr.Markdown()

                def refresh_history():
                    requests = get_all_requests(limit=20)
                    if not requests:
                        return "暂无记录"

                    lines = [
                        "| ID | 问题 | 意图 | 优先级 | 状态 | 处理人 | 处理结果 |",
                        "|---|------|------|--------|------|--------|----------|",
                    ]

                    for r in requests:
                        status_icon = "✅" if r["status"] == "resolved" else "⏳"
                        lines.append(
                            f"| {r['id']} | {r['user_query'][:20]}... | {r['intent']} | "
                            f"{r['priority']} | {status_icon} {r['status']} | "
                            f"{r['assigned_to'] or '-'} | {r['resolution'][:20] or '-'}... |"
                        )

                    return "\n".join(lines)

                history_refresh_btn.click(
                    refresh_history,
                    outputs=[history_display],
                )

    return app


def main():
    """启动管理员界面"""
    app = create_admin_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
