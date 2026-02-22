import pyodbc
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def get_sql_server_connection():
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
        print(f"数据库连接失败：{str(e)}")
        raise


def init_database():
    """初始化SQL Server数据表"""
    conn = get_sql_server_connection()
    cursor = conn.cursor()

    # 1. 学习路径表
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'LEARNING_PATH')
    CREATE TABLE LEARNING_PATH (
        path_id INT IDENTITY(1,1) PRIMARY KEY,
        target VARCHAR(255) NOT NULL,
        level VARCHAR(50) NOT NULL,
        pace VARCHAR(50) NOT NULL,
        resource_type VARCHAR(50) NOT NULL,
        create_time DATETIME DEFAULT GETDATE(),
        path_content VARCHAR(MAX)
    )
    ''')

    # 2. 学习模块表
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'LEARNING_MODULE')
    CREATE TABLE LEARNING_MODULE (
        module_id INT IDENTITY(1,1) PRIMARY KEY,
        path_id INT,
        module_name VARCHAR(100) NOT NULL,
        estimated_hours INT,
        dependency VARCHAR(100),
        FOREIGN KEY (path_id) REFERENCES LEARNING_PATH (path_id)
    )
    ''')

    # 3. 学习资源表
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'LEARNING_RESOURCE')
    CREATE TABLE LEARNING_RESOURCE (
        resource_id INT IDENTITY(1,1) PRIMARY KEY,
        module_id INT,
        title VARCHAR(255) NOT NULL,
        url VARCHAR(512) NOT NULL,
        source VARCHAR(50),
        tag VARCHAR(50),
        type VARCHAR(20),
        FOREIGN KEY (module_id) REFERENCES LEARNING_MODULE (module_id)
    )
    ''')

    # 4. 练习题表
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'EXERCISE')
    CREATE TABLE EXERCISE (
        exercise_id INT IDENTITY(1,1) PRIMARY KEY,
        module_id INT,
        question VARCHAR(MAX) NOT NULL,
        answer VARCHAR(MAX) NOT NULL,
        analysis VARCHAR(MAX),
        difficulty INT DEFAULT 1,
        FOREIGN KEY (module_id) REFERENCES LEARNING_MODULE (module_id)
    )
    ''')

    # 5. 学习进度表
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'USER_PROGRESS')
    CREATE TABLE USER_PROGRESS (
        progress_id INT IDENTITY(1,1) PRIMARY KEY,
        path_id INT,
        module_name VARCHAR(100) NOT NULL,
        status VARCHAR(20) DEFAULT '未开始',
        accuracy FLOAT DEFAULT 0.0,
        update_time DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (path_id) REFERENCES LEARNING_PATH (path_id)
    )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("数据库表初始化成功！")


def init_static_resources():
    """初始化静态学习资源和练习题（演示用）"""
    conn = get_sql_server_connection()
    cursor = conn.cursor()

    # 修复核心：先插入一条测试用的学习路径（生成有效的path_id）
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM LEARNING_PATH WHERE target = '测试路径')
    INSERT INTO LEARNING_PATH (target, level, pace, resource_type, path_content)
    VALUES ('测试路径', '零基础', '紧凑', '视频', '测试用学习路径')
    ''')
    # 获取这条测试路径的path_id（后续模块关联这个有效id）
    cursor.execute('SELECT path_id FROM LEARNING_PATH WHERE target = \'测试路径\'')
    test_path_id = cursor.fetchone()[0]

    # 插入测试模块（关联有效的path_id，不再用0）
    cursor.execute('''
    IF NOT EXISTS (SELECT * FROM LEARNING_MODULE WHERE module_name = 'HTML基础')
    INSERT INTO LEARNING_MODULE (path_id, module_name, estimated_hours, dependency)
    VALUES (?, ?, ?, ?)
    ''', (test_path_id, 'HTML基础', 8, '无'))

    # 获取HTML基础模块的module_id（避免硬编码1）
    cursor.execute('SELECT module_id FROM LEARNING_MODULE WHERE module_name = \'HTML基础\'')
    module_id = cursor.fetchone()[0]

    # 插入HTML基础模块的资源（用实际的module_id）
    static_resources = [
        (module_id, "B站 HTML零基础入门教程", "https://www.bilibili.com/video/BV1Kg411T7t9", "B站", "适合零基础",
         "视频"),
        (
        module_id, "MDN HTML参考文档", "https://developer.mozilla.org/zh-CN/docs/Web/HTML", "MDN", "适合零基础", "文档")
    ]
    cursor.executemany('''
    INSERT INTO LEARNING_RESOURCE (module_id, title, url, source, tag, type)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', static_resources)

    # 插入HTML基础模块的练习题（用实际的module_id）
    static_exercises = [
        (module_id, "以下哪个标签是HTML中定义段落的标签？A. <div> B. <p> C. <span>", "B",
         "<p>标签用于定义HTML中的段落，<div>是块级容器，<span>是行内容器。", 1),
        (module_id, "HTML文档的根标签是什么？", "<html>", "HTML文档的根标签是<html>，所有其他标签都嵌套在该标签内。", 1)
    ]
    cursor.executemany('''
    INSERT INTO EXERCISE (module_id, question, answer, analysis, difficulty)
    VALUES (?, ?, ?, ?, ?)
    ''', static_exercises)

    conn.commit()
    cursor.close()
    conn.close()
    print("静态资源初始化成功！")


if __name__ == "__main__":
    init_database()
    init_static_resources()