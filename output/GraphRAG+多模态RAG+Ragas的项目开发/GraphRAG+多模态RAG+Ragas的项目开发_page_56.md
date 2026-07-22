## 第54页

# # 删除数据库

18 client.drop_database(

20 )

21 print(client.list_databases())

## 4、collections和数据操作

在 Milvus 上，您可以创建多个 Collections 来管理数据，并将数据作为实体插入到 Collections 中。

Collections 和实体类似于关系数据库中的表和记录。

Collection 是一个二维表，具有固定的列和变化的行。每列代表一个字段，每行代表一个实体。

Fields

Entities

id title

The Reported Mortality Rate of Coronavirus Is

Not Important

Dashboards in Python: 3 Advanced Examples

for Dash Beginners and Everyone Else

2 How Can We Best Switch in Python?

3 Maternity leave shouldn't set women back

4 Python NLP Tutorial: Information Extraction

and Knowledge Graphs

5 Guide to Nest JS-RabbitMQ Microservices

title_vector

[0.041732933, 0.013779674, -0.027564144, -0.013061441, 0.009748648, 0.0]

[0.019370917, -0.008112641, -0.014931766, 0.065622255, 0.0149185015, 0.0]

[0.0039737443, 0.003020432, -0.0006188639, 0.03913546, -0.00089768134,

-0.0076336027, -0.007048531, -0.03015078, 0.03309948, 0.028124114, 0.01

link

https://medium.com/swlh/

the-reported-mortality-rate-

of-coronavirus-is-not-

important-369989c8d912

https://medium.com/swlh/

dashboards-in-python-3-

advanced-examples-for-

dash-beginners-and-

everyone-else-

b1daf4e2ec0a

reading_time

publication

13

The Startup

claps

1100

responses

18

14

The Startup

726

3

6

The Startup

500

7

9

The Startup

460

1

7

The Startup

163

0

7

The Startup

184

0

Figure 1: A Medium article collection in Zilliz Cloud database.

## 一、Schema 和字段

Schema 定义了 Collections 的数据结构。在创建一个 Collection 之前，你需要设计出它的 Schema。

Collection Schema 定义了 数据库中如何组织 Collection 中的数据。一个 Collection Schema 有一个

主键、最多四个向量字段和几个标量字段。下图说明了如何将文章映射到模式字段列表。
