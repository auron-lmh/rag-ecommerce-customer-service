## 第15页

2025-08-16 18:26:46.0057 - INFO - graphrag.cli.initialize - Initializing project at /root/

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ~]# cd ./ragtest/

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ragtest]# ls

input prompts settings.yaml

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ragtest]# vi settings.yaml

发送文本到当前Xshell窗口的全部会话

models:

default_chat_model:

type: openai chat # or azure openai chat

api_base: https://xiaoi.plus/v1

# api_version. 2024-05-01-preview

auth_type: api key # or azure managed identity

api_key: sk-KQkl o0yWo2mxhe

# audience: "https://cognitiveservices.azure.com/.default"

# organization: <organization_id>

model: gpt-4.1-mini

# deployment_name: <azure_model_deployment_name>

# encoding_model: cli100k_base # automatically set by tiktoken if left undefined

model_supports_json: true # recommended if this is available for your model.

concurrent_requests: 25 # max number of simultaneous LLM requests allowed

async_mode: threaded # or asyncio

retry_strategy: native

max_retries: 10

tokens_per_minute: auto

requests_per_minute: auto

# set to null to disable rate limiting

# set to null to disable rate limiting

default_embedding_model:

type: openai_embedding # or azure_openai_embedding

api_base: https://xiaoi.plus/v1

# api_version: 2024-05-01-preview

auth_type: api key # or azure managed identity

graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ragtest]# cd ..

025-08-16 18:32:00.0747 - INFO - graphrag.cli.index - Logging enabled at /root/ragtest/logs/logs.txt

025-08-16 18:32:24.0377 - INFO - graphrag.index.validate_config - LLM Config Params Validated

025-08-16 18:32:27.0299 - INFO - graphrag.index.validate_config - Embedding LLM Config Params Validated

025-08-16 18:32:27.0302 - INFO - graphrag.cli.index - Starting pipeline run. False

025-08-16 18:32:27.0302 - INFO - graphrag.cli.index - Using default configuration: {

"root_dir": "/root/ragtest",

"models": {

"default_chat_model": {

"api_key": "=== REDACTED ===",

"auth_type": "api_key",

"type": "openai_chat",

"model": "gpt-4.1-mini",

"encoding_model": "o200k_base",

"api_base": "https://xiaoi.plus/v1",

"api_version": null,

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ragtest]# graphrag query --root /root/ragtest/ --method global --query "马云是谁?"

2025-08-16 18:48:05.0854 - INFO - graphrag.storage.file_pipeline_storage - Creating file storage at /root/ragtest/output

2025-08-16 18:48:05.0855 - INFO - graphrag.utils.storage - reading table from storage: entities.parquet

2025-08-16 18:48:05.0864 - INFO - graphrag.utils.storage - reading table from storage: communities.parquet

2025-08-16 18:48:05.0868 - INFO - graphrag.utils.storage - reading table from storage: community_reports.parquet

# 马云简介

马云（Jack Ma）是中国著名企业家，阿里巴巴集团的联合创始人和前董事长。他于1999年创立了阿里巴巴集团，带领公司迅速成长为全球领先的电子商

务集团，旗下拥有淘宝、天猫和支付宝等重要子公司。作为中国互联网和电子商务行业的标志性人物，马云在推动中国数字经济发展方面具有举足轻重的

地位，对全球电子商务格局也产生了深远影响[Data: Reports (3, 6, 7, 8, 13, +more)]。

# 创业历程与贡献
