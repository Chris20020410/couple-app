# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from supabase import create_client

KEY = "sb_publishable_trkLA7hEG5HxAOYXJmXtnw_Z-uAi_-d"

# 模拟“云端把 URL 写成了带 /rest/v1 后缀”的情况
for url in [
    "https://iqqfnawxhvvbtdllrusa.supabase.co/rest/v1",
    "https://iqqfnawxhvvbtdllrusa.supabase.co/",
]:
    print("=== URL:", url)
    try:
        c = create_client(url, KEY)
        r = c.storage.from_("images").list()
        print("  storage list OK ->", r)
    except Exception as e:
        print("  storage list FAIL:", type(e).__name__, "|", str(e)[:200])
    try:
        r = c.table("tasks").select("*").execute()
        print("  tasks OK rows=", len(r.data))
    except Exception as e:
        print("  tasks FAIL:", type(e).__name__, "|", str(e)[:200])
