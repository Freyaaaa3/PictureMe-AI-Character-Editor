# Picture-Me-AI-人物形象编辑器
Picture Me – AI 人物形象编辑器 一站式 AI 图像生成工具，专注于改变图片中人物的发型、妆容、风格及年代感。上传一张人像，选择「发型设计」「妆容风格」「风格照片」或「时间穿越」功能，系统自动调用 通义万相 与 豆包 API 同时生成两张对比图片，直观比较不同模型的效果。


AI-powered image editor for hairstyle, makeup, fashion & time travel. Compare 通义万相 vs 豆包[人工智能ai4-最终版.pdf](https://github.com/user-attachments/files/26784094/ai4-.pdf)
 API side‑by‑side. RAG prompt enhancement with DeepSeek‑R1. Flask web UI.

✨ 核心亮点
🎭 四大功能：发型变换 / 妆容迁移 / 时尚大片 / 跨时代穿越（古埃及→未来主义）

🤖 双模型并行：通义万相（i2i）+ 豆包 Seedream 4.0，结果并列展示（也支持调用其他模型）

🧠 RAG 提示词增强：基于 Ollama + DeepSeek-R1 智能优化用户描述，生成更专业 prompt

🌐 简洁 Web 界面：拖拽上传、实时预览、功能卡片选择，开箱即用

📁 自动保存生成图片至本地目录，支持健康检查与错误重试

适用场景：虚拟试妆、发型设计、创意摄影、复古/未来风格生成、AI 绘画教学。

技术栈：Flask + 通义万相 API + 豆包 API + Ollama（DeepSeek-R1）+ 向量检索增强（RAG）

需配置 .env 文件中的 QWEN_API_KEY 与 ARK_API_KEY，可选启用 RAG 增强。

立即体验：python app.py 访问 http://localhost:5000

[人工智能ai4-最终版.pdf](https://github.com/user-attachments/files/26784096/ai4-.pdf)
