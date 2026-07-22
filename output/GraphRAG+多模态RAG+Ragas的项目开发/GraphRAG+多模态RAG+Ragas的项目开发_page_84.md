## 第81页

Answer Relevancy = \frac{1}{N} \sum_{i=1}^{N} cosine similarity(E_{gi}, E_{o})

Answer Relevancy = \frac{1}{N} \sum_{i=1}^{N} \frac{E_{gi} \cdot E_{o}}{||E_{gi}|| \cdot ||E_{o}||}

其中

- $E_{g_i}$: 第 $i$ 个生成问题的嵌入。

- $E_{o}$: 用户输入的嵌入。

- $N$: 生成问题的数量（默认为 3）。

如果回答直接且恰当地回应了原始问题，则被认为是相关的。此指标侧重于回答与问题意图的匹配程度

度，但不评估事实准确性。它会惩罚不完整或包含不必要细节的回答。

代码块

1 # 答案相关性，`ResponseRelevancy` 指标衡量回答与用户输入的关联程度。

2 response_relevancy = ResponseRelevancy( llm=self. evaluator_llm,

embeddings=self.evaluator_embeddings)

3 response_relevancy_score = await response_relevancy.single_turn_ascore(sample)

4 print(f"答案相关性: {response_relevancy_score}"

3.4、忠诚度或者忠实度（Faithfulness）

忠实度指标衡量了 响应 与 检索到的上下文 的事实一致性。其取值范围为 0 到 1，分数越高表示一

致性越好。

如果一个响应的所有主张都能得到检索到的上下文的支持，则该响应被认为是忠实的。无需:

reference

计算方法如下

1. 识别响应中的所有主张。

2. 检查每个主张，看它是否可以从检索到的上下文中推断出来。

3. 使用以下公式计算忠实度分数

忠实度分数 = \frac{响应中得到检索到的上下文支持的主张数量}{响应中的主张总数}

代码块
