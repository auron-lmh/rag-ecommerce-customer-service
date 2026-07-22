## 第74页

3、下载模型，主要是下载配置和py文件

huggingface-cli download --resume-download Alibaba-NLP/gme-Qwen2-VL-2B-Instruct --local-

dir/root/autodl-tmp/models/iic/gme-Qwen2-VL-2B-Instruct

4、配置Hugging Face 相关的顶级缓存路径

默认是: ~/.cache/huggingface/hub/

export HF_HOME=/root/autodl-tmp/huggingface_cache

5、准备测试代码

代码块

1

2

3

4

5

# 指定本地模型路径

6

为你的实际路径

7

8

# 方式1：直接指定模型名并设置 cache_folder（如果模型已下载到本地，且结构符合 sentence-

transformers 的预期)

9

model = SentenceTransformer(

10

'Alibaba-NLP/gme-Qwen2-VL-2B-Instruct', # 或者使用本地路径 model_path

11

# cache_folder=model_path

12

)

13

14

15

corpus_texts = [

16

"Lambda架构中针对实时数据处理我们可以使用Spark计算框架进行分析,Spark针对实时数据进

行分析本质是将实时流数据看成微批进行处理。"，

17

"基于有状态计算的方式最大的优势是不需要将原始数据重新从外部存储中拿出来,从而进行全量计

算,因为这种计算方式的代价可能是非常高的。"，

18

]

19

20

# 假设的图像数据路径列表（本地路径）

21

corpus_images = [

22

"/root/autodl-tmp/code/PythonProject18/output/第一章 Apache Flink 概

述/48deddd5ed7d0927ff5de3fa3ab7e635.png"，

23

"/root/autodl-tmp/code/PythonProject18/output/第一章 Apache Flink 概

述/52854c9de195f06b255e93ca363b15db.png"，

24

]

25

26

27

# 1. 编码文本

28

# 对于文本，可以直接传入字符串列表
