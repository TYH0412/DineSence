import streamlit as st
import pandas as pd
import plotly.express as px
import ast  # 用來解析儲存在資料庫裡的字典字串

def display(db_instance=None):
    st.header("📈 營運數據儀表板")
    
    if not db_instance:
        st.error("資料庫未連接，無法顯示數據。")
        return

    # 1. 從資料庫讀取數據
    try:
        df = db_instance.get_recent_logs(limit=100)
        if df.empty:
            st.info("目前資料庫中尚無數據，請先至「即時鏡頭分析」開啟鏡頭進行收集。")
            return
    except Exception as e:
        st.error(f"讀取數據錯誤: {e}")
        return

    # 2. 資料前處理 (將字串轉回字典)
    def parse_dict(dict_str):
        try:
            return ast.literal_eval(dict_str) if dict_str else {}
        except:
            return {}

    df['emotions_dict'] = df['emotions'].apply(parse_dict)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 3. 顯示 KPI 指標
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("已紀錄筆數", len(df))
    with col2:
        st.metric("最新更新", df.iloc[0]['timestamp'].strftime("%H:%M:%S"))
    with col3:
        # 顯示最近一筆紀錄中最主要的情緒
        last_emotions = df.iloc[0]['emotions_dict']
        top_emotion = max(last_emotions, key=last_emotions.get) if last_emotions else "N/A"
        st.metric("當前主要情緒", top_emotion)

    st.divider()

    # 4. 繪製圖表 (情緒趨勢)
    st.subheader("😊 情緒變化趨勢 (近100筆)")
    
    # 將字典欄位展開
    emotions_df = pd.json_normalize(df['emotions_dict'])
    emotions_df['timestamp'] = df['timestamp']
    emotions_df = emotions_df.fillna(0)
    
    # 轉換為長格式以便 Plotly 繪圖
    emotions_long = emotions_df.melt(id_vars=['timestamp'], var_name='Emotion', value_name='Count')
    
    if not emotions_long.empty:
        fig = px.line(
            emotions_long, 
            x='timestamp', 
            y='Count', 
            color='Emotion',
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("暫無情緒數據可繪製")

    # 5. 顯示原始資料表格
    with st.expander("查看原始資料庫內容"):
        st.dataframe(df[['timestamp', 'people_count', 'emotions', 'food_detected']])
