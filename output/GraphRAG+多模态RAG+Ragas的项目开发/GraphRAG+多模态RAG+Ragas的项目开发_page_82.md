## 第79页

上下文精度 (Context Precision) 是一个衡量 retrieved_contexts 中相关块比例的指标。它的计算方法是上下文中的每个块的 precision@k 的平均值。Precision@k 是在排名 k 处的相关块数量与排名 k 处的块总数的比率。

Context Precision@K = \frac{\sum_{k=1}^{K} (Precision@k \times v_k)}{前 K 个结果中的相关项总数}

其中 K 是 retrieved_contexts 中的总块数。

无参考的上下文精度

当您对某个 user_input 同时拥有检索到的上下文和参考上下文时，可以使用

LLMContextPrecisionWithoutReference 指标。为了判断检索到的上下文是否相关，此方法

使用 LLM 将 retrieved_contexts 中存在的每个检索到的上下文或块与 response 进行比

较。

有参考的上下文精度

当您对某个 user_input 同时拥有检索到的上下文和参考答案时，可以使用

LLMContextPrecisionWithReference 指标。为了判断检索到的上下文是否相关，此方法使

用 LLM 将 retrieved_contexts 中存在的每个检索到的上下文或块与 reference 进行比较。

代码块

# 1. 创建评估样本 (SingleTurnSample)

# SingleTurnSample用于表示单轮对话的评估样本

sample = SingleTurnSample(

user_input=question, # 用户输入的问题

retrieved_contexts=[context['text'] for context in contexts], # 检索到的上下

文

response=response, # 生成的答案

reference=reference # 参考答案（用于需要参考答案的指标）

8 )

9

# 2. 初始化评估指标

# 该指标评估生成答案中与检索上下文相关部分的比例

12 if reference:

# 如果有参考答案，则初始化指标为LLMContextPrecisionWithReference

context_precision =

LLMContextPrecisionWithReference(ilm=self.evaluator_llm)

15 else:

# 如果没有参考答案，则初始化指标为LLMContextPrecisionWithoutReference

context_precision =

LLMContextPrecisionWithoutReference(ilm=self.evaluator_llm)

18

# 3. 计算评估分数（异步方法，需要使用await）
