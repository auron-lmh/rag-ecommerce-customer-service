## 第16页

if not (is_python or is_js):

raise ValueError("服务器脚本必须是 .py 或 .js 文件")

# 根据脚本类型设置命令，sys.executable获取当前 python解释器的可执行文件的绝对路径

# 例如：D:\ProgramData\Anaconda3\envs\python-mcp\python.exe

command = sys.executable if is_python else "node"

# 创建服务器参数对象

server_params = StdioServerParameters(

command=command,

args=[server_script_path],

env=None

)

# 与MCP 服务器建立通信

stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))

# 解包通信通道和写入函数

self.stdio, self.write = stdio_transport

# 创建客户端会话

self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

# 初始化会话

await self.session.initialize()

# 获取可用工具列表

response = await self.session.list_tools()

tools = response.tools

print("\n已连接到服务器，可用工具:", [tool.name for tool in tools])

# 定义异步方法，处理用户查询

async def process_query(self, query: str) -> str:

"""使用 Claude 和可用工具处理查询"""

# 构建用户消息

messages = [

{

"role": "user",

"content": query

}

]

# 获取可用工具列表

response = await self.session.list_tools()

available_tools = [{

"name": tool.name,

"description": tool.description,

"input_schema": tool.inputSchema

} for tool in response.tools]

# 使用 Claude 生成初始响应

response = self.anthropic.messages.create(
