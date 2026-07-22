## 第11页

# context_builder_params：构建搜索提示的上下文时，要传递给 context_builder 对

象的其他参数的字典

callbacks：可选的回调函数，可用于为 LLM 的完成流事件提供自定义事件处理程序

## 全局搜索

Global Search Dataflow

RIR

Rated Intermediate

Response 1

Rated Intermediate

Response 2

{1..N)

Rated Intermediate

Response N

User Query

Conversation History

Shuffled Community

Report Batch 1

Shuffled Community

Report Batch 2

Shuffled Community

Report Batch N

Ranking +

Filtering

Aggregated Intermediate

Responses

Response

搜索过程：给定用户查询，以及可选的对话历史，全局搜索方法使用来自图形社区层次结构的指定级

别的 LLM 生成的社区报告集合作为上下文数据，以 map-reduce 的方式生成响应。在 map 步骤中，

社区报告被分割成预定义大小的文本块。然后，每个文本块用于生成包含一系列要点的中间响应，每

个要点都附有数值评分，指示该要点的重要性。在 reduce 步骤中，聚合从中间响应中筛选出的一组

最重要的要点，并将其用作上下文以生成最终响应。

全局搜索响应的质量可能会受到为获取社区报告而选择的社区层次结构级别的严重影响。较低的层次

结构级别及其详细的报告往往会产生更彻底的响应，但也可能由于报告数量的增加而增加生成最终响

应所需的时间和 LLM 资源。

以下是GlobalSearch 类的关键参数

llm：用于生成响应的 OpenAI 模型对象

context_builder：用于从社区报告准备上下文数据的context builder对象

map_system_prompt：map 阶段中使用的提示模板。默认模板可以在map_system_prompt

中找到

reduce_system_prompt：reduce 阶段中使用的提示模板，默认模板可以在

reduce_system_prompt中找到

response_type：描述所需响应类型和格式的自由格式文本（例如，Multiple

Paragraphs、Multi-Page Report）
