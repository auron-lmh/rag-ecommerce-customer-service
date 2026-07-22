## 第48页

1 # 1、下载官网指定的脚本文件

2 # Milvus 在 Milvus 资源库中提供了 Docker Compose 配置文件。要使用 Docker Compose 安

装 Milvus，只需运行

3 wget https://github.com/milvus-io/milvus/releases/download/v2.6.0/milvus-

standalone-docker-compose.yml -0 docker-compose.yml

4

5 # 2、启动、停止 和删除Milvus数据库的docker容器

6 sudo docker compose up -d

7 docker restart milvus-standalone

8 # Stop Milvus

9 sudo docker compose down

10

11 # Delete service data

12 sudo rm -rf volumes

13

14 # 安装可视化客户端attu

15 docker run -d -p 8080:3000 -e MILVUS_URL=localhost:19530 zilliz/attu:v2.6

下载Docker Compose 配置文件

[root@iZ8vb5acpt0ebqsuf5mtiwZ home]# wget https://github.com/milvus-io/milvus/releases/download/v2.6.0/milvus-standalo

ne-docker-compose.yml -0 docker-compose.yml

--2025-09-06 15:57:04-- https://github.com/milvus-io/milvus/releases/download/v2.6.0/milvus-standalone-docker-compose

.yml

Resolving github.com (github.com) ... 20.205.243.166

Connecting to github.com (github.com) |20.205.243.166|:443... connected.

HTTP request sent, awaiting response... 302 Found

Location: https://release-assets.githubusercontent.com/github-production-release-asset/208728772/fb20162d-c9b3-43c0-ae

2b-a9704265272f?sp=r&sv=2018-11-09&sr=b&spr=https&se=2025-09-06T08%3A37%3A32Z&rscd=attachment%3B+filename%3Dmilvus-sta

ndalone-docker-compose.yml&rsct=application%2Foctet-stream&skoid=96c2d410-5711-43a1-aedd-ab1947aa7ab0&sktid=398a6654-9

97b-47e9-b12b-9515b896b4de&skt=2025-09-06T07%3A37%3A13Z&ske=2025-09-06T08%3A37%3A32Z&skS=b&skv=2018-11-09&sig=peDyAgjs

iKLA45az%2BkpQzgfPr5YLhGSduqIuh5V4M3M%3D&jwteyJ0eXAi0iJKV1qiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWiuY29tIiwiYXVkIjoi

cmVsZWFzZS1hc3NldHMuZ2l0aHvidXNLCmNvbnRlbnQuY29tIiwia2V5Ijoi2V5MSIsImV4cCI6MTc1NzE0NTcyNSwibmJmIjoxNzU3MTQ1NDII1LCJwYX

RoIjoicmVsZWFzZWFzc2V0cHJVZHvdGlvbi5ibG9iLmNvcMud2luZG93cy5uZXQifQ.WnGNGaC2NwDMFsV_w-Wur1NmDIgX3uXrHDKzLHLtznM&respo

nse-content-disposition=attachment%3B%20filename%3Dmilvus-standalone-docker-compose.vml&response-content-type=applicat

第一次启动:

docker-compose.yml

100%[===================================================>] 1.75K 2.91KB/s in 0.6s

2025-09-06 15:57:23 (2.91 KB/s)

' docker-compose.yml'

saved [1788/1788]

[root@iZ8vb5acpt0ebqsuf5mtiwZ home]# ls

docker-compose.yml download embedEtcd.yaml rag_env standalone_embed.sh test_graphrag user.yaml volumes

[root@iZ8vb5acpt0ebqsuf5mtiwZ home]# sudo docker compose up -d

WARN [0000] /home/docker-compose.yml: version is obsolete

[+] Running 31/12

standalone [###] 875.5MB / 876.2MB Pulling

etcd Pulled

minio Pulled

第一次启动会自动下载Milvus的docker镜像

116

33

26
