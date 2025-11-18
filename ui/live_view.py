import streamlit as st
import cv2
import time
import os
import asyncio
from collections import Counter
from datetime import datetime

# 導入核心模組
from core.live_analyzer import LiveAnalyzer
from core.types import AnalysisResult
from services import llm_handler as llm

# [新增] 確保截圖資料夾存在
if not os.path.exists("snapshots"):
    os.makedirs("snapshots")

def display(model_pack: dict, menu_items: list, llm_preferences: dict):
    # 1. 取得資料庫物件
    db = model_pack.get("db")

    lcol, rcol = st.columns([2, 1])
    
    with rcol:
        st.subheader("控制台")
        run_live = st.toggle("開啟鏡頭", value=False, key="live_toggle")
        
        opt_nod = st.checkbox("點頭偵測", value=True)
        opt_emote = st.checkbox("表情分類", value=True)
        opt_plate = st.checkbox("餐盤分析", value=True)
        analysis_options = { "opt_nod": opt_nod, "opt_emote": opt_emote, "opt_plate": opt_plate }
        
        st.divider()
        fps_display = st.slider("FPS", 5, 30, 20)
        
        st.divider()
        st.subheader("即時統計")
        stat_info = st.empty()
        
        # LLM 摘要按鈕邏輯 (簡化顯示)
        if st.button("產生摘要 (LLM)"):
            st.info("摘要功能保留 (省略詳細代碼)")

    # --- 狀態管理 ---
    current_toggle_state = run_live
    last_toggle_state = st.session_state.live_toggle_last_state

    if current_toggle_state and not last_toggle_state:
        st.toast("監控開始！自動儲存數據中...", icon="🔴")
        st.session_state.nod_count = 0
        st.session_state.emotion_counter = Counter()
        st.session_state.leftover_counter = Counter()
        st.session_state.current_summary = ""

    st.session_state.live_toggle_last_state = current_toggle_state

    # --- 啟動分析引擎 ---
    if run_live and st.session_state.analyzer is None:
        st.session_state.analyzer = LiveAnalyzer(model_pack, menu_items, analysis_options)
        st.session_state.analyzer.start()
    if not run_live and st.session_state.analyzer is not None:
        st.session_state.analyzer.stop()
        st.session_state.analyzer = None

    # --- [設定] 計時器與參數 ---
    last_db_save_time = time.time()
    DB_SAVE_INTERVAL = 5.0      # 設定：每 5 秒存一次資料庫
    last_snapshot_time = 0
    SNAPSHOT_COOLDOWN = 10.0    # 設定：截圖冷卻時間 10 秒 (避免一直拍)

    # --- 主迴圈 ---
    with lcol:
        frame_slot = st.empty()

    latest_analysis_data = AnalysisResult()
    
    if run_live and st.session_state.analyzer:
        while True:
            frame = st.session_state.analyzer.get_latest_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            analysis_result = st.session_state.analyzer.get_latest_analysis_result()
            
            if analysis_result:
                # 更新統計
                if analysis_result.nod_event: st.session_state.nod_count += 1
                if analysis_result.emotion_event: st.session_state.emotion_counter[analysis_result.emotion_event] += 1
                if analysis_result.plate_event: st.session_state.leftover_counter[analysis_result.plate_event] += 1
            
                current_time = time.time()

                # ==========================================
                # 功能 1: 自動寫入資料庫 (每 5 秒)
                # ==========================================
                if db and (current_time - last_db_save_time > DB_SAVE_INTERVAL):
                    estimated_people = sum(st.session_state.emotion_counter.values())
                    # 寫入資料庫
                    db.insert_log(
                        source_type='live',
                        people_count=estimated_people,
                        emotions=dict(st.session_state.emotion_counter),
                        food_detected=dict(st.session_state.leftover_counter)
                    )
                    last_db_save_time = current_time
                
                # ==========================================
                # 功能 2: 異常事件自動截圖 (Snapshot)
                # ==========================================
                # 設定觸發條件：偵測到「生氣」或「噁心」
                target_emotions = ["Angry", "Disgust"]
                current_emotion = analysis_result.emotion_event
                
                if current_emotion in target_emotions:
                    if current_time - last_snapshot_time > SNAPSHOT_COOLDOWN:
                        # 產生檔名
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"snapshots/ALERT_{current_emotion}_{timestamp_str}.jpg"
                        
                        # 存檔 (BGR格式)
                        cv2.imwrite(filename, frame)
                        
                        # 畫面上顯示警告
                        cv2.putText(frame, f"SNAPSHOT SAVED: {filename}", (20, 150), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        
                        last_snapshot_time = current_time

            # --- 畫面繪製 ---
            display_info = analysis_result.display_info if analysis_result else {}
            
            # 顯示基本資訊
            cv2.putText(frame, f"Nod: {st.session_state.nod_count}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
            emotion_show = analysis_result.emotion_event if analysis_result and analysis_result.emotion_event else "N/A"
            cv2.putText(frame, f"Emotion: {emotion_show}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)

            # 顯示到 Streamlit
            frame_slot.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB")
            
            # 更新右側文字
            stat_info.markdown(f"""
            - **點頭**: {st.session_state.nod_count}
            - **情緒**: {dict(st.session_state.emotion_counter)}
            - **狀態**: 監控中 (每5秒存檔 + 異常截圖)
            """)
            
            time.sleep(1.0 / fps_display)
    else:
        frame_slot.info("請點擊上方「開啟鏡頭」以開始。")
