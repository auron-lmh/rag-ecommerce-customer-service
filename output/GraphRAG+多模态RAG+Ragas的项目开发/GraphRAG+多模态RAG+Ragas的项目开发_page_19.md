## 第18页

Running scriptlet: unzip-6.0-47.0.1.al8.x86_64

Verifying : unzip-6.0-47.0.1.al8.x86_64

Installed:

unzip-6.0-47.0.1.al8.x86_64

Complete!

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# yum install unzip

Last metadata expiration check: 0:31:34 ago on Fri 15 Aug 2025 06:17:46 PM CST.

Package unzip-6.0-47.0.1.al8.x86_64 is already installed.

Dependencies resolved.

Nothing to do.

Complete!

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# unzip graphrag-main.zip

Archive: graphrag-main.zip

469ee8568f2659e82aa5d3939a88e4f5be5290d9

creating: graphrag-main/

inflating: graphrag-main/.gitattributes

creating: graphrag-main/.github/

creating: graphrag-main/.github/ISSUE_TEMPLATE/

inflating: graphrag-main/.github/ISSUE_TEMPLATE/bug_report.yml

extracting: graphrag-main/.github/ISSUE_TEMPLATE/config.yml

inflating: graphrag-main/.github/ISSUE_TEMPLATE/feature_request.yml

inflation: graphrag-main/ github/ISSUE TEMPLATE/general issue vm

代码块

1

2

poetry source add aliyun https://mirrors.aliyun.com/pypi/simple/ --

priority=primary

3

4

poetry source add --priority=supplemental tsinghua

https://pypi.tuna.tsinghua.edu.cn/simple

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# poetry source add --priority=supplemental tsinghua https://pypi.tuna.tsinghua.edu.cn/sim

ple

Adding source with name tsinghua.

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# poetry source list

The requested command does not exist in the source namespace.

Did you mean one of these perhaps?

source add: Add source configuration for project.

source remove: Remove source configured for the project.

source show: Show information about sources configured for the project.

Documentation: https://python-poetry.org/docs/cli/#source

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# poetry source show

name

tsinghua

url : https://pypi.tuna.tsinghua.edu.cn/simple

priority : supplemental

查看设置

PyPI is implicitly enabled as a primary source. If you wish to disable it, or alter its priority please refer to https://python-poetry

.org/docs/repositories/#package-sources.

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]#

[root@iZ8vb5acpt0ebqsuf5mtiwZ graphrag-main]# poetry install

Jpdating dependencies

Resolving dependencies... (443.7s)

Package operations: 116 installs, 0 updates, 0 removals

Installing typing-extensions (4.14.1)

Installing six (1.17.0)

Installing python-dateutil (2.9.0.post0)

Installing pycparser (2.22)

Installing cffi (1.17.1)

Installing idna (3.10)

Installing markupsafe (3.0.2)

Installing asttokens (2.4.1)

Installing executing (2.2.0)

进入到源代码目录安装
