# LearnPath - 个性化学习路径规划助手

基于大语言模型（DeepSeek）的智能学习路径规划工具。通过分析用户的学习目标、当前水平、学习节奏和资源偏好，自动生成分层级技能树（初级→中级→高级），推荐匹配的学习资源，并提供配套练习题与正确率跟踪，帮助学习者高效、系统地掌握目标技能。

## 技术栈
- **后端**：Python、FastAPI
- **前端**：Streamlit
- **数据库**：SQL Server（Windows 身份验证）
- **其他**：DeepSeek API、pyodbc、python-dotenv、requests、pandas

## 快速开始
### 环境要求
- Python 3.8 或更高版本
- SQL Server（需安装对应版本的 ODBC Driver，如 ODBC Driver 17 for SQL Server）
- DeepSeek API Key（或兼容 OpenAI 格式的 API Key）
- 操作系统：Windows（数据库使用 Windows 身份验证）

### 安装步骤
1. 克隆本仓库到本地。
2. 创建并激活 Python 虚拟环境（推荐）。
3. 安装依赖包：fastapi、uvicorn、streamlit、pyodbc、python-dotenv、requests、pandas、openai。
4. 在项目根目录创建 `.env` 文件，配置以下环境变量：
   - `DEEPSEEK_API_KEY`：你的 DeepSeek API 密钥
   - `API_BASE_URL`：DeepSeek API 地址（如 https://api.deepseek.com/v1）
   - `SQL_SERVER_DRIVER`：ODBC 驱动名称（如 {ODBC Driver 17 for SQL Server}）
   - `SQL_SERVER_SERVER`：SQL Server 实例名（如 localhost\SQLEXPRESS）
   - `SQL_SERVER_DATABASE`：数据库名称
   - `BACKEND_URL`：后端服务地址（默认 http://127.0.0.1:8000）
5. 在 SQL Server 中创建数据库，并建立以下表（字段参考数据库设计部分）。
6. 启动后端服务：在终端执行 `uvicorn main:app --reload --host 0.0.0.0 --port 8000`。
7. 启动前端应用：在另一个终端执行 `streamlit run app.py`，访问 `http://localhost:8501` 即可使用。

## 数据库设计
主要表结构及字段说明：

- **LEARNING_PATH**：学习路径主记录  
  `path_id` (主键), `target` (学习目标), `level` (当前水平), `pace` (学习节奏), `resource_type` (资源类型偏好), `path_content` (生成的完整技能树内容)

- **LEARNING_MODULE**：技能模块  
  `module_id` (主键), `path_id` (外键), `module_name` (模块名称), `estimated_hours` (预计学习时长), `dependency` (前置依赖), `level` (所属层级), `learning_goal` (学习目标)

- **LEARNING_RESOURCE**：学习资源  
  `resource_id` (主键), `module_id` (外键), `title` (资源标题), `url` (链接), `source` (来源平台), `tag` (适配标签), `type` (资源类型：视频/文档)

- **EXERCISE**：练习题  
  `exercise_id` (主键), `module_id` (外键), `question` (题目内容), `answer` (答案), `analysis` (解析), `difficulty` (难度等级), `options` (单选题选项，逗号分隔)

- **USER_ANSWER**：用户答题记录  
  `answer_id` (主键), `path_id`, `module_name`, `exercise_id`, `user_answer` (用户答案), `is_correct` (是否正确), `submit_time` (提交时间)

- **USER_PROGRESS**：用户学习进度  
  `progress_id` (主键), `path_id`, `module_name`, `status` (完成状态), `accuracy` (正确率), `update_time` (更新时间)
