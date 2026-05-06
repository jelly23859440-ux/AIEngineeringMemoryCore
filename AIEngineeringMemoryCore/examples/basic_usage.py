"""
basic_usage.py - AI记忆中枢基本使用流程演示

运行前请确保:
1. 已安装依赖: pip install -r requirements.txt
2. 已启动本地 Ollama 服务 (或配置了远程 API)
3. 已拉取所需模型: ollama pull llama3 && ollama pull nomic-embed-text
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AppConfig, create_default_config, load_config
from memory_hub import AIMemoryHub


def demo():
    if not Path("demo_config.yaml").exists():
        create_default_config("demo_config.yaml")

    config = load_config("demo_config.yaml")

    hub = AIMemoryHub(config, root_dir=str(Path.cwd()))
    hub.start()

    try:
        exchanges = [
            ("我们正在开发一个电商系统，请帮我搭建项目框架。", "好的，我来帮你创建电商系统的项目结构，包含用户模块、商品模块和订单模块。"),
            ("用户模块需要支持邮箱注册和手机号登录。", "我来实现用户模块。注册支持邮箱验证，登录支持手机号+验证码方式。"),
            ("支付模块应该用哪个支付网关？", "建议使用 Stripe，它支持全球支付且 API 文档完善。"),
            ("好的，那就用 Stripe。退款回调的 timeout 应该设多少？", "建议先设置 5000ms，如果出现超时再调整。Stripe 官方推荐 3000-8000ms 之间。"),
        ]

        for user_msg, ai_response in exchanges:
            hub.record_exchange(user_msg, ai_response)

        query = "支付模块使用什么支付网关？"
        context = hub.inject_memory_context(query)
        print("=" * 50)
        print("查询:", query)
        print(context)
        print("=" * 50)
        print("记忆协作协议:")
        print(hub.get_memory_protocol())

        hub.mark_subtask_complete("payment_setup", ["支付模块", "Stripe集成", "退款回调"])

        query2 = "Stripe集成的配置是什么？"
        context2 = hub.inject_memory_context(query2)
        print("=" * 50)
        print("冷记忆唤醒查询:", query2)
        print(context2)
        print("=" * 50)

    finally:
        hub.stop()

    print("演示完成!")


if __name__ == "__main__":
    demo()
