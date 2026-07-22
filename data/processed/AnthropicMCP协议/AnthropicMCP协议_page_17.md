## 第17页

model="claude-3-haiku-20240307",

max_tokens=1000,

messages=messages,

tools=available_tools

)

# 初始化最终文本列表

final_text = []

print(f"response:{response}")

# 遍历 Claude 的响应内容

for content in response.content:

if content.type == 'text':

# 如果是文本，添加到最终文本列表

final_text.append(content.text)

elif content.type == 'tool_use':

# 如果是工具调用，提取工具名称和参数

tool_name = content.name

tool_args = content.input

# 调用工具，并获取工具结果

result = await self.session.call_tool(tool_name, tool_args)

# 添加工具调用信息到最终文本列表

final_text.append(f"[调用工具 {tool_name}，参数 {tool_args}]")

# 将工具返回的结果继续作为用户输入，发起新的对话

if hasattr(content, 'text') and content.text:

messages.append({

"role": "assistant",

"content": content.text

})

# 添加工具调用结果到消息列表

messages.append({

"role": "user",

"content": result.content

})

# 获取 Claude 新响应

response = self.anthropic.messages.create(

model="claude-3-haiku-20240307",

max_tokens=1000,

messages=messages,

)

# 将回复写入到final_text集合中

final_text.append(response.content[0].text)
