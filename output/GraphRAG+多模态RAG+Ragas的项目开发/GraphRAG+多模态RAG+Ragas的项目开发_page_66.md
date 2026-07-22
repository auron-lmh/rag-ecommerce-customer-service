## 第64页

代码块 analyzer_params = {

2 "tokenizer": "jieba",

3 "filter": ["cnalphanumonly"],

4 }

5

6 analyzer_params = {

7 "type": "chinese",

8 }

9

english 分析器使用以下组件:

标记化器：使用 standard 标记化器将文本分割成离散的单词单位。

过滤器：包括多个过滤器，用于全面处理文本：

lowercase :将所有标记转换为小写，从而实现不区分大小写的搜索。

stemmer :将单词还原为词根形式，以支持更广泛的匹配（例如，“running”变为“run”）。

stop_words :删除常见的英文停止词，以便集中搜索文本中的关键词语。

代码块

1 analyzer_params = {

2 "tokenizer": "standard",

3 "filter": [

"lowercase",

{

"type": "stemmer",

"language": "english"

}，{

"type": "stop",

"stop_words": "_english"

}

]

13 }

14

现在，定义一个将文本转换为稀疏向量表示的函数，然后将其添加到 Schema 中:

代码块

1 bm25_function = Function(

2 name="text_bm25_emb", # Function name

3 input_field_names=["text"], # Name of the VARCHAR field containing raw

text data

4 output_field_names=["sparse"],
