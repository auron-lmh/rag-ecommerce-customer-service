## 第18页

return "\n".join(final_text)

async def chat_loop(self):

"""运行交互式聊天循环"""

print("\nMCP 客户端已启动!")

print("输入你的查询或 'quit' 退出。")

while True:

try:

query = input("\n查询: ").strip()

if query.lower() == 'quit':

break

response = await self.process_query(query)

print("\n" + response)

except Exception as e:

print(f"\n错误: {str(e)}")

async def cleanup(self):

"""清理资源"""

await self.exit_stack.aclose()

async def main():

if len(sys.argv) < 2:

print("在参数中指定 server脚本完整路径！")

sys.exit(1)

client = MCPClient()

try:

await client.connect_to_server(sys.argv[1])

await client.chat_loop()

finally:

await client.cleanup()

if __name__ == "__main__":

import sys

asyncio.run(main())

## 关于MCP Client 代码注意如下几点：

- 需要在.env文件中设置ANTHROPIC_API_KEY

- 运行该Client代码需要传入MCP Server 对应代码位置，MCP Client 会作为父进程启动 MCP Server 并进行连接，并通过标准输入输出（stdin/stdout）与之进行通信。
