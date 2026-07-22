## 第23页

# 将工具返回的结果继续作为用户输入，发起新的对话

# 继续请求 LLM 获取完整回复

$$
next_response = self.client.chat.completions.create(model=LLM_MODEL,
$$

$$
max_tokens=1000,
$$

$$
messages=messages,
$$

$$
)
$$

for next_choice in next_response.choices:

$$
next_message = next_choice.message
$$
