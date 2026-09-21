# -*- coding: utf-8 -*-
"""
Jessie&Chris —— 云存储版 (app.py)
数据存 Supabase（PostgreSQL + Storage），云端部署后不会因休眠丢失数据。
"""

import os
import random
import time
from datetime import datetime

import streamlit as st
import pandas as pd
from supabase import create_client


# ============ 0. 页面基础设置 ============
st.set_page_config(page_title="Jessie&Chris", page_icon="❤️", layout="wide")

# 登录密码（硬编码，简单示例，不追求安全性）
PASSWORD = "520"

# Supabase Storage 里的两个存储桶名字
IMAGE_BUCKET = 'images'        # 照片墙
ATTACH_BUCKET = "attachments"  # 任务附件

# ---- 读取 Supabase 连接信息（从 Streamlit Secrets）----
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error(
        "还没配置 Supabase 密钥。请先在 `.streamlit/secrets.toml`（本地）"
        "或 Streamlit Cloud 的 Secrets 面板里，添加 `SUPABASE_URL` 和 `SUPABASE_KEY`。"
    )
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============ 1. 数据库相关函数（改用 Supabase） ============

def _to_tuple(row, keys):
    """把 Supabase 返回的字典按指定顺序转成元组，方便老代码用下标取值"""
    return tuple(row.get(k) for k in keys)


TASK_KEYS = ["id", "direction", "content", "done", "created_at", "image"]
WISH_KEYS = ["id", "name", "budget", "note", "proposer", "status", "created_at"]
PLAN_KEYS = ["id", "title", "details", "created_at"]


def add_task(direction, content, image=None):
    """往数据库里新增一条任务（image 是附件图片文件名，可以没有）"""
    supabase.table("tasks").insert({
        "direction": direction,
        "content": content,
        "done": 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image": image,
    }).execute()


def get_tasks():
    """读取所有任务，未完成的排前面、新的排前面"""
    res = supabase.table("tasks").select("*").execute()
    rows = [_to_tuple(r, TASK_KEYS) for r in res.data]
    rows.sort(key=lambda r: (r[3], -r[0]))  # done 升序(0 在前)、id 降序
    return rows


def mark_done(task_id):
    """把某条任务标记为已完成"""
    supabase.table("tasks").update({"done": 1}).eq("id", task_id).execute()


def add_wish(name, budget, note, proposer):
    """往心愿单里新增一条心愿"""
    supabase.table("wishlist").insert({
        "name": name,
        "budget": budget,
        "note": note,
        "proposer": proposer,
        "status": 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }).execute()


def get_wishes():
    """读取所有心愿，未认领的排前面、新的排前面"""
    res = supabase.table("wishlist").select("*").execute()
    rows = [_to_tuple(r, WISH_KEYS) for r in res.data]
    rows.sort(key=lambda r: (r[5], -r[0]))  # status 升序(0 在前)、id 降序
    return rows


def claim_wish(wish_id):
    """把某条心愿标记为已认领"""
    supabase.table("wishlist").update({"status": 1}).eq("id", wish_id).execute()


def add_travel_plan(title, details):
    """往出行计划里新增一条行程"""
    supabase.table("travel_plans").insert({
        "title": title,
        "details": details,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }).execute()


def get_travel_plans():
    """读取所有行程，新的排前面"""
    res = supabase.table("travel_plans").select("*").execute()
    rows = [_to_tuple(r, PLAN_KEYS) for r in res.data]
    rows.sort(key=lambda r: -r[0])  # id 降序，新的在前
    return rows


def delete_travel_plan(plan_id):
    """把某条行程从数据库删除（结束归档）"""
    supabase.table("travel_plans").delete().eq("id", plan_id).execute()


# ============ 1.5 图片存储相关函数（改用 Supabase Storage） ============

def upload_image(bucket, filename, file_bytes, content_type):
    """把图片上传到 Supabase Storage 的某个桶里"""
    supabase.storage.from_(bucket).upload(
        filename,
        file_bytes,
        {"content-type": content_type},
    )


def image_url(bucket, filename):
    """根据文件名拼出公开访问的图片链接"""
    return supabase.storage.from_(bucket).get_public_url(filename)


def list_images(bucket):
    """列出某个存储桶里的所有文件名"""
    try:
        files = supabase.storage.from_(bucket).list()
    except Exception:
        # 桶不存在 / 网络异常时，不要因为“列出失败”就整页崩溃，按空处理
        return []
    if isinstance(files, dict):  # 兼容部分版本把结果包在 data 里
        files = files.get("data", [])
    names = []
    for f in files:
        name = f["name"] if isinstance(f, dict) else getattr(f, "name", None)
        if name:
            names.append(name)
    return names


