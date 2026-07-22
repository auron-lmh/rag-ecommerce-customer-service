## 第20页

[root@iZ8vb5acpt0ebqsuf5mtiwZ test_rag]# vi settings.yaml

### This config file contains required core defaults that must be set, along with a handful of comm

### For a full list of available settings, see https://microsoft.github.io/graphrag/config/yaml/

### LLM settings ###

### There are a number of settings to tune the threading and token limits for LLM calls - check the

models:

default_chat_model:

type: openai_chat # or azure_openai_chat

api_base: https://xiaoi.plus/v1

# api_version: 2024-05-01-preview

auth type: api_key # or azure managed identity

api_key: sk-KQk1fwtIYLA0tpExdKLWrqMhhGm9iW44XQkfqo0yWo2mnxhe

# audience: "https://cognitiveservices.azure.com/.default"

# organization: <organization_id>

model: gpt-4.1-mini

# deployment_name: <azure_model_deployment_name>

# encoding_model: cl100k_base # automatically set by tiktoken if left undefined

model_supports_json: true # recommended if this is available for your model.

concurrent_requests: 25 # max number of simultaneous LLM requests allowed

async_mode: threaded # or asyncio

retry_strategy: native

may retries: 10

[root@iZ8vb5acpt0ebqsuf5mtiwZ input]# ll

total 44

-rw-r--r-- 1 root root 10908 Aug 15 21:26 book1.txt

-rw-r--r-- 1 root root 5731 Aug 15 21:27 book2.txt

-rw-r--r-- 1 root root 10805 Aug 15 21:28 book3.txt

-rw-r--r-- 1 root root 10355 Aug 15 21:28 book4.txt

[root@iZ8vb5acpt0ebqsuf5mtiwZ input]#

测试数据，放入input目录

2025-08-15 21:30:10.0920 - INFO - graphrag.index.operations.embed_text_strategies.openai - embedding 1/ Inputs via 1/

batches. max_batch_size=16, batch_max_tokens=8191

2025-08-15 21:38:20.0133 - INFO - graphrag.logger.progress - generate embeddings progress: 1/3

2025-08-15 21:38:20.0236 - INFO - graphrag.logger.progress - generate embeddings progress: 2/3

2025-08-15 21:38:20.0320 - INFO - graphrag.logger.progress - generate embeddings progress: 3/3

[2025-08-15T13:38:20Z WARN lance::dataset::write::insert] No existing dataset at /opt/test_rag/output/lancedb/default

lance, it will be created

2025-08-15 21:38:20.0327 - INFO - graphrag.index.workflows.generate_text_embeddings - Workflow completed: generate_tex

2025-08-15 21:38:20.0327 - INFO - graphrag.api.index - Workflow generate_text_embeddings completed successfully

2025-08-15 21:38:20.0372 - INFO - graphrag.index.run.run_pipeline - Indexing pipeline complete

2025-08-15 21:38:20.0374 - INFO - graphrag.cli.index - All workflows completed successfully.

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# poetry run graphrag index --root /opt/test_rag/

代码块

1 poetry run graphrag query --root /opt/test_rag --method global --query "马云是

谁？"

2

3

poetry run graphrag query --root /opt/test_rag --method global --query "马云和淘

宝网是什么关系？"
