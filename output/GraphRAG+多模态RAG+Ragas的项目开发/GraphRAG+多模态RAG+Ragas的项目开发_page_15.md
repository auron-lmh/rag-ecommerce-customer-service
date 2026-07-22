## 第14页

一、pip 安装 GraphRAG 的硬性要求

表格

类别

官方 / 社区实测要求

Python

3.10 - 3.12

≥ 23.3

系统

Win10+/macOS 12+/Ubuntu 20.04+

磁盘

预留 ≥ 3 GB 空间

网络

能访问 https://pypi.org、https://openai.com

LLM

任选其一: ① OpenAI GPT-4o/4o-mini② Azure OpenAI③ 本地 vLLM / Ollama④ 其他 OpenAI-API 兼容端点

内存

16 GB RAM 起步; 8 GB 也能跑, 但速度明显下降

Last login. Sat Aug 10 17:15:10 2023 11:08 1/3.0.00.7

[root@iZ8vb5acpt0ebqsuf5mtiwZ ~]# python3.12 -m venv graphrag_env

[root@iZ8vb5acpt0ebqsuf5mtiwZ ~]# ls

[root@iZ8vb5acpt0ebqsuf5mtiwZ ~]# cd graphrag_env/

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag_env]# ls

bin include lib lib64 pyvenv.cfg

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag_env]# cd bin/

[root@iZ8vb5acpt0ebqsuf5mtiwZ bin]# ls

activate activate.csh activate.fish Activate.ps1

[root@iZ8vb5acpt0ebqsuf5mtiwZ bin]# ll

pip pip3 pip3.12 python python3 python3.12

-rw-r--r-- 1 root root 2040 Aug 16 18:07 activate

-rw-r--r-- 1 root root 928 Aug 16 18:07 activate.csh

-rw-r--r-- 1 root root 2207 Aug 16 18:07 activate.fish

-rw-r--r-- 1 root root 9033 Aug 16 18:07 Activate.ps1

-rwxr-xr-x 1 root root 238 Aug 16 18:07 pip

-rwxr-xr-x 1 root root 238 Aug 16 18:07 pip3

-rwxr-xr-x 1 root root 238 Aug 16 18:07 pip3.12

[root@iZ8vb5acpt0ebqsuf5mtiwZ bin]# source ./activate

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ bin]# pip install graphrag

Looking in indexes: http://mirrors.cloud.aliyuncs.com/pypi/simple/

Collecting graphrag

370.4/370.4 kB 2.4 MB/s eta 0:00:00

Collecting environs>=11.0.0 (from graphrag)

Downloading http://mirrors.cloud.aliyuncs.com/pypi/packages/ad/e3/98d8567eb438c7856a4dcedd97a8a7c6707120a5ada6

ons-14.3.0-py3-none-any.whl (16 kB)

Collecting azure-search-documents>=11.5.2 (from graphrag)

Downloading http://mirrors.cloud.aliyuncs.com/pypi/packages/4b/f5/0f6b52567cbb33f1efba13060514ed7088a86de84d74

_search_documents-11.5.3-py3-none-any.whl (298 kB)

298.8/298.8 kB 3.0 MB/s eta 0:00:00

Collecting lancedb>=0.17.0 (from graphrag)

Downloading http://mirrors.cloud.aliyuncs.com/pypi/packages/9a/b9/3e0e25b7c6dcd4f6b0e977cb886965070ca05d799481

db-0.24.3-cp39-abi3-manylinux_2_28_x86_64.whl (35.0 MB)

创建工作目录并放入测试数据来构建索引

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ~]# ls

graphrag_env

mkdir -p ./ragtest/input

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ~]# cp -a /opt/test_rag/input/* .txt ./ragtest/input/

(graphrag_env) [root@iZ8vb5acpt0ebqsuf5mtiwZ ~]# graphrag init --root ./ragtest/
