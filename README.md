# 基于 LangChain 与 RAG 的智能扫地机器人售后问答系统

## 1. 项目简介

本项目是一个面向智能扫地机器人售后服务场景的智能问答系统。系统基于 Streamlit 构建前端交互界面，使用 LangChain Agent 组织大模型推理流程，并结合 Chroma 向量数据库实现本地知识库检索问答。

系统支持产品知识问答、故障排查、用户使用数据查询和月度报告生成等功能，可用于智能家居售后客服场景下的轻量级 AI Agent 应用。

## 2. 技术栈

- Python
- Streamlit
- LangChain
- LangGraph
- Chroma
- DashScope / 通义千问
- RAG
- YAML 配置管理
- Logging 日志模块

## 3. 核心功能

- 基于 Streamlit 搭建聊天式交互界面
- 基于 LangChain Agent 实现工具调用流程
- 支持 PDF/TXT 文档加载、切分和向量化存储
- 基于 Chroma 构建本地向量知识库
- 支持扫地机器人产品问答、维护建议和故障排查
- 支持用户使用记录查询
- 支持动态 Prompt 切换，实现月度使用报告生成
- 支持日志记录、配置文件读取和统一路径管理

## 4. 项目结构

```text
Agent/
├── app.py
├── check_imports.py
├── agent/
│   ├── __init__.py
│   ├── react_agent.py
│   └── tools/
│       ├── __init__.py
│       ├── agent_tools.py
│       └── middleware.py
├── rag/
│   ├── __init__.py
│   ├── rag_service.py
│   └── vector_store.py
├── model/
│   ├── __init__.py
│   └── factory.py
├── Agent_project/
│   ├── __init__.py
│   └── utils/
│       ├── __init__.py
│       ├── config_handler.py
│       ├── file_handler.py
│       ├── logger_handler.py
│       ├── path_tool.py
│       └── prompt_loader.py
├── config/
├── prompts/
├── requirements.txt
├── .gitignore
└── README.md
```

## 5. 环境配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

项目需要配置 DashScope API Key。

可以在系统环境变量中配置：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

如果需要使用浏览器定位、当前位置天气和高德 IP 定位兜底能力，还需要配置高德 Web 服务 Key：

```env
AMAP_WEB_KEY=your_amap_web_key_here
```

当前代码直接从系统环境变量读取 Key。若需要使用 `.env` 文件，需在启动入口中自行加载环境变量。

注意：`.env` 是本地敏感文件，不应上传到 GitHub。

## 6. 启动项目

在项目根目录下运行：

```powershell
cd E:\AI_LLM\Agent
& "E:\Anacoda\envs\torch311\python.exe" -m streamlit run app.py
```

如果已经激活了对应的 Conda 环境，也可以运行：

```powershell
streamlit run app.py
```

## 7. 整体运行流程

项目的主流程从 `app.py` 开始，由 Streamlit 接收用户输入，再交给 `ReactAgent` 执行。

```text
用户在 Streamlit 页面输入问题
        ↓
app.py 获取输入、定位信息和历史消息
        ↓
ReactAgent.execute_stream(query)
        ↓
LangChain Agent 根据系统提示词判断是否需要调用工具
        ↓
工具层执行 RAG 检索、天气查询、定位查询、用户数据查询等能力
        ↓
模型结合用户问题和工具结果生成回答
        ↓
app.py 将回答流式输出到聊天页面
```

其中 `ReactAgent` 是整个智能体的装配层，它把模型、Prompt、工具和中间件组合起来，不直接实现具体业务逻辑。

## 8. 模块说明

### app.py

项目前端入口，负责 Streamlit 页面展示、用户输入、聊天记录保存和流式输出。

### agent/react_agent.py

负责创建 LangChain Agent，并组织模型、工具和中间件的调用流程。

该模块中的 `ReactAgent` 类主要包含两个部分：

- `__init__()`：调用 `create_agent()` 创建智能体，注入聊天模型、系统提示词、工具列表和中间件。
- `execute_stream(query)`：接收用户问题，将问题包装成 LangChain Agent 所需的 `messages` 格式，并通过 `self.agent.stream()` 流式返回结果。

`create_agent()` 中的核心组成如下：

```text
chat_model
    来自 model/factory.py，当前使用 qwen3-max。

load_system_prompts()
    从 prompts/main_prompt.txt 读取普通问答场景下的系统提示词。

tools
    来自 agent/tools/agent_tools.py，包括 RAG 问答、天气查询、定位查询、用户数据查询和报告上下文触发工具。

middleware
    来自 agent/tools/middleware.py，包括工具调用监控、模型调用前日志记录和动态 Prompt 切换。
```

`ReactAgent` 的执行链路如下：

```text
app.py
  └── ReactAgent.execute_stream(user_prompt)
        └── self.agent.stream(...)
              ├── 模型判断是否需要调用工具
              ├── 调用 agent_tools.py 中的具体工具
              ├── middleware.py 记录工具调用和模型调用日志
              └── 返回模型生成内容
```

当用户要求生成使用报告时，Agent 会调用 `fill_context_for_report` 工具。该工具被中间件捕获后，会将运行时上下文中的 `report` 标记改为 `True`，随后 `report_prompt_switch` 会自动切换到 `prompts/report_prompt.txt`，让同一个 Agent 从普通问答模式切换到报告生成模式。

### agent/tools/agent_tools.py

封装业务工具函数，包括知识库问答、天气查询、用户位置查询、使用记录查询和报告上下文触发工具。

### agent/tools/middleware.py

封装 Agent 中间件逻辑，包括工具调用监控、模型调用前日志记录和动态 Prompt 切换。

### rag/rag_service.py

负责 RAG 问答流程，将用户问题与检索到的参考资料共同输入模型生成回答。

### rag/vector_store.py

负责本地知识库构建，包括文档加载、文本切分、向量化存储和检索器创建。

### model/factory.py

负责封装聊天模型和 Embedding 模型的创建逻辑。

### Agent_project/utils/

负责配置读取、路径管理、文件加载、日志记录和 Prompt 加载等基础工具能力。

## 9. 项目亮点

- 将普通大模型问答与本地知识库检索结合，提高回答的业务相关性。
- 使用 LangChain Agent 封装多工具调用流程，支持用户信息、外部数据和知识库的动态调用。
- 通过中间件实现动态 Prompt 切换，使普通问答和报告生成可以使用不同的提示词策略。
- 使用 YAML 配置管理、日志模块和统一路径工具，提高项目可维护性。
- 基于 Streamlit 实现可交互页面，支持流式响应和历史对话展示。

## 10. 后续优化方向

- 将随机模拟工具改为基于 CSV 或 SQLite 的真实用户数据查询。
- 增加扫地机器人故障代码诊断模块。
- 在 RAG 回答中展示参考来源，提高回答可解释性。
- 增加问答测试集，对检索命中率和响应耗时进行评估。
- 增加报告下载功能，支持导出月度使用报告。
- 优化前端页面，增加用户 ID、设备型号、功能模式等侧边栏配置。