# ============ 2. 登录模块 ============

def login_page():
    """登录页面：输入正确密码才放行"""
    st.title("❤️ Jessie&Chris")
    password = st.text_input("请输入密码", type="password")
    if st.button("登录"):
        if password == PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("密码错误，请重试！")


# ============ 3. 任务与记账模块 ============

def tasks_page():
    st.header("📋 任务与记账")

    # ---- 3.1 添加记录的表单 ----
    with st.form("add_form", clear_on_submit=True):
        direction = st.selectbox("谁欠谁", ["我欠女友", "女友欠我"])
        content = st.text_input("欠了什么要求 / 任务")
        reason_img = st.file_uploader(
            "上传原因图片（可选）",
            type=["png", "jpg", "jpeg", "gif", "webp"],
        )
        submitted = st.form_submit_button("提交")

    if submitted:
        if content.strip():
            image_name = None
            if reason_img is not None:
                ext = os.path.splitext(reason_img.name)[1]
                image_name = datetime.now().strftime("%Y%m%d%H%M%S%f") + ext
                upload_image(ATTACH_BUCKET, image_name, reason_img.getvalue(), reason_img.type)
            add_task(direction, content.strip(), image_name)
            st.success("已添加记录！")
            st.rerun()
        else:
            st.error("请先输入任务内容～")

    # ---- 3.2 用表格展示所有记录 ----
    st.subheader("记录列表")
    rows = get_tasks()

    if rows:
        df = pd.DataFrame(rows, columns=["ID", "谁欠谁", "任务/要求", "状态", "创建时间", "附件"])
        df["状态"] = df["状态"].apply(lambda x: "✅ 已完成" if x == 1 else "⏳ 未完成")
        df["附件"] = df["附件"].apply(lambda x: "📎 有附件" if x else "无")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ---- 3.3 标记完成 ----
        incomplete = [r for r in rows if r[3] == 0]
        if incomplete:
            st.subheader("标记完成")
            option_map = {f"#{r[0]} ｜ {r[1]} ｜ {r[2]}": r[0] for r in incomplete}
            choice = st.selectbox("选择要标记为完成的记录", list(option_map.keys()))
            if st.button("标记完成"):
                mark_done(option_map[choice])
                st.success("已标记完成！")
                st.rerun()

        # ---- 3.4 附件预览 ----
        with_img = [r for r in rows if r[5]]
        if with_img:
            st.subheader("附件预览")
            cols = st.columns(3)
            for i, r in enumerate(with_img):
                with cols[i % 3]:
                    st.image(image_url(ATTACH_BUCKET, r[5]), caption=f"#{r[0]} {r[2]}", use_container_width=True)
    else:
        st.info("还没有记录，先在上面添加一条吧～")


# ============ 4. 照片墙模块 ============

def photos_page():
    st.header("🖼️ 照片墙")

    uploaded = st.file_uploader(
        "上传照片",
        type=["png", "jpg", "jpeg", "gif"],
        accept_multiple_files=True,
    )
    if uploaded:
        for f in uploaded:
            upload_image(IMAGE_BUCKET, f.name, f.getvalue(), f.type)
        st.success("上传成功！")
        st.rerun()

    st.subheader("我们的回忆")
    files = list_images(IMAGE_BUCKET)
    if files:
        cols = st.columns(3)
        for i, name in enumerate(files):
            with cols[i % 3]:
                st.image(image_url(IMAGE_BUCKET, name), caption=name, use_container_width=True)
    else:
        st.info("还没有照片，上传一张开启回忆吧～")


# ============ 5. 专属数据大屏模块 ============

