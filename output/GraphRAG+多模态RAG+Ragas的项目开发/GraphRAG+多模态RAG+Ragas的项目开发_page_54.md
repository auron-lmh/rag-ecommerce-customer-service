## 第52页

已安装 grpcio-tools。可以使用 pip3 install grpcio-tools 命令安装。

代码块
1 python3 -m pip install pymilvus==2.6.0

一、数据库操作

在 Milvus 中，数据库是组织和管理数据的逻辑单元。为了提高数据安全性并实现多租户，你可以创建

多个数据库，为不同的应用程序或租户从逻辑上隔离数据。例如，创建一个数据库用于存储用户 A 的

数据，另一个数据库用于存储用户 B 的数据。

a、连接数据库

代码块
1 from pymilvus import MilvusClient

2

3 client = MilvusClient(

6)

7

8

9 client = MilvusClient(

14

15

print(client.list_databases())

print(client.list_users())

b、用户管理

代码块

# 创建新用户

client.create_user(

5

6
