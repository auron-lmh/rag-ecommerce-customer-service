## 第8页

Free plan · Upgrade

Good afternoon, zs

How can I help you today?

Claude 3.7 Sonnet ⌄

Write

Learn

Code

Life stuff

Claude's choice

# 3. Python API-MCP开发及使用

## 3.1. python环境准备

要开发一个基于 Python 的 MCP（Model Context Protocol）服务器需要python3.10版本以上并且需要安装mcp相关依赖。

下面在Windows中通过anconda安装python3.10环境，命令如下：

conda create --name python-mcp python=3.10

## 3.2. MCP Server开发

进入到创建的python环境中，安装MCP Server所需如下依赖：

#切换python环境

conda activate python-mcp

#安装依赖 mcp==1.6.0 httpx==0.28.1

pip install "mcp[cli]" httpx
