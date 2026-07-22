## 第23页

# 将工具返回的结果继续作为用户输入，发起新的对话

messages.append({

"role": "user",

"content": result.content

})

# 继续请求 LLM 获取完整回复

next_response = self.client.chat.completions.create(

model=LLM_MODEL,

max_tokens=1000,

messages=messages,

)

for next_choice in next_response.choices:

next_message = next_choice.message

if next_message.content:

final_text.append(next_message.content)

elif choice.finish_reason == 'stop':

# 正常结束，没有工具调用

if message.content:

final_text.append(message.content)

return "\n".join(final_text)

async def chat_loop(self):

""" 运行交互式聊天循环 """

print("\nMCP 客户端已启动!")

print(" 输入你的查询或 'quit' 退出。 ")

while True:

try:

query = input("\n 查询: ").strip()

if query.lower() == 'quit':

break

response = await self.process_query(query)

print("\n" + response)

except Exception as e:

print(f"\n 错误: {str(e)}")

async def cleanup(self):

""" 清理资源 """

await self.exit_stack.aclose()

async def main():
