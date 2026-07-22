## 第24页

error: Failed dependencies:

cypher-shell >= 5.0 is needed by neo4j-5.26.8-1.noarch

cypher-shell < 6.0 is needed by neo4j-5.26.8-1.noarch

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm -rf cypher-shell-5.26.8-1.noarch.rpm

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm --install cypher-shell-5.26.8-1.noarch.rpm neo4j-5.26.8-1.noarch.rpm

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# cd /usr/local/

aegis/ bin/ cloudmonitor/ etc/ games/

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm -qa neo4j-5.26.8-1

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm -qk neo4j-5.26.8-1

rpm: -qk: unknown option

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# rpm -ql neo4j-5.26.8-1

/etc/bash_completion.d/neo4j-admin_completion

/etc/bash_completion.d/neo4j_completion

/etc/default/neo4j

/etc/neo4j

/etc/neo4j/neo4j-admin.conf

/etc/neo4j/neo4j.conf

/etc/neo4j/server-logs.xml

/etc/neo4j/user-logs.xml

/lib/systemd/system/neo4j.service

/usr/bin/neo4j

/usr/bin/neo4j-admin

/usr/share/doc/neo4j/LICENSE.txt

查看安装后的路径

安装

配置存储在/etc/neo4j/neo4j.conf中。在首次启动数据库之前，建议使用 neo4j-admin 的 set-

initial-password 命令定义本机用户 neo4j 的密码。

如果未使用此方法显式设置密码，则它将设置为默认密码 neo4j 。在这种情况下，您将在首次登录

时被提示更改默认密码。

代码块

1 neo4j-admin dbs set-initial-password <password> [--require-password-change]

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# neo4j-admin dbs set-initial-password 1qaz3edc

Changed password for user 'neo4j'. IMPORTANT: this change will only take effect if performed before the database is started for t

rst time.

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# ^C

系统服务使用 systemctl 命令进行控制。它接受许多命令

代码块

1 systemctl {start|stop|restart|status|edit} neo4j

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# systemctl start neo4j

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# netstat -ntpl

Active Internet connections (only servers)

Proto Recv-Q Send-Q Local Address

Foreign Address

State

PID/Program name

tcp

0

0 0.0.0.0:111

0.0.0.0:

0

0 0.0.0.0:22

LISTEN

1/systemd

0

0 :::111

0.0.0.0:

LISTEN

1989/sshd

0

0 127.0.0.1:7474

:::*

LISTEN

1/systemd

0

0 :::22

:::*

LISTEN

1989/sshd

0

0 127.0.0.1:7687

:::*

LISTEN

15007/java

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]#
