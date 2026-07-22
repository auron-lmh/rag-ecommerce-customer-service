## 第17页

# GraphRAG

## 主页

## 索引

## 提示调优

## 查询

## 配置

## 命令行界面 (CLI)

## 附加功能

## 主页

## 欢迎

## 快速入门

## 开发指南

## 开发指南

## 要求

名称 安装 目的

Python 3.10-3.12 下载 该库基于 Python。

Poetry 说明 Poetry 用于 Python 代码库中的包管理和 virtualenv 管理

## 快速入门

inflating: graphrag-main/unified-search-app/pyproject.toml

inflating: graphrag-main/unified-search-app/uv.lock

inflating: graphrag-main/uv.lock

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# ls

cypher-shell-5.26.8-1.noarch.rpm graphrag-main.zip

jdk-17.0.16_linux-x64_bin.rpm

neo4j-5.26.8-1.noarch.rpm Python-3.12.4.tgz

Python-3.12.4

先安装Python-3.12.4

graphrag-main

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# cd graphrag-main/

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# ls

breaking-changes.md

CONTRIBUTING.md

CHANGELOG.md

CODE_OF_CONDUCT.md

cspell.config.yaml

DEVELOPING.md

CODEOWNERS

dictionary.txt

LICENSE

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# pip install poetry

WARNING: Disabling truststore since ssl support is missing

Looking in indexes: http://mirrors.cloud.aliyuncs.com/pypi/simple/

Collecting poetry

Downloading http://mirrors.cloud.aliyuncs.com/pypi/packages/6d/37/578fe593a07daa5e4417a7965d46093a255ebd7fbb797df6959c0f37

y-2.1.4-py3-none-any.whl (278 kB)

Collecting build<2.0.0.>=1.2.1 (from poetrv)

## 代码块

1 # 源码安装Python的解释器

2 ./configure --prefix=/usr/python-3.12 --with-openssl=/usr --enable-

optimizations

3 make -j$(nproc)

4 make altinstall

## 5

## # 安装pip

7 python3.12 -m ensurepip --upgrade

8 wget https://bootstrap.pypa.io/get-pip.py

## 9

sudo python3.12 get-pip.py

## 10

11 # 创建软连接（可以不要）

12 ln -s /usr/python-3.12/bin/python3.12 /usr/python-3.12/bin/python

standard-0.23.0

WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager,

ssibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. U

the --root-user-action option if you know what you are doing and want to suppress this warning.

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# ls /usr/python-3.12/bin/

安装成功了

2to3-3.12

dul-upload-pack

get-pip.py

keyring

pip

pkginfo

pyproject-build

python3.12-config

doesitcache

dulwich

httpx
