## 第22页

response = await self.session.list_tools()

tools = response.tools

print("\n已连接到服务器，可用工具:", [tool.name for tool in tools])

async def process_query(self, query: str) -> str:

"""使用 LLM 和可用工具处理查询"""

messages = [

{

"role": "user",

"content": query

}

]

response = await self.session.list_tools()

available_tools = [{

"type": "function", # OpenAI 方式中，必须加上

"function":{

"name": tool.name,

"description": tool.description,

"input_schema": tool.inputSchema

}

} for tool in response.tools]

# 初始 OpenAI API 调用

response = self.client.chat.completions.create(

model=LLM_MODEL,

max_tokens=1000,

messages=messages,

tools=available_tools

)

print(f"response:{response}")

# 处理响应和工具调用

final_text = []

for choice in response.choices:

message = choice.message

if choice.finish_reason == 'tool_calls':

# 有工具调用

for tool_call in message.tool_calls:

tool_name = tool_call.function.name

import json

tool_args = json.loads(tool_call.function.arguments)

# 执行工具调用

result = await self.session.call_tool(tool_name, tool_args)

final_text.append(f"[调用工具 {tool_name}，参数 {tool_args}]")