def dashboard_page():
    """数据大屏：展示两人任务对比、本月新增等统计"""
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

    love_quotes = [
        "遇见你之后，我的世界才变得完整 ❤️",
        "你是我所有计划里，唯一的例外。",
        "和你在一起的每一天，都是情人节。",
        "世界那么大，我只想和你虚度时光。",
        "谢谢你来到我身边，让我想成为更好的人。",
    ]
    st.markdown(f"### 💌 {random.choice(love_quotes)}")

    rows = get_tasks()

    if not rows:
        st.info("还没有数据，先到「任务与记账」添加几条吧～")
        return

    df = pd.DataFrame(rows, columns=["ID", "谁欠谁", "任务/要求", "状态", "创建时间", "附件"])
    df["状态"] = df["状态"].apply(lambda x: "已完成" if x == 1 else "未完成")

    this_month = datetime.now().strftime("%Y-%m")
    month_count = sum(1 for r in rows if r[4] and r[4].startswith(this_month))
    done_count = int((df["状态"] == "已完成").sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("本月新增任务", month_count)
    c2.metric("任务总数", len(df))
    c3.metric("已完成", done_count, f"{done_count/len(df)*100:.0f}% 完成率")

    st.subheader("我们俩的任务对比")
    summary = df.groupby(["谁欠谁", "状态"]).size().unstack(fill_value=0)
    for col in ["已完成", "未完成"]:
        if col not in summary.columns:
            summary[col] = 0
    summary = summary[["已完成", "未完成"]]
    st.bar_chart(summary)


# ============ 6. 礼物与心愿单模块 ============

def wishlist_page():
    """礼物与心愿单：许愿、展示心愿、认领买单"""
    st.header("🎁 礼物与心愿单")

    if st.session_state.get("celebrate"):
        st.balloons()
        st.session_state.celebrate = False

    with st.form("wish_form", clear_on_submit=True):
        proposer = st.selectbox("这是谁的心愿", ["Jessie", "Chris"])
        name = st.text_input("心愿名称", placeholder="例如：汪苏泷演唱会门票")
        budget = st.text_input("预算（可选）", placeholder="例如：1000 元")
        note = st.text_input("详情备注（款式 / 规格，可选）", placeholder="例如：内场票、粉色款式")
        submitted = st.form_submit_button("许下心愿 ✨")

    if submitted:
        if name.strip():
            add_wish(name.strip(), budget.strip(), note.strip(), proposer)
            st.success("心愿已许下！")
            st.rerun()
        else:
            st.error("请先填写心愿名称～")

    st.subheader("我们的心愿清单")
    wishes = get_wishes()

    if not wishes:
        st.info("还没有心愿，快来许下第一个吧～")
        return

    cols = st.columns(3)
    for i, w in enumerate(wishes):
        w_id, name, budget, note, proposer, status, _ = w
        claimed = status == 1
        with cols[i % 3]:
            with st.container(border=True):
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
                        st.session_state.celebrate = True
                        st.rerun()


# ============ 7. 随机选择器模块 ============

def picker_page():
    """随机选择器：解决今天吃什么、周末去哪玩"""
    st.header("🎲 随机选择器")

    st.write("把备选方案用逗号隔开，交给命运决定吧～")

    options_text = st.text_area(
        "备选方案（用逗号分隔）",
        value="去打板球, 骑行绿道, 宅家看剧",
        height=120,
    )

    if st.button("🎯 听天由命 (随机抽取)", type="primary", use_container_width=True):
        items = [x.strip() for x in options_text.split(",") if x.strip()]
        if not items:
            st.error("请先输入至少一个备选方案～")
        else:
            with st.spinner("命运的齿轮开始转动..."):
                time.sleep(1.5)
            result = random.choice(items)
            st.success(f"### 🎉 就决定是你啦：**{result}**")


# ============ 8. 出行计划模块 ============

def travel_page():
    """出行计划：录入行程、用折叠面板展示、结束后归档删除"""
    st.header("🗺️ 出行计划")

    with st.form("travel_form", clear_on_submit=True):
        title = st.text_input("行程标题", placeholder="例如：周末露营")
        details = st.text_area(
            "日程安排",
            placeholder="带什么装备、时间表等，直接打字或粘贴到这里...",
            height=200,
        )
        submitted = st.form_submit_button("保存行程 ✈️")

    if submitted:
        if title.strip():
            add_travel_plan(title.strip(), details.strip())
            st.success("行程已保存！")
            st.rerun()
        else:
            st.error("请先填写行程标题～")

    st.subheader("我的行程")
    plans = get_travel_plans()

    if not plans:
        st.info("还没有行程，先在上面规划一个吧～")
        return

    for plan in plans:
        plan_id, title, details, _ = plan
        with st.expander(f"📍 {title}"):
            if details:
                st.text(details)
            else:
                st.caption("（还没有填写日程安排）")
            if st.button("✅ 行程已结束", key=f"end_plan_{plan_id}"):
                delete_travel_plan(plan_id)
                st.success("行程已归档删除～")
                st.rerun()


# ============ 9. 主流程 ============

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
    else:
        st.sidebar.title("❤️ Jessie&Chris")
        menu = st.sidebar.radio(
            "导航",
            ["🏠 首页", "📋 任务与记账", "🖼️ 照片墙", "📊 专属数据大屏", "🎁 礼物与心愿单", "🎲 随机选择器", "🗺️ 出行计划"],
        )

        if st.sidebar.button("退出登录"):
            st.session_state.logged_in = False
            st.rerun()

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
