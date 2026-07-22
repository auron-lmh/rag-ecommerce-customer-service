## 第25页

[root@iZ8vb5acpt0ebqsuf5mtiwZ download]# systemctl status neo4j

neo4j.service - Neo4j Graph Database

Loaded: loaded (/usr/lib/systemd/system/neo4j.service; disabled; vendor preset: disabled)

Active: active (running) since Sat 2025-08-09 19:23:12 CST; 1min 43s ago

Main PID: 14976 (java)

Tasks: 78 (limit: 95926)

Memory: 582.3M

CGroup: /system.slice/neo4j.service

14976 /usr/bin/java -Xmx128m -classpath /usr/share/neo4j/lib/*:/usr/share/neo4j/etc:/usr/share/neo4j/repo/* -Dapp.name=

15007 /usr/lib/jvm/jdk-17.0.16-oracle-x64/bin/java -cp /var/lib/neo4j/plugins/*/etc/neo4j/*:/usr/share/neo4j/lib/* -XX

Aug 09 19:23:16 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:16.739+0000 INFO This instance is ServerId{79a2ab97} (79a2ab9

Aug 09 19:23:18 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:18.008+0000 INFO =========== Neo4j 5.26.8 ===========

Aug 09 19:23:20 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:20.279+0000 INFO Anonymus Usage Data is being sent to Neo4j

Aug 09 19:23:20 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:20.325+0000 INFO Bolt enabled on localhost:7687.

Aug 09 19:23:21 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:21.099+0000 INFO HTTP enabled on localhost:7474.

Aug 09 19:23:21 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:21.103+0000 INFO Remote interface available at http://localhost:

Aug 09 19:23:21 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:21.103+0000 INFO id: 592505C0F85909673FA89AFFF6D42FA32E1C113:

Aug 09 19:23:21 iZ8vb5acpt0ebqsuf5mtiwZ neo4j[15007]: 2025-08-09 11:23:21.104+0000 INFO name: system

lines 1-20/20 (END)

要使 Neo4j 在系统启动时自动启动，请运行以下命令

代码块
1 systemctl enable neo4j

不安全 | 39.100.64.14:7474/browser/

Database access not available. Please use :server connect to establish connection. There's a graph waiting for you.

s :server connect
Connect to Neo4j

Database access might require
an authenticated connection

Connect URL
neo4j// 39.100.64.14:7687

Database - leave empty for default

Authentication type
Username / Password

Username
Password

Connect
Connect

默认neo4j
之前修改的密码
