## 第16页

* @Description :

* @School:优极限学堂

* @Official-website: http://www.yjxxt.com

* @Teacher:李毅大帝

* @Mail:863159469@qq.com

* /

//创建一个线程生成数据

//生成一个商品ID

String goodId =

RandomStringUtils.randomAlphabetic(16).toLowerCase();

//发送goodInfo数据 [id:info.ts]

KafkaUtil.sendMsg("t_goodinfo", goodId + ":info" + i +

":" + System.currentTimeMillis());

//创建goodPrice数据[id:price.ts]

KafkaUtil.sendMsg("t_goodprice", goodId + "" + i + ":"

+ (System.currentTimeMillis() - 5000));

//让线程休眠一下

Thread.sleep(1000);
