## 第21页

# Deepseek

# LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# LLM_URL = "https://api.deepseek.com"

# LLM_MODEL = "deepseek-chat"

# 阿里通义千问

LLM_API_KEY = os.getenv("TONGYI_API_KEY")

LLM_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

LLM_MODEL = "qwen-plus"

class MCPClient:

def __init__(self):

# 初始化会话和客户端对象

self.session: Optional[ClientSession] = None

self.exit_stack = AsyncExitStack()

#创建OpenAI Client

self.client = OpenAI(

api_key=LLM_API_KEY, # API KEY

base_url=LLM_URL

)

async def connect_to_server(self, server_script_path: str):

"""连接到 MCP 服务器

参数：

server_script_path: 服务器脚本路径 (.py 或 .js)

"""

is_python = server_script_path.endswith('.py')

is_js = server_script_path.endswith('.js')

if not (is_python or is_js):

raise ValueError("服务器脚本必须是 .py 或 .js 文件")

command = sys.executable if is_python else "node"

server_params = StdioServerParameters(

command=command,

args=[server_script_path],

env=None

)

# 与MCP 服务器建立通信

stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))

self.stdio, self.write = stdio_transport

self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

await self.session.initialize()

# 列出可用工具
