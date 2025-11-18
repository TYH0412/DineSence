import streamlit as st
import config
# 引入服務與 UI 模組 (包含新的 db_manager)
from services import llm_handler, vision_analysis as va, db_manager
from ui import live_view, video_view, dashboard_view, login_view
from utils import state_manager

st.set_page_config(
    page_title="DineSence 顧客分析平台",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 初始化資源與資料庫 ---
@st.cache_resource
def load_resources():
    """集中載入所有昂貴的模型物件與資料庫連線"""
    openai_client = llm_handler.get_openai_client(config.OPENAI_API_KEY)
    pose_detector = va.get_pose_detector()
    face_detector = va.get_face_detector()
    # 觸發 YOLO 模型載入 (確保它被 cache)
    _ = va.detect_food_regions_yolo 

    # [核心修改] 初始化資料庫管理員
    db = db_manager.DatabaseManager("dinesence.db")

    return openai_client, pose_detector, face_detector, db

# 初始化 Session State
state_manager.initialize_state()
# 載入資源 (解包回傳值，新增 db)
client, pose_detector, face_detector, db = load_resources()

# --- 登入閘門 ---
if not st.session_state.auth:
    login_view.display()
    st.stop()

# --- 側邊欄 UI ---
with st.sidebar:
    st.header("⚙️ 設定")
    store_type = st.selectbox("店型", ["一般餐廳", "咖啡店"], index=0)
    tone = st.selectbox("摘要語氣", ["專業", "親切"], index=0)
    tips_style = st.selectbox("建議風格", ["執行優先", "行銷洞察"], index=0)
    
    st.divider()
    menu_text = st.text_area("菜單設定", "咖啡\n蛋糕\n三明治", height=100)
    menu_items = [x.strip() for x in menu_text.splitlines() if x.strip()]

llm_preferences = {"store_type": store_type, "tone": tone, "tips_style": tips_style}

# [核心修改] 將 db 加入 model_pack，方便傳遞給 live_view
model_pack = {
    "client": client,
    "pose_detector": pose_detector,
    "face_detector": face_detector,
    "db": db 
}

# --- 主頁面 UI ---
st.title("🍽️ DineSence 顧客分析平台")

if not client:
    st.error("⚠️ 請設定 OPENAI_API_KEY")
else:
    tab_live, tab_video, tab_dashboard = st.tabs([
        "🟢 即時鏡頭分析", 
        "🎞️ 影片離線分析",
        "📈 本月數據儀表板" # 新增的分頁
    ])

    with tab_live:
        live_view.display(model_pack, menu_items, llm_preferences)

    with tab_video:
        video_view.display(client, menu_items, llm_preferences)
        
    with tab_dashboard:
        # 將資料庫物件傳入儀表板
        dashboard_view.display(db_instance=db)
