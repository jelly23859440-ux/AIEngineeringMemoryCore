# AIEngineeringMemoryCore (AI记忆中枢)

> 如何正确使用AI的能力，搭建可靠的运行架构，才是接下来AI影响现实世界的基石。

一个**本地运行、模型无关**的记忆引擎。模拟人脑记忆巩固机制：工作时监听推理节奏，在上下文将满前自动触发"心跳巩固"，将对话历史压缩为**情景骨架 + 精确实体索引**双层记忆。

## 快速开始

### 1. 安装依赖

```bash
cd AIEngineeringMemoryCore
pip install -r requirements.txt
```

### 2. 准备模型服务

确保本地已安装并运行 Ollama，并拉取所需模型：

```bash
ollama pull llama3
ollama pull nomic-embed-text
```

或配置任意 OpenAI 兼容 API。

### 3. 启动

```bash
python start.py
```

首次运行会引导你完成配置，之后自动静默启动。

### 4. 使用

```python
from memory_hub import AIMemoryHub
from config import AppConfig

config = AppConfig()
hub = AIMemoryHub(config)
hub.start()

# 记录对话
hub.record_exchange("我们要开发支付模块", "好的，建议使用Stripe")

# 检索相关记忆
context = hub.inject_memory_context("支付")
print(context)

# 标记子任务完成（冷归档）
hub.mark_subtask_complete("payment", ["支付模块", "Stripe"])

hub.stop()
```

## 配置说明

编辑 `config.yaml`：

```yaml
management_ai:
  api_base: "http://localhost:11434/v1"  # API端点
  api_key: ""                             # API密钥
  model: "llama3"                         # 模型名称

memory:
  storage_path: "./.memory"               # 记忆存储位置
  heartbeat_ratio: 0.8                    # 心跳触发阈值比例
  context_limit: 4096                     # 上下文token上限
  cold_storage_enabled: true              # 是否启用冷热分级

retrieval:
  top_k_summaries: 5                      # 返回摘要数量
  top_m_entities: 10                      # 返回实体数量
  embed_model: "nomic-embed-text"         # 嵌入模型

memory_manager:
  mode: "hybrid"                          # async | realtime | hybrid
  async_heartbeat_batch: 60               # 异步批次大小
```

## 记忆存储结构

```
.memory/
├── summaries/              # 情景骨架摘要
├── entities/               # 精确实体索引
├── cold/                   # 冷记忆归档
├── chroma/                 # ChromaDB 向量索引
├── .backup/                # 旧条目备份
└── heartbeat_state.json    # 心跳计数状态
```

## 运行测试

```bash
cd tests
python test_models.py
python test_project_manager.py
python test_heartbeat_monitor.py
python test_consolidator.py
python test_cold_storage.py
python test_retriever.py
python test_scheduler.py
python test_processor.py
python test_memory_hub.py
```

## 项目结构

```
AIEngineeringMemoryCore/
├── models.py                          # 核心数据结构
├── project_manager.py                 # 项目隔离管理
├── heartbeat_monitor.py               # 心跳监控器
├── consolidator.py                    # 巩固模型适配器
├── cold_storage_manager.py            # 冷热分级管理
├── memory_retriever.py                # 记忆检索器
├── memory_manager_scheduler.py        # 调度器
├── memory_consolidation_processor.py  # 整理处理器
├── config.py                          # 配置模型
├── memory_hub.py                      # 主控枢纽
├── start.py                           # 启动入口
├── requirements.txt                   # 依赖
├── config.yaml                        # 配置文件
├── examples/                          # 示例代码
├── tests/                             # 单元测试
└── README.md
```

## 核心理念

1. **承认模型的边界，用架构补足** — 模型有物理上限，记忆中枢在边界处架起延伸的桥梁。
2. **记忆是结构，不是日志** — 压缩归纳，情景骨架快速重建认知，实体索引高保真回溯。
3. **用户永远掌握控制权** — 记忆存本地，巩固用本地模型，全部可配置。
4. **可靠的架构才是基石** — 稳定的记忆架构比等待下一个更强模型更值得投入。
