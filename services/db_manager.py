import sqlite3
import datetime
import pandas as pd
import os

class DatabaseManager:
    def __init__(self, db_path="dinesence.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """建立並回傳資料庫連線"""
        # check_same_thread=False 是為了讓 Streamlit 的不同執行緒都能存取
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        """初始化資料庫結構"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 建立分析紀錄表
        # emotions 和 food_detected 將會以文字形式儲存 (例如 "{'Happy': 1}")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source_type TEXT,   
                people_count INTEGER,
                emotions TEXT,      
                food_detected TEXT, 
                raw_data TEXT       
            )
        ''')
        conn.commit()
        conn.close()

    def insert_log(self, source_type, people_count, emotions, food_detected):
        """寫入一筆分析數據"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            current_time = datetime.datetime.now()
            
            # 將字典轉為字串以便儲存
            emotions_str = str(emotions)
            food_str = str(food_detected)

            cursor.execute('''
                INSERT INTO analysis_logs (timestamp, source_type, people_count, emotions, food_detected)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_time, source_type, people_count, emotions_str, food_str))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"DB Error: {e}")
            return False

    def get_recent_logs(self, limit=100):
        """讀取最近的 N 筆數據"""
        conn = self.get_connection()
        query = "SELECT * FROM analysis_logs ORDER BY timestamp DESC LIMIT ?"
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
