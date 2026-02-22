from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyodbc
import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()
app = FastAPI(title="LearnPath 后端API")

# 初始化LLM客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("API_BASE_URL")
)


# 数据库连接函数
def get_db_connection():
    """获取SQL Server数据库连接（Windows身份验证）"""
    try:
        conn = pyodbc.connect(
            f"DRIVER={os.getenv('SQL_SERVER_DRIVER')};"
            f"SERVER={os.getenv('SQL_SERVER_SERVER')};"
            f"DATABASE={os.getenv('SQL_SERVER_DATABASE')};"
            f"Trusted_Connection=yes;"  # Windows身份验证的关键配置
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败：{str(e)}")


# 数据模型定义
class PathRequest(BaseModel):
    target: str
    level: str
    pace: str
    resource_type: str


class ProgressRequest(BaseModel):
    path_id: int
    module_name: str
    status: str
    accuracy: float = 0.0


class AnswerRequest(BaseModel):
    path_id: int
    module_name: str
    exercise_id: int
    user_answer: str
    is_correct: bool


class AccuracyRequest(BaseModel):
    path_id: int
    module_name: str = None


# Prompt构建函数 - 分层级技能树（核心修改）
def build_learning_path_prompt(target, level, pace, resource_type):
    """构建结构化分层级技能树Prompt"""
    prompt = f"""
    # 角色
    你是一位资深的学习规划专家，擅长为不同基础的学习者制定系统化、可落地的分层级技能树学习路径。

    # 用户需求
    - 核心目标：{target}
    - 当前水平：{level}
    - 学习节奏：{pace}（紧凑=每天2小时，总时长压缩；宽松=每天1小时，总时长适中）
    - 资源类型偏好：{resource_type}

    # 输出要求（必须严格遵守）
    1. 层级划分：必须按「初级→中级→高级」3个核心层级划分，每个层级包含2-3个技能模块；
    2. 层级要求：
       - 初级：基础入门技能，适配{level}零基础/入门用户，无前置依赖
       - 中级：进阶核心技能，依赖初级全部模块完成
       - 高级：实战/拔高技能，依赖中级全部模块完成
    3. 每个技能模块必须包含：
       - 模块名称（如“HTML基础”）
       - 预计学习时长（按{pace}节奏计算，单位：小时）
       - 所属层级（初级/中级/高级）
       - 前置依赖（模块名称列表）
       - 核心技能点（3-5个，适配{level}水平）
       - 学习目标（该模块掌握后能达成的具体目标）
    4. 格式要求：
       - 整体用Markdown格式输出，层级用一级标题（#），模块用二级标题（##）+ 列表展示；
       - 增加可视化分隔线和层级标识；
       - 不要多余的开场白/结束语，只输出技能树内容；
       - 时长要贴合{level}水平（初级模块≤10小时，中级≤15小时，高级≤20小时）；
    5. 内容适配：
       - 零基础用户：初级模块占比60%，侧重基础认知；
       - 入门级用户：初级40%+中级60%，侧重应用；
       - 进阶级用户：中级50%+高级50%，侧重实战；
       - 紧凑节奏：模块时长总和按目标周期压缩；
       - 宽松节奏：模块时长总和按目标周期放宽。

    # 示例输出格式（仅参考结构，不要复制示例内容）
    # 🟢 初级（基础入门）
    ---
    ## 1. HTML基础
    - 预计学习时长：8小时
    - 所属层级：初级
    - 前置依赖：无
    - 核心技能点：HTML文档结构、常用标签、属性、语义化HTML、基础表单
    - 学习目标：能够独立编写符合规范的HTML静态页面结构
    ## 2. CSS基础
    - 预计学习时长：10小时
    - 所属层级：初级
    - 前置依赖：HTML基础
    - 核心技能点：选择器、盒模型、样式属性、简单布局、响应式基础
    - 学习目标：能够为HTML页面添加样式，实现基础的页面布局
    # 🟡 中级（进阶核心）
    ---
    ## 1. CSS进阶
    - 预计学习时长：12小时
    - 所属层级：中级
    - 前置依赖：HTML基础、CSS基础
    - 核心技能点：Flex布局、Grid布局、动画效果、CSS变量、兼容性处理
    - 学习目标：能够实现复杂的页面布局和交互动效
    ## 2. JavaScript基础
    - 预计学习时长：15小时
    - 所属层级：中级
    - 前置依赖：HTML基础、CSS基础
    - 核心技能点：变量、数据类型、函数、DOM操作、事件处理
    - 学习目标：能够编写基础的交互逻辑，实现页面动态效果
    # 🔴 高级（实战拔高）
    ---
    ## 1. JavaScript进阶
    - 预计学习时长：18小时
    - 所属层级：高级
    - 前置依赖：JavaScript基础
    - 核心技能点：异步编程、原型链、闭包、模块化、ES6+特性
    - 学习目标：能够编写高性能、可维护的JavaScript代码
    ## 2. 前端框架（Vue）
    - 预计学习时长：20小时
    - 所属层级：高级
    - 前置依赖：JavaScript进阶、CSS进阶
    - 核心技能点：组件化、路由、状态管理、生命周期、API调用
    - 学习目标：能够独立开发中小型Vue项目
    """
    return prompt.strip()


# Prompt构建函数 - 学习资源
def build_resource_prompt(module_name, level, resource_type):
    """生成模块对应的学习资源Prompt（严格版）"""
    return f"""
    你是学习资源推荐专家，请为「{module_name}」模块（{level}水平）推荐 **2 个免费、可访问、高质量的学习资源**。

    要求必须严格遵守：

    1. 资源类型必须完全匹配：{resource_type}
       - 如果用户要求“视频”，必须全部是视频资源
       - 如果用户要求“文档”，必须全部是文档资源
       - 如果用户要求“视频+文档”，可以混合，但必须明确标记 type

    2. 资源必须是真实存在、可访问的公共资源
       - B站视频链接必须以 BV 开头
       - CSDN 文档必须是真实文章链接
       - 官方文档必须是官方域名（如 .org / .com / .cn）
       - 不允许虚构链接

    3. 每个资源必须包含以下字段：
       title（资源标题）
       url（资源链接）
       source（来源平台：B站 / CSDN / 官方文档 / 慕课网 / 掘金 / 知乎等）
       type（视频 / 文档）
       tag（必须包含 "{level}" 关键词，如“适合零基础”）

    4. 输出格式必须是 JSON 数组，不允许任何多余文字
       - 不要输出 Markdown
       - 不要输出解释
       - 不要输出代码块标记
       - 只输出 JSON

    5. 资源难度必须与 {level} 严格匹配
       - 零基础：内容必须是入门级，不包含复杂概念
       - 入门级：可包含基础到中等内容
       - 进阶级：可包含较深入的技术细节

    6. 示例格式（仅示例结构，不要复制示例内容）：
    [
        {{
            "title": "Python 零基础入门教程",
            "url": "https://www.bilibili.com/video/BV1234567890",
            "source": "B站",
            "type": "视频",
            "tag": "适合零基础"
        }},
        {{
            "title": "Python 基础语法详解",
            "url": "https://blog.csdn.net/xxx/article/details/123456789",
            "source": "CSDN",
            "type": "文档",
            "tag": "适合零基础"
        }}
    ]

    现在请为「{module_name}」生成资源。
    """.strip()


# 练习题Prompt（3单选+1问答）
def build_exercise_prompt(module_name, level):
    """生成模块对应的练习题Prompt：3道单选 + 1道问答题"""
    return f"""
    你是练习题生成专家，请为「{module_name}」模块（{level}水平）生成练习题。
    要求：
    1. 共 4 题：3 道单选题 + 1 道问答题；
    2. 单选题格式必须包含：question, options, answer, analysis, difficulty=1；
    3. 问答题格式必须包含：question, answer, analysis, difficulty=1；
    4. 题目难度适配{level}水平；
    5. 格式：仅返回JSON数组，不要多余内容；
    6. options 为数组，至少 4 个选项。

    示例输出（不要复制示例内容，仅参考结构）：
    [
        {{
            "type": "single_choice",
            "question": "云计算的核心特点不包括以下哪一项？",
            "options": ["按需分配", "弹性扩展", "本地部署", "资源池化"],
            "answer": "本地部署",
            "analysis": "云计算的核心特点包括按需分配、弹性扩展、资源池化，本地部署不属于云计算特点。",
            "difficulty": 1
        }},
        {{
            "type": "single_choice",
            "question": "IaaS 代表什么？",
            "options": ["软件即服务", "平台即服务", "基础设施即服务", "数据即服务"],
            "answer": "基础设施即服务",
            "analysis": "IaaS 是 Infrastructure as a Service 的缩写，即基础设施即服务。",
            "difficulty": 1
        }},
        {{
            "type": "single_choice",
            "question": "以下哪项属于 PaaS 服务？",
            "options": ["阿里云ECS", "AWS S3", "Google App Engine", "腾讯云CVM"],
            "answer": "Google App Engine",
            "analysis": "Google App Engine 是典型的 PaaS 服务，提供应用部署平台。",
            "difficulty": 1
        }},
        {{
            "type": "essay",
            "question": "简述云计算的三种服务模式及其区别。",
            "answer": "IaaS提供基础设施，PaaS提供开发平台，SaaS提供软件应用。",
            "analysis": "IaaS让用户管理服务器，PaaS让用户管理应用，SaaS让用户直接使用软件。",
            "difficulty": 1
        }}
    ]
    """.strip()


# 解析分层级技能树模块（核心修改）
def parse_learning_modules(path_content):
    """解析DeepSeek返回的Markdown格式分层级技能树，提取模块信息"""
    modules = []
    # 匹配层级和模块
    level_pattern = re.compile(r'#\s*[🟢🟡🔴]?\s*(初级|中级|高级).*?\n(.*?)(?=#\s*[🟢🟡🔴]|$)', re.DOTALL)
    level_matches = level_pattern.findall(path_content)

    for level_match in level_matches:
        level_name = level_match[0].strip()
        level_content = level_match[1]

        # 匹配该层级下的所有模块
        module_pattern = re.compile(r'##\s*\d+\.\s*(.+?)\n(.*?)(?=##\s*\d+\.|$)', re.DOTALL)
        module_matches = module_pattern.findall(level_content)

        for module_match in module_matches:
            module_name = module_match[0].strip()
            module_details = module_match[1]

            # 提取模块各项信息
            duration_pattern = re.compile(r'预计学习时长：(\d+)小时')
            duration = duration_pattern.search(module_details).group(1) if duration_pattern.search(
                module_details) else "8"

            dependency_pattern = re.compile(r'前置依赖：(.+)')
            dependency = dependency_pattern.search(module_details).group(1).strip() if dependency_pattern.search(
                module_details) else "无"

            points_pattern = re.compile(r'核心技能点：(.+)')
            points = points_pattern.search(module_details).group(1).strip() if points_pattern.search(
                module_details) else ""

            goal_pattern = re.compile(r'学习目标：(.+)')
            goal = goal_pattern.search(module_details).group(1).strip() if goal_pattern.search(module_details) else ""

            modules.append({
                "name": module_name,
                "duration": duration,
                "dependency": dependency,
                "points": points,
                "level": level_name,
                "goal": goal
            })

    return modules


# 接口1：生成学习路径（技能树）
@app.post("/api/generate-path")
def generate_path(request: PathRequest):
    try:
        prompt = build_learning_path_prompt(request.target, request.level, request.pace, request.resource_type)
        print(f"生成的Prompt：{prompt[:200]}...")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )

        if not response.choices or not response.choices[0].message.content:
            raise Exception("DeepSeek返回的学习路径内容为空")
        path_content = response.choices[0].message.content.strip()
        print(f"AI返回的学习路径：{path_content[:200]}...")

        modules = parse_learning_modules(path_content)
        if not modules:
            raise Exception("解析学习模块失败，未提取到有效模块")
        print(f"解析出{len(modules)}个学习模块：{[m['name'] for m in modules]}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # 插入学习路径主记录
        cursor.execute('''
        INSERT INTO LEARNING_PATH (target, level, pace, resource_type, path_content)
        VALUES (?, ?, ?, ?, ?)
        ''', (request.target, request.level, request.pace, request.resource_type, path_content))

        # 获取path_id
        cursor.execute("SELECT IDENT_CURRENT('LEARNING_PATH')")
        path_id_result = cursor.fetchone()
        if not path_id_result or path_id_result[0] is None:
            raise Exception("插入学习路径后，获取path_id失败（返回空）")
        path_id = int(path_id_result[0])
        print(f"生成的path_id：{path_id}")

        # 插入模块+生成资源+练习题
        module_list = []
        for module in modules:
            cursor.execute('''
            INSERT INTO LEARNING_MODULE (path_id, module_name, estimated_hours, dependency, level, learning_goal)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (path_id, module["name"], module["duration"], module["dependency"], module["level"], module["goal"]))

            cursor.execute("SELECT IDENT_CURRENT('LEARNING_MODULE')")
            module_id = int(cursor.fetchone()[0])
            module_list.append({
                "module_name": module["name"],
                "estimated_hours": module["duration"],
                "dependency": module["dependency"],
                "module_id": module_id,
                "level": module["level"],
                "goal": module["goal"],
                "points": module["points"]
            })

            print(f"\n处理模块：{module['name']} (module_id: {module_id})")

            # 生成学习资源
            try:
                print(f"生成{module['name']}的学习资源...")
                resource_prompt = build_resource_prompt(module["name"], request.level, request.resource_type)
                resource_response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": resource_prompt}],
                    temperature=0.3
                )

                resource_content = resource_response.choices[0].message.content.strip()
                resource_content = re.sub(r'^```json|```$', '', resource_content).strip()
                resources = json.loads(resource_content)

                for res in resources:
                    cursor.execute('''
                    INSERT INTO LEARNING_RESOURCE (module_id, title, url, source, tag, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        module_id,
                        res.get("title", ""),
                        res.get("url", ""),
                        res.get("source", ""),
                        res.get("tag", ""),
                        res.get("type", "")
                    ))
                print(f"成功插入{len(resources)}个{module['name']}的学习资源")
            except Exception as e:
                print(f"生成{module['name']}资源失败：{str(e)}")

            # 生成练习题
            try:
                print(f"生成{module['name']}的练习题...")
                exercise_prompt = build_exercise_prompt(module["name"], request.level)
                exercise_response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": exercise_prompt}],
                    temperature=0.3
                )

                exercise_content = exercise_response.choices[0].message.content.strip()
                exercise_content = re.sub(r'^```json|```$', '', exercise_content).strip()
                exercises = json.loads(exercise_content)

                for ex in exercises:
                    if ex.get("type") == "single_choice":
                        question = f"{ex['question']}\n选项：{', '.join(ex['options'])}"
                        # 额外存储options用于前端展示
                        options = ','.join(ex['options'])
                    else:
                        question = ex["question"]
                        options = ""

                    cursor.execute('''
                    INSERT INTO EXERCISE (module_id, question, answer, analysis, difficulty, options)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        module_id,
                        question,
                        ex["answer"],
                        ex["analysis"],
                        ex.get("difficulty", 1),
                        options
                    ))
                print(f"成功插入{len(exercises)}个{module['name']}的练习题")
            except Exception as e:
                print(f"生成{module['name']}练习题失败：{str(e)}")

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "code": 200,
            "msg": "生成成功",
            "data": {
                "path_id": path_id,
                "path_content": path_content,
                "modules": module_list,
                "create_time": "2025-01-01 10:00:00"
            }
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print("=" * 50 + "详细报错信息" + "=" * 50)
        print(error_detail)
        print("=" * 100)
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")


# 接口2：获取学习资源
@app.get("/api/get-resources")
def get_resources(module_name: str, resource_type: str = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT module_id FROM LEARNING_MODULE WHERE module_name = ?', (module_name,))
        module_result = cursor.fetchone()
        if not module_result:
            raise HTTPException(status_code=404, detail="模块不存在")
        module_id = module_result[0]

        query = 'SELECT * FROM LEARNING_RESOURCE WHERE module_id = ?'
        params = [module_id]
        if resource_type:
            query += ' AND type = ?'
            params.append(resource_type)

        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        resources = [dict(zip(columns, row)) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return {
            "code": 200,
            "msg": "查询成功",
            "data": resources
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


# 接口3：获取练习题（含options字段）
@app.get("/api/get-exercises")
def get_exercises(module_name: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT module_id FROM LEARNING_MODULE WHERE module_name = ?', (module_name,))
        module_result = cursor.fetchone()
        if not module_result:
            raise HTTPException(status_code=404, detail="模块不存在")
        module_id = module_result[0]

        cursor.execute('SELECT * FROM EXERCISE WHERE module_id = ?', (module_id,))
        columns = [column[0] for column in cursor.description]
        exercises = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # 解析options为列表
        for ex in exercises:
            if ex.get('options'):
                ex['options'] = ex['options'].split(',')
            else:
                ex['options'] = []

        cursor.close()
        conn.close()

        return {
            "code": 200,
            "msg": "查询成功",
            "data": exercises
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


# 接口4：更新学习进度（移除progress字段）
@app.post("/api/update-progress")
def update_progress(request: ProgressRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查进度是否已存在
        cursor.execute('''
        SELECT progress_id FROM USER_PROGRESS WHERE path_id = ? AND module_name = ?
        ''', (request.path_id, request.module_name))
        progress = cursor.fetchone()

        if progress:
            # 更新进度（移除progress字段）
            cursor.execute('''
            UPDATE USER_PROGRESS SET status = ?, accuracy = ?, update_time = GETDATE()
            WHERE path_id = ? AND module_name = ?
            ''', (request.status, request.accuracy, request.path_id, request.module_name))
            progress_id = progress[0]
        else:
            # 新增进度（移除progress字段）
            cursor.execute('''
            INSERT INTO USER_PROGRESS (path_id, module_name, status, accuracy)
            VALUES (?, ?, ?, ?)
            ''', (request.path_id, request.module_name, request.status, request.accuracy))

            cursor.execute("SELECT IDENT_CURRENT('USER_PROGRESS')")
            progress_id_result = cursor.fetchone()
            if not progress_id_result or progress_id_result[0] is None:
                raise Exception("插入进度后，获取progress_id失败（返回空）")
            progress_id = int(progress_id_result[0])

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "code": 200,
            "msg": "更新成功",
            "data": {
                "progress_id": progress_id,
                "update_time": "2025-01-01 11:00:00"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")


# 接口5：提交答题记录
@app.post("/api/submit-answer")
def submit_answer(request: AnswerRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查答题记录是否存在
        cursor.execute('''
        SELECT answer_id FROM USER_ANSWER WHERE path_id = ? AND module_name = ? AND exercise_id = ?
        ''', (request.path_id, request.module_name, request.exercise_id))
        answer_record = cursor.fetchone()

        if answer_record:
            # 更新答题记录
            cursor.execute('''
            UPDATE USER_ANSWER SET user_answer = ?, is_correct = ?, submit_time = GETDATE()
            WHERE path_id = ? AND module_name = ? AND exercise_id = ?
            ''', (request.user_answer, request.is_correct, request.path_id, request.module_name, request.exercise_id))
            answer_id = answer_record[0]
        else:
            # 新增答题记录
            cursor.execute('''
            INSERT INTO USER_ANSWER (path_id, module_name, exercise_id, user_answer, is_correct)
            VALUES (?, ?, ?, ?, ?)
            ''', (request.path_id, request.module_name, request.exercise_id, request.user_answer, request.is_correct))

            cursor.execute("SELECT IDENT_CURRENT('USER_ANSWER')")
            answer_id_result = cursor.fetchone()
            if not answer_id_result or answer_id_result[0] is None:
                raise Exception("插入答题记录失败，获取answer_id失败")
            answer_id = int(answer_id_result[0])

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "code": 200,
            "msg": "答题记录提交成功",
            "data": {
                "answer_id": answer_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交答题记录失败：{str(e)}")


# 接口6：获取正确率统计（移除progress相关字段）
@app.post("/api/get-accuracy")
def get_accuracy(request: AccuracyRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.module_name:
            # 获取指定模块正确率
            cursor.execute('''
            SELECT 
                COUNT(ua.is_correct) as total, 
                SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM USER_ANSWER ua
            LEFT JOIN USER_PROGRESS up ON ua.path_id = up.path_id AND ua.module_name = up.module_name
            WHERE ua.path_id = ? AND ua.module_name = ?
            GROUP BY ua.path_id, ua.module_name
            ''', (request.path_id, request.module_name))
        else:
            # 获取总体正确率
            cursor.execute('''
            SELECT 
                COUNT(ua.is_correct) as total, 
                SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM USER_ANSWER ua
            LEFT JOIN USER_PROGRESS up ON ua.path_id = up.path_id AND ua.module_name = up.module_name
            WHERE ua.path_id = ?
            GROUP BY ua.path_id
            ''', (request.path_id,))

        result = cursor.fetchone()
        # 处理无数据的情况（默认返回0）
        total = result[0] if (result and result[0] is not None) else 0
        correct = result[1] if (result and result[1] is not None) else 0

        accuracy = (correct / total * 100) if total > 0 else 0.0

        cursor.close()
        conn.close()

        return {
            "code": 200,
            "msg": "查询成功",
            "data": {
                "total": total,
                "correct": correct,
                "accuracy": round(accuracy, 2)
            }
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print("=" * 50 + "get-accuracy报错" + "=" * 50)
        print(error_detail)
        print("=" * 100)
        raise HTTPException(status_code=500, detail=f"查询正确率失败：{str(e)}")


# 启动服务
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)