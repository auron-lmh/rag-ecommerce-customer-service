## 第2页

# APIs: Every tool needs its own key

传统APIs需要为每个服务进行不同的认证和集成，就像需要不同钥匙开不同锁一样

MCP的核心是对大模型调用外部工具建立一个标准化流程。MCP基于 Function Calling，进一步定义了从请求构建、发送、执行到结果返回的标准化流程。通过 MCP，模型可以以统一方式与各种外部工具和数据源交互，极大提升了跨平台兼容性和 AI 应用开发效率。

Without MCP

With MCP

MCP 与 Function Calling 的区别和联系如下：

- • Function Calling : 是 LLM 内部定义的一组函数，通过 JSON schema 让 LLM知道有哪些功能能调用。
