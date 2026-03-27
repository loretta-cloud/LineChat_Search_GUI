import streamlit as st
import re
from collections import Counter
from datetime import datetime
import pandas as pd

# 設定網頁標題
st.set_page_config(page_title="LINE 社群對話分析工具", layout="centered")
st.title("📊 LINE 社群對話分析工具")

# 1. 檔案上傳區
st.subheader("1. 上傳對話紀錄")
uploaded_file = st.file_uploader("請上傳從 LINE 匯出的 txt 檔案", type="txt")

# 2. 時間範圍
st.subheader("2. 設定時間範圍")
st.write("請點擊下方選取起始與結束日期 (若不選則代表分析全部時間)")
date_range = st.date_input("選擇時間範圍", value=[])

# 3. 關鍵字輸入
st.subheader("3. 設定搜尋關鍵字")
keyword_input = st.text_input(
    "輸入要搜尋的關鍵字 (多個關鍵字/錯別字請用半形逗號 ',' 隔開):", 
    value="我奶粉我驕傲,我奶粉我嬌傲,我是奶粉我驕傲"
)

# 將核心分析邏輯包裝成一個獨立的 Function
def analyze_chat_data(content, keywords, start_date, end_date):
    lines = content.split('\n')
    
    # ==========================================
    # 雙軌制正規表達式 (支援中/英文匯出格式)
    # ==========================================
    # 格式一 (舊版/英文): Thu, 08/07/2025
    date_pattern_en = re.compile(r'^[A-Z][a-z]{2},\s(\d{2}/\d{2}/\d{4})$')
    # 格式二 (新版/中文): 2026.01.26 星期一
    date_pattern_zh = re.compile(r'^(\d{4}\.\d{2}\.\d{2})\s+星期[一二三四五六日]$')
    
    # 格式一訊息: 05:37PM \t 瑄瑄 \t [Photo]
    msg_pattern_en = re.compile(r'^(\d{2}:\d{2}[AP]M)\t([^\t]+)\t(.*)$')
    # 格式二訊息: 10:26 Unknown 圖片 (空白或Tab分隔)
    msg_pattern_zh = re.compile(r'^(\d{2}:\d{2})\s+([^\s\t]+)[\s\t]+(.*)$')
    
    user_keyword_counts = Counter()
    current_date = None
    current_user = None
    current_message_buffer = []

    def process_buffered_message():
        nonlocal current_user, current_date, current_message_buffer
        if current_user and current_date:
            if start_date <= current_date <= end_date:
                full_message = "\n".join(current_message_buffer)
                # 只要訊息內包含任何一個變體關鍵字，該使用者的計數就 +1
                if any(kw in full_message for kw in keywords):
                    user_keyword_counts[current_user] += 1

    # 逐行分析
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 1. 檢查是否為英文日期
        date_match_en = date_pattern_en.match(line)
        if date_match_en:
            process_buffered_message()
            current_user = None
            current_message_buffer = []
            current_date = datetime.strptime(date_match_en.group(1), "%m/%d/%Y")
            continue
            
        # 2. 檢查是否為中文日期
        date_match_zh = date_pattern_zh.match(line)
        if date_match_zh:
            process_buffered_message()
            current_user = None
            current_message_buffer = []
            current_date = datetime.strptime(date_match_zh.group(1), "%Y.%m.%d")
            continue
        
        # 3. 檢查是否為英文格式訊息
        msg_match_en = msg_pattern_en.match(line)
        if msg_match_en:
            process_buffered_message()
            time_str, user, message = msg_match_en.groups()
            current_user = user
            current_message_buffer = [message]
            continue
            
        # 4. 檢查是否為中文格式訊息
        msg_match_zh = msg_pattern_zh.match(line)
        if msg_match_zh:
            process_buffered_message()
            time_str, user, message = msg_match_zh.groups()
            current_user = user
            current_message_buffer = [message]
            continue
            
        # 若都不是，則視為多行留言的換行內容
        if current_user is not None:
            current_message_buffer.append(line)
                
    # 處理最後一筆停留在 buffer 中的訊息
    process_buffered_message()
    
    return user_keyword_counts


# 執行介面邏輯
if st.button("🚀 開始分析", use_container_width=True):
    if not uploaded_file:
        st.warning("⚠️ 請先上傳 txt 檔案！")
    elif not keyword_input:
        st.warning("⚠️ 請輸入至少一個搜尋關鍵字！")
    else:
        with st.spinner("分析中，請稍候..."):
            keywords = [k.strip() for k in keyword_input.split(',') if k.strip()]
            
            # 處理日期範圍邏輯
            start_date = datetime.min
            end_date = datetime.max
            
            if isinstance(date_range, (tuple, list)):
                if len(date_range) == 2:
                    start_date = datetime.combine(date_range[0], datetime.min.time())
                    end_date = datetime.combine(date_range[1], datetime.max.time())
                elif len(date_range) == 1:
                    start_date = datetime.combine(date_range[0], datetime.min.time())
                    end_date = datetime.combine(date_range[0], datetime.max.time())

            # 讀取檔案內容
            content = uploaded_file.read().decode("utf-8")
            
            # 呼叫分析函數
            user_keyword_counts = analyze_chat_data(content, keywords, start_date, end_date)

            # --- 顯示分析結果 ---
            total_unique_users = len(user_keyword_counts)
            total_message_mentions = sum(user_keyword_counts.values())
            
            st.success("✅ 分析完成！")
            
            col1, col2 = st.columns(2)
            col1.metric("不重複發言人數", f"{total_unique_users} 人")
            col2.metric("符合條件的訊息總數", f"{total_message_mentions} 則")
            
            st.markdown("---")
            
            if total_unique_users > 0:
                st.subheader("🏆 留言排行榜 (由多到少)")
                data = [{"排名": rank, "使用者名稱": user, "留言則數": count} 
                        for rank, (user, count) in enumerate(user_keyword_counts.most_common(), 1)]
                df = pd.DataFrame(data)
                
                # 顯示表格
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("在指定的條件內，沒有找到符合的紀錄。")