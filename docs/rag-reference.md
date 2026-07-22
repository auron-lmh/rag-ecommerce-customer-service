# RAG 项目 PDF 解析流程（源码级参考）

来源: `D:\PythonProject1\PythonProject\RAG\dots_ocr\`

## 核心流程

```
parse_pdf(input_path)
  │
  ├─ load_images_from_pdf(input_path, dpi=200)
  │    └─ fitz.open(pdf) → 每页 fitz_doc_to_image(page, dpi) → 返回 List[PIL.Image]
  │
  ├─ 构建 tasks = [{origin_image, prompt_mode, save_dir, save_name, source, page_idx}, ...]
  │
  ├─ ThreadPool(num_thread=4)
  │    └─ pool.imap_unordered(_execute_task, tasks)
  │         │
  │         └─ _parse_single_image(**task_args)  ← 处理单页
  │              │
  │              ├─ fetch_image(origin_image, min_pixels, max_pixels)
  │              │    └─ 转RGB + smart_resize(h, w) → 确保尺寸被28整除
  │              │
  │              ├─ smart_resize(image.height, image.width) → 算目标尺寸
  │              │
  │              ├─ get_prompt(prompt_mode) → 获取prompt文本
  │              │
  │              └─ _inference_with_zhipu(image, prompt)  ← ★ PIL Image 传入, 不是base64!
  │                   │
  │                   ├─ image_to_base64(image) → RGB → JPEG(buf, quality=?) → base64
  │                   └─ client.chat.completions.create(model, messages, ...)
  │
  ├─ tqdm 实时更新 (每完成一页更新一次)
  │
  └─ results.sort(key=lambda x: x["page_no"])  → 按页码排序
```

## 关键设计

1. **图片在各函数间以 PIL Image 传递，不是 base64**
   - `_parse_single_image` 接收 PIL Image
   - `_inference_with_zhipu` 接收 PIL Image
   - 只在 API 调用前一刻 `image_to_base64()` 转 base64

2. **ThreadPool.imap_unordered + tqdm 实时进度**
   - 每完成一页立即更新进度条
   - 不是等全部完成才打印

3. **fetch_image 做图片预处理**
   - 确保尺寸被 IMAGE_FACTOR(28) 整除
   - 像素在 [MIN_PIXELS, MAX_PIXELS] 范围

4. **prompt_ocr: "Extract the text content from this image."**
   - 简洁，让模型自己判断输出格式

## API 调用模式

```python
# parser.py 的 _inference_with_zhipu
def _inference_with_zhipu(self, image, prompt):
    base64_img = image_to_base64(image)  # PIL → JPEG base64
    response = self.client.chat.completions.create(
        model=self.model_name,      # glm-4v-plus or glm-ocr
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        temperature=0.1, top_p=0.1, max_tokens=4096
    )
    return response.choices[0].message.content
```

## 我们需要的改动

1. 使用千问 API (Bailian OpenAI-compatible) 替代智谱 SDK
2. 其余流程完整照搬
