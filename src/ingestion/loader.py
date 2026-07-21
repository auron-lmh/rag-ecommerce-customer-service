"""模块1 数据加载器 — 批量导入 + 进度反馈 + 示例数据生成"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from src.config import settings

from .clean_markdown import clean_markdown
from .models import DocType, ParseStatus
from .router import parse_file

logger = logging.getLogger(__name__)


def load_directory(
    dir_path: str,
    doc_type: Optional[DocType] = None,
    recursive: bool = True,
) -> dict:
    """批量加载目录下所有文档 → 解析 → 清洗

    Args:
        dir_path: 目录路径
        doc_type: 限制文档类型（不指定则自动推断）
        recursive: 是否递归子目录

    Returns:
        {
            "total_files": 50,
            "success": 45, "partial": 3, "failed": 2, "skipped": 0,
            "cleaned_chunks": 320,
            "total_api_cost": 1.23,
            "results": [...],
            "cleaned_docs": [...],
            "errors": [...],
        }
    """
    path = Path(dir_path)
    if not path.exists():
        return {"total_files": 0, "errors": [f"目录不存在: {dir_path}"]}

    # 收集文件
    pattern = "**/*" if recursive else "*"
    files = [f for f in path.glob(pattern) if f.is_file()]
    files = [
        f for f in files if not f.name.startswith(".") and not f.name.startswith("~")
    ]

    # 支持的扩展名
    supported = {
        ".pdf",
        ".docx",
        ".doc",
        ".xlsx",
        ".xls",
        ".pptx",
        ".ppt",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        ".json",
        ".txt",
        ".md",
        ".html",
        ".htm",
    }

    results = []
    errors = []
    all_cleaned = []
    total_api_cost = 0.0

    for i, file_path in enumerate(files):
        ext = file_path.suffix.lower()
        if ext not in supported:
            continue

        file_str = str(file_path)
        total = len(files)
        logger.info("[%d/%d] 解析: %s", i + 1, total, file_path.name)

        t_start = time.time()

        # 解析
        result = parse_file(file_str, doc_type=doc_type)
        results.append(result)

        if result.status == ParseStatus.SUCCESS:
            chunk_count = 0
            if result.markdown:
                # 清洗
                cleaned = clean_markdown(
                    result.markdown,
                    file_str,
                    result.document.doc_type,
                    metadata={
                        "source": result.document.source,
                        "category": result.document.category,
                        "parse_time_ms": result.parse_time_ms,
                        "api_cost": result.api_cost_estimate,
                    },
                )
                all_cleaned.extend(cleaned)
                chunk_count = len(cleaned)

            total_api_cost += result.api_cost_estimate
            elapsed = (time.time() - t_start) * 1000
            logger.info(
                "[%d/%d] ✅ %d块 | ¥%.4f | %.0fms",
                i + 1,
                total,
                chunk_count,
                result.api_cost_estimate,
                elapsed,
            )

        elif result.status == ParseStatus.PARTIAL:
            if result.markdown:
                cleaned = clean_markdown(
                    result.markdown, file_str, result.document.doc_type
                )
                all_cleaned.extend(cleaned)
            total_api_cost += result.api_cost_estimate
            logger.warning(
                "[%d/%d] ⚠️ 部分成功 | 警告: %s",
                i + 1,
                total,
                result.warnings,
            )

        else:
            errors.extend(result.errors)
            logger.error(
                "[%d/%d] ❌ %s",
                i + 1,
                total,
                result.errors[0] if result.errors else "未知错误",
            )

    # 汇总
    return {
        "total_files": len(files),
        "success": sum(1 for r in results if r.status == ParseStatus.SUCCESS),
        "partial": sum(1 for r in results if r.status == ParseStatus.PARTIAL),
        "failed": sum(1 for r in results if r.status == ParseStatus.FAILED),
        "skipped": sum(1 for r in results if r.status == ParseStatus.SKIPPED),
        "cleaned_chunks": len(all_cleaned),
        "total_api_cost": round(total_api_cost, 4),
        "results": results,
        "cleaned_docs": all_cleaned,
        "errors": errors,
    }


def load_faq_json(json_path: str) -> dict:
    """加载单个FAQ JSON文件"""
    result = parse_file(json_path, doc_type=DocType.FAQ_JSON)

    if result.status == ParseStatus.SUCCESS and result.markdown:
        cleaned = clean_markdown(result.markdown, json_path, DocType.FAQ_JSON)
        return {
            "total_files": 1,
            "success": 1,
            "failed": 0,
            "skipped": 0,
            "cleaned_chunks": len(cleaned),
            "total_api_cost": 0,
            "results": [result],
            "cleaned_docs": cleaned,
            "errors": [],
        }
    else:
        return {
            "total_files": 1,
            "success": 0,
            "failed": 1,
            "skipped": 0,
            "cleaned_chunks": 0,
            "total_api_cost": 0,
            "results": [result],
            "cleaned_docs": [],
            "errors": result.errors,
        }


# ═══════════════════════════════════════
# 示例数据生成
# ═══════════════════════════════════════


def create_sample_faq(output_path: str = None) -> str:
    """生成电商客服示例FAQ JSON"""
    if output_path is None:
        output_path = str(settings.faq_dir / "sample_faq.json")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    samples = [
        {
            "question": "如何申请退货？",
            "answer": "您可以在订单详情页点击'申请退货'，选择退货原因并提交。审核通过后，系统会安排上门取件。退货有效期为签收后7天内。",
            "keywords": ["退货", "退款", "申请"],
        },
        {
            "question": "退货的运费谁出？",
            "answer": "商品质量问题导致的退货，运费由平台承担。非质量问题的退货（如不喜欢、买错），运费由买家承担。",
            "keywords": ["退货", "运费"],
        },
        {
            "question": "多久能收到退款？",
            "answer": "商品退回仓库验收后，退款将在1-3个工作日内原路返回。如超过3个工作日未收到，请联系客服查询。",
            "keywords": ["退款", "到账", "时间"],
        },
        {
            "question": "怎么修改收货地址？",
            "answer": "订单未发货时可在订单详情页直接修改地址。已发货的订单请联系客服尝试拦截或改派。",
            "keywords": ["修改", "地址", "收货"],
        },
        {
            "question": "商品保修多久？",
            "answer": "电子产品保修期为1年，服装鞋帽支持7天无理由退货。具体保修政策请查看商品详情页。",
            "keywords": ["保修", "期限"],
        },
        {
            "question": "发货时间是多久？",
            "answer": "一般下单后24小时内发货，预售商品以页面标注的发货时间为准，节假日可能会有延迟。",
            "keywords": ["发货", "时间"],
        },
        {
            "question": "支持哪些支付方式？",
            "answer": "支持微信支付、支付宝、银行卡、花呗分期、白条等主流支付方式。",
            "keywords": ["支付", "微信", "支付宝"],
        },
        {
            "question": "如何联系人工客服？",
            "answer": "APP内'我的-客服中心'联系在线客服，或拨打客服热线400-xxx-xxxx（9:00-21:00）。",
            "keywords": ["人工客服", "电话"],
        },
        {
            "question": "收到的商品有质量问题怎么办？",
            "answer": "请拍照保留证据，在订单详情页选择'质量问题'申请售后。审核通过后可换货或退款，平台承担运费。",
            "keywords": ["质量问题", "瑕疵", "换货"],
        },
        {
            "question": "可以货到付款吗？",
            "answer": "部分商品支持货到付款，以提交订单页面显示为准。生鲜、定制类商品不支持。",
            "keywords": ["货到付款", "支付"],
        },
        {
            "question": "优惠券怎么使用？",
            "answer": "下单时在结算页面选择可用优惠券即可。满减券和折扣券不能叠加使用，系统会自动选最优方案。",
            "keywords": ["优惠券", "满减", "折扣"],
        },
        {
            "question": "订单取消了优惠券会退回吗？",
            "answer": "取消订单后已使用的优惠券会自动退回到您的账户，可在'我的-优惠券'中查看。优惠券在有效期内可继续使用。",
            "keywords": ["取消", "优惠券", "退回"],
        },
        {
            "question": "配送范围是哪里？",
            "answer": "目前覆盖全国大部分城市及县城。具体是否支持配送请以结算页面显示的配送方式为准。偏远地区可能需要额外时效。",
            "keywords": ["配送", "范围", "快递"],
        },
        {
            "question": "可以指定快递公司吗？",
            "answer": "目前系统根据收货地址自动分配最优快递公司，暂不支持手动指定。如有特殊需求请联系客服。",
            "keywords": ["快递", "指定"],
        },
        {
            "question": "怎么查看物流信息？",
            "answer": "在订单详情页点击'查看物流'即可实时追踪包裹位置。您也会收到发货和签收的短信/App推送通知。",
            "keywords": ["物流", "快递", "追踪"],
        },
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    return output_path


def create_sample_product_csv(output_path: str = None) -> str:
    """生成示例商品数据CSV"""
    import csv

    if output_path is None:
        output_path = str(settings.processed_data_dir / "products.csv")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    products = [
        [
            "商品ID",
            "名称",
            "类别",
            "品牌",
            "价格",
            "库存",
            "颜色",
            "材质",
            "尺寸",
            "重量",
            "保修月数",
            "上架时间",
        ],
        [
            "P001",
            "男士纯棉短袖T恤",
            "服装",
            "优衣库",
            "79.00",
            "500",
            "白色/黑色/灰色",
            "100%棉",
            "M/L/XL/XXL",
            "0.2kg",
            "3",
            "2026-06-01",
        ],
        [
            "P002",
            "女士防晒外套UPF50+",
            "服装",
            "蕉下",
            "199.00",
            "320",
            "浅粉/天蓝/白色",
            "锦纶",
            "S/M/L/XL",
            "0.15kg",
            "6",
            "2026-06-15",
        ],
        [
            "P003",
            "无线蓝牙耳机Pro",
            "数码",
            "漫步者",
            "299.00",
            "150",
            "黑色/白色",
            "ABS+金属",
            "均码",
            "0.05kg",
            "12",
            "2026-05-20",
        ],
        [
            "P004",
            "便携充电宝20000mAh",
            "数码",
            "小米",
            "129.00",
            "800",
            "白色/黑色",
            "锂聚合物",
            "140×68×28mm",
            "0.38kg",
            "18",
            "2026-07-01",
        ],
        [
            "P005",
            "智能手表运动版",
            "数码",
            "华为",
            "899.00",
            "200",
            "黑色/银色",
            "不锈钢+硅胶",
            "46mm表盘",
            "0.06kg",
            "12",
            "2026-05-10",
        ],
        [
            "P006",
            "不锈钢保温杯500ml",
            "日用品",
            "富光",
            "59.00",
            "600",
            "白色/黑色/蓝色",
            "304不锈钢",
            "高240mm",
            "0.3kg",
            "6",
            "2026-06-20",
        ],
        [
            "P007",
            "乳胶枕护颈款",
            "家居",
            "网易严选",
            "149.00",
            "400",
            "白色",
            "天然乳胶",
            "60×40×12cm",
            "1.2kg",
            "12",
            "2026-07-05",
        ],
        [
            "P008",
            "有机核桃仁500g",
            "食品",
            "三只松鼠",
            "39.90",
            "1000",
            "原味",
            "核桃",
            "500g/袋",
            "0.5kg",
            "6",
            "2026-07-10",
        ],
        [
            "P009",
            "速干运动毛巾",
            "日用品",
            "迪卡侬",
            "29.90",
            "700",
            "蓝色/灰色/橙色",
            "超细纤维",
            "80×40cm",
            "0.1kg",
            "3",
            "2026-06-25",
        ],
        [
            "P010",
            "折叠雨伞自动开合",
            "日用品",
            "天堂",
            "49.00",
            "450",
            "藏青/酒红/黑色",
            "碰击布+钢骨",
            "折叠后28cm",
            "0.35kg",
            "3",
            "2026-07-08",
        ],
        [
            "P011",
            "空气炸锅4.5L",
            "家电",
            "美的",
            "349.00",
            "120",
            "黑色",
            "不粘涂层+塑料",
            "35×28×32cm",
            "4.5kg",
            "12",
            "2026-06-01",
        ],
        [
            "P012",
            "即食鸡胸肉10袋",
            "食品",
            "薄荷健康",
            "69.00",
            "300",
            "原味/黑椒",
            "鸡胸肉",
            "100g×10袋",
            "1.0kg",
            "3",
            "2026-07-12",
        ],
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(products)

    return output_path
