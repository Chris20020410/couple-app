# -*- coding: utf-8 -*-
"""
Jessie&Chris —— 单文件版本 (app.py)
功能：1. 密码登录  2. 任务与记账  3. 照片墙
"""

import os
import random
import time
from datetime import datetime

import streamlit as st
import pandas as pd
import sqlite3  # Python 自带，无需安装


# ============ 0. 页面基础设置 ============
st.set_page_config(page_title="Jessie&Chris", page_icon="❤️", layout="wide")

# 登录密码（硬编码，简单示例，不追求安全性）
PASSWORD = "520"

# 数据库文件、图片文件夹的名字
DB_NAME = "couple.db"
IMAGE_DIR = "images"
ATTACH_DIR = "attachments"  # 存任务附件（原因图片）的文件夹


# ============ 1. 数据库相关函数（用 sqlite3） ============

def init_db():
    """建表：自动创建 tasks（任务）和 wishlist（心愿单）两张表"""
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

    # 心愿单表：存大家的礼物心愿
    c.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增主键
            name     TEXT NOT NULL,                -- 心愿名称
            budget   TEXT,                         -- 预算（可以写 "1000 元" 这种）
            note     TEXT,                         -- 详情备注（款式/规格等）
            proposer TEXT NOT NULL,                -- 提出人：Jessie 或 Chris
            status   INTEGER DEFAULT 0,            -- 状态：0=未认领，1=已认领
            created_at TEXT                        -- 提出时间
        )
    """)

    # 出行计划表：存行程标题和日程安排
    c.execute("""
        CREATE TABLE IF NOT EXISTS travel_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增主键
            title      TEXT NOT NULL,              -- 行程标题
            details    TEXT,                       -- 日程安排（大段纯文本）
            created_at TEXT                        -- 创建时间
        )
    """)
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


def add_wish(name, budget, note, proposer):
    """往心愿单里新增一条心愿"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO wishlist (name, budget, note, proposer, status, created_at) VALUES (?, ?, ?, ?, 0, ?)",
        (name, budget, note, proposer, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_wishes():
    """读取所有心愿，未认领的排前面、新的排前面"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM wishlist ORDER BY status ASC, id DESC")
    rows = c.fetchall()  # 得到 [(id, name, budget, note, proposer, status, created_at), ...]
    conn.close()
    return rows


def claim_wish(wish_id):
    """把某条心愿标记为已认领"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE wishlist SET status = 1 WHERE id = ?", (wish_id,))
    conn.commit()
    conn.close()


def add_travel_plan(title, details):
    """往出行计划里新增一条行程"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO travel_plans (title, details, created_at) VALUES (?, ?, ?)",
        (title, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_travel_plans():
    """读取所有行程，新的排前面"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM travel_plans ORDER BY id DESC")
    rows = c.fetchall()  # 得到 [(id, title, details, created_at), ...]
    conn.close()
    return rows


