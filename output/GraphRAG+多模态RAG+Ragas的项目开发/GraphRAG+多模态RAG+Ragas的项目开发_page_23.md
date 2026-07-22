## 第22页

1 云服务器

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# ll

total 177592

-rw-r--r-- 1 root root 181847735 Aug 9 17:48 jdk-17.0.16_linux-x64_bin.rpm

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm -ivh jdk-17.0.16_linux-x64_bin.rpm

warning: jdk-17.0.16_linux-x64_bin.rpm: Header V3 RSA/SHA256 Signature, key ID 8d8b756f: NOKEY

Verifying...

###

Preparing...

[100%]

[100%]

Updating / installing...

1: jdk-17-2000:17.0.16-12

###

[100%]

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]#

安装命令

1 云服务器 [0]

2 云服务器 [1]

-rw-r--r-- 1 root root 181847735 Aug 9 17:48 jdk-17.0.16_linux-x64_bin.rpm

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm -ivh jdk-17.0.16_linux-x64_bin.rpm

warning: jdk-17.0.16_linux-x64_bin.rpm: Header V3 RSA/SHA256 Signature, key ID 8d8b756f: NOKEY

Verifying...

###

Preparing...

Updating / installing...

###

1: jdk-17-2000:17.0.16-12

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# vi ~/.bashrc

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# vi ~/.bashrc

.bashrc

# User specific aliases and functions

alias rm='rm -i'

alias cp='cp -i'

alias mv='mv -i'

# Source global definitions

if [ -f /etc/bashrc ]; then

/etc/bashrc

fi

export JAVA_HOME=/usr/java/jdk-17

export PATH=$PATH:$JAVA_HOME/bin

配置环境变量

1 云服务器 [0]

2 云服务器 [1]

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# ll

total 177592

-rw-r--r-- 1 root root 181847735 Aug 9 17:48 jdk-17.0.16_linux-x64_bin.rpm

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm -ivh jdk-17.0.16_linux-x64_bin.rpm

warning: jdk-17.0.16_linux-x64_bin.rpm: Header V3 RSA/SHA256 Signature, key ID 8d8b756f: NOKEY

Verifying...

###

Preparing...

Updating / installing...

###

1: jdk-17-2000:17.0.16-12

###

[100%]

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# vi ~/.bashrc

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# vi ~/.bashrc

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# soure ~/.bashrc

-bash: soure: command not found

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# source ~/.bash

-bash: /root/.bash: No such file or directory

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# source ~/.bashrc

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]#

让环境变量配置生效
