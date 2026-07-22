## 第42页

return new CommandLineRunner() {

@Override

public void run(String... args) throws Exception {

// 构建聊天客户端

var chatClient = chatClientBuilder

//设置系统提示，引导 AI 的行为和角色

.defaultSystem("你是一个可以查询天气的助手，可以调用工具回答用户关于天气相关问题。")

//配置工具回调提供者，使 AI 能调用外部工具

.defaultTools(new SyncMcpToolCallbackProvider(mcpSyncClients))

//设置对话记忆，使用内存存储对话历史，保持上下文

.defaultAdvisors(new MessageChatMemoryAdvisor(new InMemoryChatMemory()))

.build();

// 开始聊天循环

System.out.println("\n我是你的AI助手。\n");

try (Scanner scanner = new Scanner(System.in)) {

while (true) {

System.out.print("\n用户: ");

System.out.println("\n助手: " +

chatClient.prompt(scanner.nextLine()) // chatClient.prompt(...)：将用户输入作为提示发

.call()

.content());//.call().content()：调用 LLM 模型并获取响应内容

}

}

}

};

// return args -> {

//

// // 构建聊天客户端

// var chatClient = chatClientBuilder

// //设置系统提示，引导 AI 的行为和角色。

// .defaultSystem("你是一个可以查询天气的助手，可以调用工具回答用户关于天气相关问题。")

// //配置工具回调提供者，使 AI 能调用外部工具

// .defaultTools(new SyncMcpToolCallbackProvider(mcpSyncClients))

// //设置对话记忆，使用内存存储对话历史，保持上下文

// .defaultAdvisors(new MessageChatMemoryAdvisor(new InMemoryChatMemory()))

// .build();

//

// // 开始聊天循环

// System.out.println("\n我是你的AI助手。\n");

// try (Scanner scanner = new Scanner(System.in)) {

// while (true) {

// System.out.print("\n用户: ");

// System.out.println("\n助手: " +

// chatClient.prompt(scanner.nextLine()) // chatClient.prompt(...)：将用户输入作为提示发送

// .call()

// .content());//.call().content()：调用 LLM 模型并获取响应内容

// }

// }
