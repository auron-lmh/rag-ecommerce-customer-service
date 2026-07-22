"""用户聊天界面 — Gradio ChatBot

面向终端用户的客服聊天界面，支持：
- 流式输出（逐字显示）
- 多轮对话
- 显示意图分类和人工介入状态
- 显示检索来源

启动: python -m src.admin.chat_ui
"""

import logging
from pathlib import Path

import gradio as gr
import requests

logger = logging.getLogger(__name__)

# API 地址
API_BASE_URL = "http://localhost:8000"


def chat_with_bot(message: str, history: list) -> tuple:
    """与客服机器人对话

    Args:
        message: 用户输入
        history: 对话历史 [(user, assistant), ...]

    Returns:
        (更新后的历史, 状态信息)
    """
    if not message.strip():
        return history, "请输入问题"

    try:
        # 调用 API
        resp = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "query": message,
                "top_k": 5,
                "use_reranker": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # 提取结果
        reply = data.get("reply", "抱歉，暂时无法回答。")
        intent = data.get("intent", "")
        confidence = data.get("confidence", 0)
        needs_human = data.get("needs_human", False)
        human_reason = data.get("human_reason", "")
        results = data.get("results", [])

        # 构建状态信息
        status_parts = []
        if intent:
            status_parts.append(f"意图: {intent} ({confidence:.0%})")
        if needs_human:
            status_parts.append(f"⚠️ 需要人工介入: {human_reason}")
        if results:
            status_parts.append(f"检索到 {len(results)} 条结果")
            # 显示来源
            sources = set(
                r.get("source_file", "") for r in results if r.get("source_file")
            )
            if sources:
                status_parts.append(f"来源: {', '.join(sources)}")

        status = " | ".join(status_parts) if status_parts else "正常回复"

        # 更新历史
        history.append((message, reply))

        return history, status

    except Exception as e:
        logger.error("聊天请求失败: %s", e)
        history.append((message, f"系统错误: {str(e)}"))
        return history, f"错误: {str(e)}"


def clear_history():
    """清空对话历史"""
    return [], "对话已清空"


def create_chat_ui() -> gr.Blocks:
    """创建聊天界面"""

    with gr.Blocks(
        title="电商智能客服",
        theme=gr.themes.Soft(),
        css="""
        .status-bar {
            background: #f0f0f0;
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }
        """,
    ) as app:
        gr.Markdown("""
            # 🤖 电商智能客服

            欢迎使用电商智能客服系统！请输入您的问题，我会尽力为您解答。

            **支持的功能：**
            - 商品咨询、退货退款、物流查询
            - 智能意图识别 + 多级检索降级
            - 幻觉检测 + 自纠正
            - 人工介入（退款/投诉/敏感话题）
            """)

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=400,
                    show_label=False,
                    bubble_full_width=False,
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="输入问题",
                        placeholder="请输入您的问题...",
                        show_label=False,
                        scale=4,
                        container=False,
                    )
                    submit_btn = gr.Button("发送", variant="primary", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("清空对话", variant="secondary")
                    retry_btn = gr.Button("重新回答", variant="secondary")

            with gr.Column(scale=1):
                status_display = gr.Textbox(
                    label="状态",
                    value="等待输入...",
                    interactive=False,
                    lines=3,
                )

                gr.Markdown("""
                    ### 📋 快捷问题

                    - 怎么退货？
                    - 退款多久到账？
                    - 快递到哪了？
                    - 这个商品怎么样？
                    - 我要投诉
                    """)

                gr.Markdown("""
                    ### ℹ️ 系统说明

                    - 意图分类：6类意图自动识别
                    - 检索策略：Hybrid Search + Reranker
                    - 降级策略：4级降级 + 联网搜索
                    - 质量保证：幻觉检测 + 自纠正
                    """)

        # 事件绑定
        def respond(message, history):
            return chat_with_bot(message, history)

        msg_input.submit(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, status_display],
        ).then(
            lambda: "",
            outputs=[msg_input],
        )

        submit_btn.click(
            respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, status_display],
        ).then(
            lambda: "",
            outputs=[msg_input],
        )

        clear_btn.click(
            clear_history,
            outputs=[chatbot, status_display],
        )

        def retry_last(history):
            if history:
                last_message = history[-1][0]
                history = history[:-1]
                return chat_with_bot(last_message, history)
            return history, "没有可重试的消息"

        retry_btn.click(
            retry_last,
            inputs=[chatbot],
            outputs=[chatbot, status_display],
        )

    return app


def main():
    """启动聊天界面"""
    app = create_chat_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
