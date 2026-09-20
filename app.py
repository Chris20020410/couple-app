# -*- coding: utf-8 -*-
"""
情侣互动小应用 —— 单文件版本 (app.py)
功能：1. 密码登录  2. 任务与记账  3. 照片墙
"""

import os
from datetime import datetime

import streamlit as st
import pandas as pd
import sqlite3  # Python 自带，无需安装


# ============ 0. 页面基础设置 ============
st.set_page_config(page_title="情侣互动小应用", page_icon="❤️", layout="wide")

# 登录密码（硬编码，简单示例，不追求安全性）
PASSWORD = "520"

# 数据库文件、图片文件夹的名字
DB_NAME = "couple.db"
IMAGE_DIR = "images"
ATTACH_DIR = "attachments"  # 存任务附件（原因图片）的文件夹


# ============ 1. 数据库相关函数（用 sqlite3） ============

def init_db():
    """建表：如果数据库还不存在，就自动创建一张 tasks 表"""
    conn = sqlite3.connect(DB_NAME)  # 连接数据库（文件不存在会自动创建）
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增主键，每条记录唯一编号
            direction TEXT NOT NULL,               -- 谁欠谁：'我欠女友' 或 '女友欠我'
            content   TEXT NOT NULL,               -- 欠了什么要求/任务
            done      INTEGER DEFAULT 0,           -- 是否完成：0=未完成，1=已完成
            created_at TEXT,                       -- 创建时间
            image     TEXT                          -- 附件（原因图片）文件名，没有则为空
        )
    """)
    # 兼容旧数据库：如果表里还没有 image 列，就补上
    cols = [row[1] for row in c.execute("PRAGMA table_info(tasks)").fetchall()]
    if "image" not in cols:
        c.execute("ALTER TABLE tasks ADD COLUMN image TEXT")
    conn.commit()  # 保存改动
    conn.close()   # 关闭连接


def add_task(direction, content, image=None):
    """往数据库里新增一条任务（image 是附件图片文件名，可以没有）"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (direction, content, done, created_at, image) VALUES (?, ?, 0, ?, ?)",
        (direction, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), image),
    )
    conn.commit()
    conn.close()


def get_tasks():
    """读取所有任务，未完成的排前面、新的排前面"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM tasks ORDER BY done ASC, id DESC")
    rows = c.fetchall()  # 得到 [(id, direction, content, done, created_at), ...]
    conn.close()
    return rows


def mark_done(task_id):
    """把某条任务标记为已完成"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# ============ 2. 登录模块 ============

def login_page():
    """登录页面：输入正确密码才放行"""
    st.title("❤️ 情侣互动小应用")
    password = st.text_input("请输入密码", type="password")  # type="password" 让输入显示成圆点
    if st.button("登录"):
        if password == PASSWORD:
            st.session_state.logged_in = True  # 记录登录状态
            st.rerun()                          # 重新运行，刷新页面进入主界面
        else:
            st.error("密码错误，请重试！")


# ============ 3. 任务与记账模块 ============