def delete_travel_plan(plan_id):
    """把某条行程从数据库删除（结束归档）"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM travel_plans WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()


# ============ 2. 登录模块 ============

def login_page():
    """登录页面：输入正确密码才放行"""
    st.title("❤️ Jessie&Chris")
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


# ============ 5. 专属数据大屏模块 ============

def dashboard_page():
    """数据大屏：展示两人任务对比、本月新增等统计"""
    init_db()  # 先确保数据库/表存在

    # ---- 顶部横幅（渐变标题，科技感 + 温馨感）----
    st.markdown(
        """
        <div style="background:linear-gradient(90deg,#ff758c,#ff7eb3,#a18cd1);
                    padding:16px 24px;border-radius:14px;color:#ffffff;
                    font-size:22px;font-weight:bold;text-align:center;">
        💕 Jessie & Chris 的专属数据大屏
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- 随机一句情话（每次刷新都不一样）----
    love_quotes = [
        "遇见你之后，我的世界才变得完整 ❤️",
        "你是我所有计划里，唯一的例外。",
        "和你在一起的每一天，都是情人节。",
        "世界那么大，我只想和你虚度时光。",
        "谢谢你来到我身边，让我想成为更好的人。",
    ]
    st.markdown(f"### 💌 {random.choice(love_quotes)}")

    rows = get_tasks()  # 读取所有任务

    if not rows:
        st.info("还没有数据，先到「任务与记账」添加几条吧～")
        return

    # 转成 DataFrame，方便统计
    df = pd.DataFrame(rows, columns=["ID", "谁欠谁", "任务/要求", "状态", "创建时间", "附件"])
    df["状态"] = df["状态"].apply(lambda x: "已完成" if x == 1 else "未完成")

    # ---- 指标卡片：本月新增 / 总任务 / 已完成 ----
    this_month = datetime.now().strftime("%Y-%m")  # 例如 "2026-09"
    month_count = sum(1 for r in rows if r[4] and r[4].startswith(this_month))
    done_count = int((df["状态"] == "已完成").sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("本月新增任务", month_count)
    c2.metric("任务总数", len(df))
    c3.metric("已完成", done_count, f"{done_count/len(df)*100:.0f}% 完成率")

    # ---- 图表：两人各自 已完成 / 未完成 数量对比 ----
    st.subheader("我们俩的任务对比")
    summary = df.groupby(["谁欠谁", "状态"]).size().unstack(fill_value=0)
    # 保证「已完成」「未完成」两列都存在，缺了就补 0
    for col in ["已完成", "未完成"]:
        if col not in summary.columns:
            summary[col] = 0
    summary = summary[["已完成", "未完成"]]
    st.bar_chart(summary)


# ============ 6. 礼物与心愿单模块 ============

def wishlist_page():
    """礼物与心愿单：许愿、展示心愿、认领买单"""
    init_db()  # 先确保数据库/表存在
    st.header("🎁 礼物与心愿单")

    # 认领成功后触发气球动画（用 session_state 标记，避免被 rerun 冲掉）
    if st.session_state.get("celebrate"):
        st.balloons()
        st.session_state.celebrate = False

    # ---- 6.1 许愿表单 ----
    with st.form("wish_form", clear_on_submit=True):
        proposer = st.selectbox("这是谁的心愿", ["Jessie", "Chris"])
        name = st.text_input("心愿名称", placeholder="例如：汪苏泷演唱会门票")
        budget = st.text_input("预算（可选）", placeholder="例如：1000 元")
        note = st.text_input("详情备注（款式 / 规格，可选）", placeholder="例如：内场票、粉色款式")
        submitted = st.form_submit_button("许下心愿 ✨")

    if submitted:
        if name.strip():          # 心愿名称不能为空
            add_wish(name.strip(), budget.strip(), note.strip(), proposer)
            st.success("心愿已许下！")
            st.rerun()
        else:
            st.error("请先填写心愿名称～")

    # ---- 6.2 用卡片展示所有心愿 ----
    st.subheader("我们的心愿清单")
    wishes = get_wishes()

    if not wishes:
        st.info("还没有心愿，快来许下第一个吧～")
        return

    cols = st.columns(3)  # 每行放 3 个心愿卡片
    for i, w in enumerate(wishes):
        w_id, name, budget, note, proposer, status, _ = w
        claimed = status == 1
        with cols[i % 3]:
            with st.container(border=True):  # 圆角卡片
                st.markdown(f"### {name}")
                st.caption(f"👤 {proposer} 的心愿")
                if budget:
                    st.caption(f"💰 预算：{budget}")
                if note:
                    st.caption(f"📝 {note}")
                if claimed:
                    st.success("✅ 已认领")
                else:
                    if st.button("我来买单 💳", key=f"claim_{w_id}"):
                        claim_wish(w_id)
                        st.session_state.celebrate = True  # 标记要放气球
                        st.rerun()


# ============ 7. 随机选择器模块 ============

def picker_page():
    """随机选择器：解决今天吃什么、周末去哪玩"""
    st.header("🎲 随机选择器")

    st.write("把备选方案用逗号隔开，交给命运决定吧～")

    # ---- 7.1 输入备选方案 ----
    options_text = st.text_area(
        "备选方案（用逗号分隔）",
        value="去打板球, 骑行绿道, 宅家看剧",  # 默认预填的示例
        height=120,
    )

    # ---- 7.2 醒目的随机抽取按钮 ----
    if st.button("🎯 听天由命 (随机抽取)", type="primary", use_container_width=True):
        items = [x.strip() for x in options_text.split(",") if x.strip()]  # 拆成一个个方案
        if not items:
            st.error("请先输入至少一个备选方案～")
        else:
            with st.spinner("命运的齿轮开始转动..."):
                time.sleep(1.5)  # 制造 1-2 秒的悬念
            result = random.choice(items)
            st.success(f"### 🎉 就决定是你啦：**{result}**")


# ============ 8. 出行计划模块 ============

def travel_page():
    """出行计划：录入行程、用折叠面板展示、结束后归档删除"""
    init_db()  # 先确保数据库/表存在
    st.header("🗺️ 出行计划")

    # ---- 8.1 录入表单 ----
    with st.form("travel_form", clear_on_submit=True):
        title = st.text_input("行程标题", placeholder="例如：周末露营")
        details = st.text_area(  # 多行文本框，方便粘贴大段行程安排
            "日程安排",
            placeholder="带什么装备、时间表等，直接打字或粘贴到这里...",
            height=200,
        )
        submitted = st.form_submit_button("保存行程 ✈️")

    if submitted:
        if title.strip():          # 标题不能为空
            add_travel_plan(title.strip(), details.strip())
            st.success("行程已保存！")
            st.rerun()
        else:
            st.error("请先填写行程标题～")

    # ---- 8.2 用折叠面板展示所有行程 ----
    st.subheader("我的行程")
    plans = get_travel_plans()

    if not plans:
        st.info("还没有行程，先在上面规划一个吧～")
        return

    for plan in plans:
        plan_id, title, details, _ = plan
        with st.expander(f"📍 {title}"):
            if details:
                st.text(details)  # 纯文本原样展示，保留换行
            else:
                st.caption("（还没有填写日程安排）")
            if st.button("✅ 行程已结束", key=f"end_plan_{plan_id}"):  # key 必须唯一
                delete_travel_plan(plan_id)
                st.success("行程已归档删除～")
                st.rerun()


# ============ 9. 主流程 ============

def main():
    # 用 session_state 记住登录状态（刷新页面不会丢）
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()  # 没登录 → 显示登录页
    else:
        # 侧边栏导航
        st.sidebar.title("❤️ Jessie&Chris")
        menu = st.sidebar.radio(
            "导航",
            ["🏠 首页", "📋 任务与记账", "🖼️ 照片墙", "📊 专属数据大屏", "🎁 礼物与心愿单", "🎲 随机选择器", "🗺️ 出行计划"],
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
        elif menu == "📊 专属数据大屏":
            dashboard_page()
        elif menu == "🎁 礼物与心愿单":
            wishlist_page()
        elif menu == "🎲 随机选择器":
            picker_page()
        elif menu == "🗺️ 出行计划":
            travel_page()


if __name__ == "__main__":
    main()
