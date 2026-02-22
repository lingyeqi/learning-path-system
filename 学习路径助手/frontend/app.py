import streamlit as st
import requests
import os
from dotenv import load_dotenv
import pyodbc
import pandas as pd

# 加载环境变量
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# 页面配置
st.set_page_config(
    page_title="LearnPath 学习路径助手",
    page_icon="📚",
    layout="wide"
)

# 自定义CSS美化样式（移除进度相关样式，保留其他优化）
st.markdown("""
<style>
/* 整体样式 */
.main {
    padding: 2rem;
}
/* 卡片样式 */
.stExpander {
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
    border: 1px solid #e9ecef;
}
/* 层级标签样式 */
.level-tag {
    display: inline-block;
    padding: 0.2rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: bold;
    margin-right: 0.5rem;
}
.level-primary {
    background-color: #d4edda;
    color: #155724;
}
.level-intermediate {
    background-color: #fff3cd;
    color: #856404;
}
.level-advanced {
    background-color: #f8d7da;
    color: #721c24;
}
/* 按钮样式（文字换行+宽度限制） */
.stButton > button {
    border-radius: 8px;
    height: 2.5rem;
    font-weight: bold;
    white-space: normal !important;  /* 允许按钮文字换行 */
    padding: 0.5rem 1rem;          /* 增加内边距 */
    width: 100%;
    word-wrap: break-word;         /* 长文字换行 */
}
/* 标题样式 */
h1, h2, h3, h5 {
    color: #2c3e50;
    margin-bottom: 0.5rem;
}
/* 数据卡片 */
.metric-card {
    background-color: #f8f9fa;
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    margin-bottom: 1rem;
}
/* 修复expander内边距（避免文字贴边） */
.stExpanderContent {
    padding: 1.2rem;  /* 增加内边距 */
}
/* 优化文字行高和溢出（长文本换行） */
p {
    line-height: 1.8;     /* 增加行高 */
    word-wrap: break-word; /* 长文本自动换行 */
    word-break: break-all;
    margin-bottom: 0.6rem !important;
}
/* 分栏间距优化 */
.stColumn {
    padding: 0 0.8rem;
}
/* 容器边框美化（内边距+圆角） */
div[data-testid="stVerticalBlock"] > div[style*="border: 1px solid rgb(221, 221, 221);"] {
    border-radius: 8px;
    margin-bottom: 0.8rem;
    padding: 0.8rem;  /* 容器内边距，文字不贴边 */
}
/* 技能点容器（强制换行） */
.skill-points {
    white-space: pre-wrap;  /* 保留换行符 */
    line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

# 初始化会话状态（移除所有进度相关字段）
if "path_id" not in st.session_state:
    st.session_state.path_id = None
if "modules" not in st.session_state:
    st.session_state.modules = []
if "selected_module" not in st.session_state:
    st.session_state.selected_module = None
if "resources" not in st.session_state:
    st.session_state.resources = []
if "exercises" not in st.session_state:
    st.session_state.exercises = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "学习需求"
if "module_accuracy" not in st.session_state:
    st.session_state.module_accuracy = 0.0
if "total_accuracy" not in st.session_state:
    st.session_state.total_accuracy = 0.0
if "level_groups" not in st.session_state:
    st.session_state.level_groups = {}

# 定义导航栏
tabs = ["学习需求", "可视化", "学习资源与练习", "学习进度统计"]
st.session_state.current_tab = st.sidebar.radio("导航菜单", tabs, index=tabs.index(st.session_state.current_tab))

# 页面标题
st.title("📚 LearnPath 个性化学习规划助手")

# ====================== 标签1：学习需求 ======================
if st.session_state.current_tab == "学习需求":
    st.header("📝 填写你的学习需求")
    with st.form(key="path_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            target = st.text_area(
                "学习目标",
                placeholder="例如：3个月掌握Web前端基础、精通Python数据分析等",
                height=80
            )
            level = st.selectbox("当前水平", ["零基础", "入门级", "进阶级"])
        with col2:
            pace = st.selectbox("学习节奏", ["紧凑", "宽松"])
            resource_type = st.selectbox("资源类型偏好", ["视频", "文档", "视频+文档"])

        submit_btn = st.form_submit_button("生成分层级技能", type="primary")

    if submit_btn and target:
        with st.spinner("🎯 正在生成分层级技能（包含初级→中级→高级），请耐心等待...（预计需要3-5分钟）"):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/generate-path",
                    json={
                        "target": target,
                        "level": level,
                        "pace": pace,
                        "resource_type": resource_type
                    },
                    timeout=300
                )
                response.raise_for_status()
                result = response.json()

                st.session_state.path_id = result["data"]["path_id"]
                st.session_state.modules = result["data"]["modules"]

                level_groups = {}
                for module in result["data"]["modules"]:
                    if module["level"] not in level_groups:
                        level_groups[module["level"]] = []
                    level_groups[module["level"]].append(module)
                st.session_state.level_groups = level_groups

                if result["data"]["modules"]:
                    st.session_state.selected_module = result["data"]["modules"][0]["module_name"]

                st.success("✅ 分层级技能生成成功！请切换到「可视化」查看详情")
            except requests.exceptions.Timeout:
                st.error("⚠️ 请求超时！后端可能仍在生成，请等待1分钟后刷新页面。")
            except requests.exceptions.ConnectionError:
                st.error("❌ 连接失败！请检查后端服务是否启动。")
            except Exception as e:
                st.error(f"❌ 生成失败：{str(e)}")
    elif submit_btn and not target:
        st.warning("⚠️ 请填写学习目标！")

# ====================== 标签2：可视化（移除所有进度相关内容） ======================
elif st.session_state.current_tab == "可视化":
    st.header("🌳 分层级技能可视化")
    if st.session_state.path_id:
        try:
            conn = pyodbc.connect(
                f"DRIVER={os.getenv('SQL_SERVER_DRIVER')};"
                f"SERVER={os.getenv('SQL_SERVER_SERVER')};"
                f"DATABASE={os.getenv('SQL_SERVER_DATABASE')};"
                f"Trusted_Connection=yes;"
            )
            cursor = conn.cursor()
            cursor.execute('SELECT path_content FROM LEARNING_PATH WHERE path_id = ?', (st.session_state.path_id,))
            path_content = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            st.subheader("🎯 你的个性化分层级技能")

            # 初级模块（移除进度相关内容）
            if "初级" in st.session_state.level_groups:
                st.markdown("### 🟢 初级（基础入门）")
                with st.container(border=True):
                    for module in st.session_state.level_groups["初级"]:
                        expander_title = f"<span class='level-tag level-primary'>初级</span> {module['module_name']}"
                        with st.expander("", expanded=True):
                            col_content = st.columns([5])[0]  # 移除进度列，只保留内容列
                            with col_content:
                                st.markdown(f"<h5>{expander_title}</h5>", unsafe_allow_html=True)
                                # 带内边距的容器，文字不贴边
                                with st.container(border=True):
                                    st.write(f"**预计学习时长**：{module['estimated_hours']} 小时")
                                with st.container(border=True):
                                    st.write(f"**前置依赖**：{module['dependency']}")
                                with st.container(border=True):
                                    # 核心优化：用HTML容器强制换行，长文本自动折行
                                    skill_points = module['points'].replace('、', '、<br>')  # 技能点换行
                                    st.markdown(f"<div class='skill-points'>**核心技能点**：{skill_points}</div>",
                                                unsafe_allow_html=True)
                                with st.container(border=True):
                                    st.write(f"**学习目标**：{module['goal']}")
                            # 移除进度相关内容，保留学习按钮（仅切换标签）
                            if st.button(f"开始学习 {module['module_name']}", key=f"start_{module['module_id']}"):
                                st.session_state.current_tab = "学习资源与练习"
                                st.session_state.selected_module = module["module_name"]
                                st.rerun()

            # 中级模块（移除进度相关内容）
            if "中级" in st.session_state.level_groups:
                st.markdown("### 🟡 中级（进阶核心）")
                with st.container(border=True):
                    for module in st.session_state.level_groups["中级"]:
                        expander_title = f"<span class='level-tag level-intermediate'>中级</span> {module['module_name']}"
                        with st.expander("", expanded=False):
                            col_content = st.columns([5])[0]
                            with col_content:
                                st.markdown(f"<h5>{expander_title}</h5>", unsafe_allow_html=True)
                                with st.container(border=True):
                                    st.write(f"**预计学习时长**：{module['estimated_hours']} 小时")
                                with st.container(border=True):
                                    st.write(f"**前置依赖**：{module['dependency']}")
                                with st.container(border=True):
                                    skill_points = module['points'].replace('、', '、<br>')
                                    st.markdown(f"<div class='skill-points'>**核心技能点**：{skill_points}</div>",
                                                unsafe_allow_html=True)
                                with st.container(border=True):
                                    st.write(f"**学习目标**：{module['goal']}")
                            if st.button(f"开始学习 {module['module_name']}", key=f"start_{module['module_id']}"):
                                st.session_state.current_tab = "学习资源与练习"
                                st.session_state.selected_module = module["module_name"]
                                st.rerun()

            # 高级模块（移除进度相关内容）
            if "高级" in st.session_state.level_groups:
                st.markdown("### 🔴 高级（实战拔高）")
                with st.container(border=True):
                    for module in st.session_state.level_groups["高级"]:
                        expander_title = f"<span class='level-tag level-advanced'>高级</span> {module['module_name']}"
                        with st.expander("", expanded=False):
                            col_content = st.columns([5])[0]
                            with col_content:
                                st.markdown(f"<h5>{expander_title}</h5>", unsafe_allow_html=True)
                                with st.container(border=True):
                                    st.write(f"**预计学习时长**：{module['estimated_hours']} 小时")
                                with st.container(border=True):
                                    st.write(f"**前置依赖**：{module['dependency']}")
                                with st.container(border=True):
                                    skill_points = module['points'].replace('、', '、<br>')
                                    st.markdown(f"<div class='skill-points'>**核心技能点**：{skill_points}</div>",
                                                unsafe_allow_html=True)
                                with st.container(border=True):
                                    st.write(f"**学习目标**：{module['goal']}")
                            if st.button(f"开始学习 {module['module_name']}", key=f"start_{module['module_id']}"):
                                st.session_state.current_tab = "学习资源与练习"
                                st.session_state.selected_module = module["module_name"]
                                st.rerun()

            # 技能总览表格（移除进度列）
            st.subheader("📋 技能总览")
            module_data = []
            for module in st.session_state.modules:
                module_data.append({
                    "模块名称": module["module_name"],
                    "所属层级": module["level"],
                    "预计时长(小时)": module["estimated_hours"],
                    "前置依赖": module["dependency"],
                    "学习目标": module["goal"][:30] + "..." if len(module["goal"]) > 30 else module["goal"]
                })

            df = pd.DataFrame(module_data)

            def color_level(val):
                if val == "初级":
                    return 'background-color: #d4edda; color: #155724'
                elif val == "中级":
                    return 'background-color: #fff3cd; color: #856404'
                elif val == "高级":
                    return 'background-color: #f8d7da; color: #721c24'
                return ''

            st.dataframe(
                df.style.applymap(color_level, subset=["所属层级"]),
                use_container_width=True,
                hide_index=True
            )

        except Exception as e:
            st.error(f"获取技能失败：{str(e)}")
    else:
        st.info("💡 请先在「学习需求」标签页生成技能")

# ====================== 标签3：学习资源与练习（移除进度同步相关内容） ======================
elif st.session_state.current_tab == "学习资源与练习":
    st.header("📖 学习资源与练习")
    if st.session_state.modules:
        st.subheader("选择学习模块")
        level_tabs = st.tabs(["初级", "中级", "高级"])

        # 初级模块选择
        with level_tabs[0]:
            if "初级" in st.session_state.level_groups:
                primary_modules = [m["module_name"] for m in st.session_state.level_groups["初级"]]
                if primary_modules:
                    selected = st.selectbox("初级模块", primary_modules, key="primary_select")
                    if st.button("选择该模块", key="primary_btn"):
                        st.session_state.selected_module = selected

        # 中级模块选择
        with level_tabs[1]:
            if "中级" in st.session_state.level_groups:
                intermediate_modules = [m["module_name"] for m in st.session_state.level_groups["中级"]]
                if intermediate_modules:
                    selected = st.selectbox("中级模块", intermediate_modules, key="intermediate_select")
                    if st.button("选择该模块", key="intermediate_btn"):
                        st.session_state.selected_module = selected

        # 高级模块选择
        with level_tabs[2]:
            if "高级" in st.session_state.level_groups:
                advanced_modules = [m["module_name"] for m in st.session_state.level_groups["高级"]]
                if advanced_modules:
                    selected = st.selectbox("高级模块", advanced_modules, key="advanced_select")
                    if st.button("选择该模块", key="advanced_btn"):
                        st.session_state.selected_module = selected

        # 显示当前选中模块（移除进度展示）
        if st.session_state.selected_module:
            st.markdown(f"""
            <div class="metric-card">
                <h4>当前选中模块：{st.session_state.selected_module}</h4>
            </div>
            """, unsafe_allow_html=True)

            selected_module = st.session_state.selected_module

            # 分割资源和练习
            tab1, tab2 = st.tabs(["📚 学习资源", "✏️ 练习题"])

            # 学习资源标签
            with tab1:
                try:
                    res_response = requests.get(
                        f"{BACKEND_URL}/api/get-resources",
                        params={"module_name": selected_module},
                        timeout=30
                    )
                    if res_response.status_code == 200:
                        st.session_state.resources = res_response.json()["data"]
                        st.subheader("推荐学习资源")
                        if st.session_state.resources:
                            for idx, res in enumerate(st.session_state.resources):
                                with st.expander("", expanded=True):
                                    st.markdown(f"<h5>📌 {res['title']}</h5>", unsafe_allow_html=True)
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.write(f"**来源平台**：{res['source']}")
                                        st.write(f"**资源类型**：{res['type']}")
                                        st.write(f"**适配标签**：{res['tag']}")
                                        st.markdown(f"[🔗 点击访问资源]({res['url']})")
                                    with col2:
                                        if res['type'] == "视频":
                                            st.markdown(
                                                '<div style="background-color: #e8f4fd; padding: 1rem; border-radius: 8px; text-align: center;">📹 视频资源</div>',
                                                unsafe_allow_html=True)
                                        else:
                                            st.markdown(
                                                '<div style="background-color: #f0f8fb; padding: 1rem; border-radius: 8px; text-align: center;">📄 文档资源</div>',
                                                unsafe_allow_html=True)
                                st.divider()
                        else:
                            st.info("该模块暂无推荐资源～")
                except Exception as e:
                    st.warning(f"获取资源失败：{str(e)}")

            # 练习题标签（移除进度更新逻辑，仅保留答题和正确率统计）
            with tab2:
                try:
                    ex_response = requests.get(
                        f"{BACKEND_URL}/api/get-exercises",
                        params={"module_name": selected_module},
                        timeout=30
                    )
                    if ex_response.status_code == 200:
                        st.session_state.exercises = ex_response.json()["data"]
                        st.subheader("练习题（3单选+1问答）")

                        if st.session_state.exercises:
                            # 提交答题按钮
                            col_submit, col_reset = st.columns([8, 2])
                            with col_submit:
                                submit_answers_btn = st.button("📤 提交所有答案", type="primary")
                            with col_reset:
                                if st.button("🔄 重置答案"):
                                    st.session_state.user_answers = {}
                                    st.rerun()

                            # 遍历展示题目
                            for idx, ex in enumerate(st.session_state.exercises):
                                st.markdown(f"""
                                <div class="metric-card">
                                    <h5>题目{idx + 1}：{ex['question'].split('选项：')[0]}</h5>
                                </div>
                                """, unsafe_allow_html=True)

                                # 区分单选题和问答题
                                if ex.get('options'):
                                    options = ex['options']
                                    key = f"q_{ex['exercise_id']}"
                                    if key not in st.session_state.user_answers:
                                        st.session_state.user_answers[key] = None
                                    selected_option = st.radio(
                                        "请选择答案：",
                                        options,
                                        key=key,
                                        index=None if st.session_state.user_answers[key] is None else options.index(
                                            st.session_state.user_answers[key])
                                    )
                                    if selected_option is not None:
                                        st.session_state.user_answers[key] = selected_option
                                    with st.expander("📖 查看答案与解析"):
                                        st.write(f"**正确答案**：{ex['answer']}")
                                        st.write(f"**解析**：{ex['analysis']}")
                                else:
                                    key = f"q_{ex['exercise_id']}"
                                    if key not in st.session_state.user_answers:
                                        st.session_state.user_answers[key] = ""
                                    user_answer = st.text_area(
                                        "请输入答案：",
                                        value=st.session_state.user_answers[key],
                                        key=key,
                                        height=100
                                    )
                                    st.session_state.user_answers[key] = user_answer
                                    with st.expander("📖 查看答案与解析"):
                                        st.write(f"**参考答案**：{ex['answer']}")
                                        st.write(f"**解析**：{ex['analysis']}")

                                st.divider()

                            # 提交答案逻辑（仅保留答题记录提交和正确率计算，移除进度更新）
                            if submit_answers_btn:
                                correct_count = 0
                                total_count = len(st.session_state.exercises)
                                for ex in st.session_state.exercises:
                                    key = f"q_{ex['exercise_id']}"
                                    user_answer = st.session_state.user_answers.get(key, "")
                                    is_correct = False
                                    if ex.get('options'):
                                        is_correct = (user_answer == ex['answer'])
                                    else:
                                        is_correct = ex['answer'].lower() in user_answer.lower()
                                    # 提交答题记录
                                    try:
                                        requests.post(
                                            f"{BACKEND_URL}/api/submit-answer",
                                            json={
                                                "path_id": st.session_state.path_id,
                                                "module_name": selected_module,
                                                "exercise_id": ex['exercise_id'],
                                                "user_answer": user_answer,
                                                "is_correct": is_correct
                                            },
                                            timeout=10
                                        )
                                    except Exception as e:
                                        st.warning(f"提交题目{ex['exercise_id']}答案失败：{str(e)}")
                                    if is_correct:
                                        correct_count += 1

                                # 计算正确率（移除进度更新）
                                module_accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0.0
                                st.session_state.module_accuracy = module_accuracy

                                # 美化展示（仅显示正确率，移除进度）
                                st.markdown(f"""
                                <div class="metric-card">
                                    <h3>✅ 答案提交成功！</h3>
                                    <p>本模块正确率：<strong>{module_accuracy:.2f}%</strong></p>
                                    <p>答对：{correct_count} / 总题数：{total_count}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                st.progress(module_accuracy / 100, text=f"正确率：{module_accuracy:.1f}%")
                    else:
                        st.info("该模块暂无练习题～")
                except Exception as e:
                    st.warning(f"获取练习题失败：{str(e)}")
    else:
        st.info("💡 请先在「学习需求」标签页生成技能")

# ====================== 标签4：学习进度统计（移除所有进度相关内容，仅保留正确率） ======================
elif st.session_state.current_tab == "学习进度统计":
    st.header("📊 学习正确率统计")
    if st.session_state.path_id:
        col1, col2 = st.columns(2)
        with col1:
            selected_module = st.selectbox(
                "选择模块查看正确率",
                ["总体"] + [m["module_name"] for m in st.session_state.modules]
            )

        try:
            # 调用后端接口获取正确率（移除进度相关字段）
            if selected_module == "总体":
                response = requests.post(
                    f"{BACKEND_URL}/api/get-accuracy",
                    json={"path_id": st.session_state.path_id},
                    timeout=10
                )
                response.raise_for_status()
                st.subheader("📈 总体学习正确率")
            else:
                response = requests.post(
                    f"{BACKEND_URL}/api/get-accuracy",
                    json={"path_id": st.session_state.path_id, "module_name": selected_module},
                    timeout=10
                )
                response.raise_for_status()
                st.subheader(f"📈 {selected_module} - 模块正确率")

            data = response.json()["data"]
            # 美化展示（仅保留正确率，移除进度）
            st.markdown(f"""
            <div class="metric-card">
                <h4>正确率：{data['accuracy']}%</h4>
                <p>答对：{data['correct']} 题 / 总题数：{data['total']} 题</p>
            </div>
            """, unsafe_allow_html=True)

            # 正确率进度条（仅展示正确率，非学习进度）
            st.progress(data["accuracy"] / 100, text=f"正确率：{data['accuracy']:.1f}%")

            # 各模块正确率列表（移除进度）
            if selected_module == "总体":
                st.subheader("📋 各模块正确率详情")
                for level_name in ["初级", "中级", "高级"]:
                    if level_name in st.session_state.level_groups:
                        st.markdown(f"### {level_name}模块正确率")
                        cols = st.columns(2)
                        col_idx = 0
                        for module in st.session_state.level_groups[level_name]:
                            with cols[col_idx]:
                                try:
                                    module_response = requests.post(
                                        f"{BACKEND_URL}/api/get-accuracy",
                                        json={"path_id": st.session_state.path_id,
                                              "module_name": module['module_name']},
                                        timeout=10
                                    )
                                    module_response.raise_for_status()
                                    module_data = module_response.json()["data"]
                                    st.markdown(f"""
                                    <div class="metric-card">
                                        <h5>{module['module_name']}</h5>
                                        <p>正确率：{module_data['accuracy']}%</p>
                                        <p>答对：{module_data['correct']} / 总题数：{module_data['total']}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    st.progress(module_data['accuracy'] / 100, text=f"{module_data['accuracy']:.1f}%")
                                except:
                                    # 接口调用失败时显示默认数据
                                    st.markdown(f"""
                                    <div class="metric-card">
                                        <h5>{module['module_name']}</h5>
                                        <p>正确率：0%</p>
                                        <p>答对：0 / 总题数：0</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    st.progress(0)
                            col_idx = 1 - col_idx
        except Exception as e:
            # 接口调用失败时显示友好提示
            st.warning(f"获取正确率数据失败：{str(e)}，当前显示默认数据")
            # 显示默认空数据
            st.markdown(f"""
            <div class="metric-card">
                <h4>正确率：0%</h4>
                <p>答对：0 题 / 总题数：0 题</p>
            </div>
            """, unsafe_allow_html=True)
            st.progress(0)
    else:
        st.info("💡 请先在「学习需求」标签页生成技能")