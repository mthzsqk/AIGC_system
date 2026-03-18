# AIGC 智能社团策划系统 (AIGC Club Planner)

这是一个基于 Python 和 DeepSeek 大模型的智能社团活动策划辅助系统。 (Final Year Programming)

## 🚀 快速启动

1. **双击运行 `start_system.bat`**
   - 该脚本会自动检查依赖、启动后端服务，并打开浏览器访问系统界面。
   - 请保持弹出的黑色命令窗口运行，不要关闭。

2. **手动启动方式**
   如果你更喜欢使用命令行：
   ```bash
   # 1. 安装依赖
   pip install -r AIGC_Club_Planner/requirements.txt

   # 2. 启动后端服务
   python -m uvicorn AIGC_Club_Planner.app.main:app --reload --port 8000
   ```
   然后访问: `http://localhost:8000/static/index.html`

## 🛠️ 系统配置

- **DeepSeek API**: 已配置在 `AIGC_Club_Planner/.env` 文件中。
- **依赖库**: 位于 `AIGC_Club_Planner/requirements.txt`。

## 📂 项目结构

- `AIGC_Club_Planner/app`: 后端代码 (FastAPI)
  - `services/rag_service.py`: 高级 RAG 实现
  - `services/agent_service.py`: 智能体工作流实现
  - `utils/llm_client.py`: LLM 调用客户端
- `AIGC_Club_Planner/static`: 前端代码 (HTML/Vue/Tailwind)
