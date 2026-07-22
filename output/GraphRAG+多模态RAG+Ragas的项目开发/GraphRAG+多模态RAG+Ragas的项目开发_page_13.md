## 第12页

# allow_general_knowledge: 将此设置为 True 将在 reduce_system_prompt 中包含其

他说明，以提示 LLM 结合数据集之外的相关真实世界知识。请注意，这可能会增加幻觉，但对于

某些场景可能有用。默认为 False* general_knowledge_inclusion_prompt: 如果启用

allow_general_knowledge，则添加到 reduce_system_prompt 的指令。默认指令可

以在general_knowledge_instruction中找到

max_data_tokens: 上下文数据的令牌预算

map_llm_params: 要在 map 阶段传递给 LLM 调用的附加参数字典（例如，温度、

max_tokens)

reduce_llm_params: 要在 reduce 阶段传递给 LLM 调用的附加参数字典（例如，温度、

max_tokens)

context_builder_params: 在为 map 阶段构建上下文窗口时，传递给

context_builder 对象的附加参数字典。

concurrent_coroutines: 控制 map 阶段的并行度。

callbacks: 可选的回调函数，可用于为 LLM 的完成流事件提供自定义事件处理程序。

## DRIFT 搜索

DRIFT 搜索（具有灵活遍历的动态推理和推断）建立在微软的 GraphRAG 技术之上，结合了全局搜索

和本地搜索的特性，使用我们的 drift search 方法，以在计算成本和质量结果之间取得平衡的方式生成

详细响应。

A

B

C

整个 DRIFT 搜索层级结构，突出显示了 DRIFT 搜索过程的三个核心阶段。

1. A (首先): DRIFT 将用户的查询与语义最相关的 K 个社区报告进行比较，生成广泛的初始答案和后

续问题，以指导进一步的探索。

2. B (后续): DRIFT 使用本地搜索来优化查询，产生额外的中间答案和后续问题，从而增强特异性，

引导引擎找到上下文丰富的信息。图中的每个节点上的字形都显示了算法继续查询扩展步骤的置信

度。

3. C（输出层级）：最终输出是一个按相关性排序的问题和答案的层级结构，反映了全局洞察和本地

改进的平衡组合，使结果具有适应性和全面性。

DRIFT 搜索通过在搜索过程中包含社区信息，引入了一种新的本地搜索查询方法。这大大扩展了查询

起点的广度，并导致在最终答案中检索和使用了更多种类的的事实。这种添加通过为本地搜索提供更

全面的选项来扩展 GraphRAG 查询引擎，该选项使用社区洞察力将查询细化为详细的后续问题。
