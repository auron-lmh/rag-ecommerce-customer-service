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

# API 地址 (Docker 容器内使用服务名)
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://rag-api:8000")

# 模块33: 管理端用 admin 账号登录 API（在 api_auth 首次导入前设好 env 默认）
os.environ.setdefault("API_USERNAME", "admin")
os.environ.setdefault("API_PASSWORD", "admin123")

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS human_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
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


def get_human_conversation(session_id: str) -> list[dict]:
    """获取某会话的人工对话记录"""
    with sqlite3.connect(HITL_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM human_messages WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def send_human_reply(session_id: str, content: str) -> None:
    """客服回复客户（保存到人工对话，客户端轮询推送）"""
    with sqlite3.connect(HITL_DB) as conn:
        conn.execute(
            "INSERT INTO human_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "assistant", content, datetime.now().isoformat()),
        )
        conn.commit()


def format_conversation(messages: list[dict]) -> str:
    """格式化对话记录"""
    if not messages:
        return "暂无对话"
    lines = []
    for m in messages:
        who = "👤 客户" if m["role"] == "user" else "🎧 客服"
        lines.append(f"**{who}**: {m['content']}")
    return "\n\n".join(lines)


def get_system_stats() -> dict:
    """获取系统统计"""
    try:
        from src.admin.api_auth import auth_headers

        resp = requests.get(
            f"{API_BASE_URL}/api/stats/daily",
            headers=auth_headers(),
            timeout=5,
        )
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

            # Tab 2: 人工对话（转人工后同窗口与客户对话）
            with gr.Tab("💬 人工对话"):
                gr.Markdown("### 与客户实时对话（转人工后同一窗口）")
                gr.Markdown(
                    "客户转人工后，消息会进入这里。客服回复后，客户侧自动收到。"
                )

                conv_refresh_btn = gr.Button("🔄 刷新会话列表", variant="secondary")
                conv_session = gr.Dropdown(
                    label="选择会话", choices=[], interactive=True
                )
                conv_state = gr.State("")
                conv_display = gr.Markdown("选择会话查看对话")

                with gr.Row():
                    conv_reply = gr.Textbox(
                        label="客服回复", placeholder="输入回复内容...", scale=4
                    )
                    conv_send = gr.Button("📤 发送给客户", variant="primary", scale=1)
                conv_status = gr.Textbox(label="状态", interactive=False)

                def load_sessions():
                    reqs = get_pending_requests()
                    choices = [
                        (f"#{r['id']} {r['user_query'][:20]}", r["session_id"])
                        for r in reqs
                    ]
                    val = choices[0][1] if choices else None
                    return gr.Dropdown(choices=choices, value=val, interactive=True)

                def show_conv(session_id):
                    conv_state.value = session_id or ""
                    if not session_id:
                        return "选择会话查看对话"
                    return format_conversation(get_human_conversation(session_id))

                def send_reply(content):
                    sid = conv_state.value
                    if not sid:
                        return "请先选择会话", gr.update(), ""
                    if not content.strip():
                        return "请输入回复内容", gr.update(), content
                    send_human_reply(sid, content.strip())
                    return (
                        f"✅ 已发送给客户: {content.strip()[:30]}",
                        format_conversation(get_human_conversation(sid)),
                        "",  # 清空输入框
                    )

                def refresh_conv():
                    """自动刷新当前会话的对话（客服界面动态显示新消息）"""
                    sid = conv_state.value
                    if not sid:
                        return gr.update()
                    return format_conversation(get_human_conversation(sid))

                conv_refresh_btn.click(load_sessions, outputs=[conv_session])
                conv_session.change(
                    show_conv, inputs=[conv_session], outputs=[conv_display]
                )
                conv_send.click(
                    send_reply,
                    inputs=[conv_reply],
                    outputs=[conv_status, conv_display, conv_reply],
                )

                # 自动刷新: 每 5 秒更新当前会话的对话（新客户消息自动出现）
                conv_timer = gr.Timer(5)
                conv_timer.tick(refresh_conv, outputs=[conv_display])

            # Tab 3: 系统监控
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
                        from src.admin.api_auth import auth_headers

                        resp = requests.get(
                            f"{API_BASE_URL}/api/health",
                            headers=auth_headers(),
                            timeout=5,
                        )
                        resp.raise_for_status()
                        return json.dumps(resp.json(), indent=2, ensure_ascii=False)
                    except Exception as e:
                        return f"错误: {str(e)}"

                def clear_cache():
                    try:
                        from src.admin.api_auth import auth_headers

                        resp = requests.delete(
                            f"{API_BASE_URL}/api/cache",
                            headers=auth_headers(),
                            timeout=5,
                        )
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