def tasks_page():
    init_db()  # 先确保数据库/表存在
    st.header("📋 任务与记账")

    # ---- 3.1 添加记录的表单 ----
    with st.form("add_form", clear_on_submit=True):  # clear_on_submit：提交后自动清空输入框
        direction = st.selectbox("谁欠谁", ["我欠女友", "女友欠我"])
        content = st.text_input("欠了什么要求 / 任务")
        reason_img = st.file_uploader(  # 可选：上传一张“原因图片”作为附件
            "上传原因图片（可选）",
            type=["png", "jpg", "jpeg", "gif", "webp"],
        )
        submitted = st.form_submit_button("提交")

    if submitted:                     # 表单提交后（在 with 外判断更稳）
        if content.strip():           # 判断内容不为空
            image_name = None
            if reason_img is not None:
                os.makedirs(ATTACH_DIR, exist_ok=True)  # 确保附件文件夹存在
                ext = os.path.splitext(reason_img.name)[1]  # 取出文件后缀，如 .jpg
                image_name = datetime.now().strftime("%Y%m%d%H%M%S%f") + ext  # 用时间戳命名，避免重名
                with open(os.path.join(ATTACH_DIR, image_name), "wb") as f_out:
                    f_out.write(reason_img.getbuffer())  # 把图片保存到磁盘
            add_task(direction, content.strip(), image_name)
            st.success("已添加记录！")
            st.rerun()
        else:
            st.error("请先输入任务内容～")

    # ---- 3.2 用表格展示所有记录 ----
    st.subheader("记录列表")
    rows = get_tasks()

    if rows:
        # 转成 pandas 表格，方便 st.dataframe 展示；顺便把 done 换成看得懂的文字
        df = pd.DataFrame(rows, columns=["ID", "谁欠谁", "任务/要求", "状态", "创建时间", "附件"])
        df["状态"] = df["状态"].apply(lambda x: "✅ 已完成" if x == 1 else "⏳ 未完成")
        df["附件"] = df["附件"].apply(lambda x: "📎 有附件" if x else "无")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ---- 3.3 标记完成：用一个下拉框选一条未完成的记录 ----
        incomplete = [r for r in rows if r[3] == 0]  # r[3] 是 done 字段
        if incomplete:
            st.subheader("标记完成")
            # 下拉框显示成好读的文字，选中后拿到对应的 id
            option_map = {f"#{r[0]} ｜ {r[1]} ｜ {r[2]}": r[0] for r in incomplete}
            choice = st.selectbox("选择要标记为完成的记录", list(option_map.keys()))
            if st.button("标记完成"):
                mark_done(option_map[choice])
                st.success("已标记完成！")
                st.rerun()

        # ---- 3.4 附件预览：有原因图片的记录，在下面显示缩略图 ----
        with_img = [r for r in rows if r[5]]  # r[5] 是 image 字段，有值才显示
        if with_img:
            st.subheader("附件预览")
            cols = st.columns(3)
            for i, r in enumerate(with_img):
                path = os.path.join(ATTACH_DIR, r[5])
                with cols[i % 3]:
                    if os.path.exists(path):
                        st.image(path, caption=f"#{r[0]} {r[2]}", use_container_width=True)
                    else:
                        st.caption(f"#{r[0]} {r[2]}（附件文件缺失）")
    else:
        st.info("还没有记录，先在上面添加一条吧～")


# ============ 4. 照片墙模块 ============

def photos_page():
    st.header("🖼️ 照片墙")

    # 确保 images 文件夹存在（不存在就自动创建）
    os.makedirs(IMAGE_DIR, exist_ok=True)

    # ---- 4.1 上传图片 ----
    uploaded = st.file_uploader(
        "上传照片",
        type=["png", "jpg", "jpeg", "gif"],
        accept_multiple_files=True,  # 允许一次上传多张
    )
    if uploaded:
        for f in uploaded:
            save_path = os.path.join(IMAGE_DIR, f.name)
            with open(save_path, "wb") as f_out:  # 以二进制写入，保存图片
                f_out.write(f.getbuffer())
        st.success("上传成功！")
        st.rerun()

    # ---- 4.2 展示已有照片 ----
    st.subheader("我们的回忆")
    files = sorted(os.listdir(IMAGE_DIR))  # 列出 images 文件夹里所有文件
    if files:
        cols = st.columns(3)               # 每行放 3 张
        for i, name in enumerate(files):
            path = os.path.join(IMAGE_DIR, name)
            with cols[i % 3]:
                st.image(path, caption=name, use_container_width=True)
    else:
        st.info("还没有照片，上传一张开启回忆吧～")


# ============ 5. 主流程 ============

def main():
    # 用 session_state 记住登录状态（刷新页面不会丢）
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()  # 没登录 → 显示登录页
    else:
        # 侧边栏导航
        st.sidebar.title("❤️ 情侣小应用")
        menu = st.sidebar.radio(
            "导航",
            ["🏠 首页", "📋 任务与记账", "🖼️ 照片墙"],
        )

        # 侧边栏加一个退出登录按钮
        if st.sidebar.button("退出登录"):
            st.session_state.logged_in = False
            st.rerun()

        # 根据选择的菜单显示对应页面
        if menu == "🏠 首页":
            st.title("欢迎来到我们的小天地 ❤️")
            st.write("请在左侧选择「任务与记账」或「照片墙」开始使用～")
        elif menu == "📋 任务与记账":
            tasks_page()
        elif menu == "🖼️ 照片墙":
            photos_page()


if __name__ == "__main__":
    main()
