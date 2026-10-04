import json
import os
import re
import streamlit as st
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# --- 1. DTO & Schema الشامل للرولبلي العميق ---
class GameState(BaseModel):
    is_created: bool = Field(default=False, description="هل تم إنشاء الشخصية؟")
    name: str = Field(description="اسم النينجا")
    ninja_type: str = Field(description="نوع النينجا: نينجا نظامي أم نينجا هارب (Nukenin)")
    rogue_background: Optional[str] = Field(default="غير محدد", description="خلفية النينجا الهارب وطبيعة ملاحقته")
    bounty: int = Field(default=0, description="المكافأة المالية على رأس النينجا (بالـ Ryo)")
    anbu_heat: int = Field(default=0, description="مستوى خطر ملاحقة فرق الأنبو والنينجا الصيادين (0-100)")
    rank: str = Field(description="الرتبة أو التصنيف القتالي")
    level: int = Field(default=1, description="المستوى")
    exp: int = Field(default=0, description="نقاط الخبرة")
    origin_village: str = Field(description="قرية المنشأ أو الانتماء")
    era: str = Field(description="الحقبة الزمنية للقصة (الآرك)")
    location: str = Field(description="المكان الحالي بدقة")
    nindo: str = Field(description="طريق النينجا / الدافع وفلسفة الحياة")
    kekkei_genkai: str = Field(description="الحد الجيني أو القدرة الخاصة")
    health: int = Field(default=100, description="الصحة النفسية والجسدية من 0 إلى 100")
    chakra: int = Field(default=100, description="الشاكرا من 0 إلى 100")
    substitutions: int = Field(default=4, description="عدد شخطات الاستبدال (0-4)")
    storm_gauge: int = Field(default=0, description="عداد الستورم (0-100%)")
    awakening_active: bool = Field(default=False, description="هل طور الصحوة مفعل؟")
    awakening_type: str = Field(description="نوع الصحوة الكبرى")
    ultimate_jutsu: str = Field(description="التقنية السرية الأسطورية (Ougi)")
    relationships: Dict[str, str] = Field(default_factory=dict, description="شبكة العلاقات وتصور الشخصيات عنك")
    jutsus: List[str] = Field(description="التقنيات المتقنة")
    inventory: List[str] = Field(description="الحقيبة والعتاد")
    current_situation: str = Field(description="الموقف الراهن والورطة القائمة")
    active_enemy: str = Field(default="لا يوجد", description="اسم الخصم الحالي")
    enemy_health: int = Field(default=100, description="صحة الخصم من 0 إلى 100")
    story_log: List[str] = Field(description="أرشيف القرارات والأحداث")

class GameResponse(BaseModel):
    story_narration: str = Field(description="السرد القصصي السينمائي وحوارات الشخصيات بأسلوب مانجا كيشيموتو")
    updated_state: GameState = Field(description="تحديث حالة اللعبة بالكامل")

STATE_FILE = "naruto_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"is_created": False}

def save_state(state_data: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)

def clamp(val: int, min_val: int = 0, max_val: int = 100) -> int:
    try:
        return max(min_val, min(max_val, int(val)))
    except Exception:
        return min_val

def clean_json_response(raw_text: str) -> str:
    """تصفية نص الـ JSON من وسوم المارك داون لمنع الـ Crash"""
    match = re.search(r'\{[\s\S]*\}', raw_text)
    if match:
        return match.group(0)
    return raw_text

def test_gemini_api_key(key: str) -> bool:
    """فحص صحة مفتاح الـ API بشكل حي"""
    if not key or len(key.strip()) < 20:
        return False
    try:
        client = genai.Client(api_key=key.strip())
        # تجربة طلب خفيف جداً للتأكد من التفعيل
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="ping"
        )
        return True if res.text else False
    except Exception:
        return False

# --- 2. التصميم البصري (Manga Dark UI) ---
st.set_page_config(page_title="Naruto RPG Engine v10.0 Uncut", page_icon="📜", layout="wide")

MANGA_STORM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@600;800;900&family=Orbitron:wght@700;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif !important;
        background-color: #030406 !important;
        color: #F1F5F9 !important;
    }
    .stApp {
        background: radial-gradient(circle at 50% 10%, #170724 0%, #020305 90%) !important;
    }
    div[data-testid="stSidebar"] {
        background: rgba(6, 8, 14, 0.96) !important;
        backdrop-filter: blur(16px);
        border-left: 2px solid #DC2626 !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #220F33 0%, #090412 100%) !important;
        color: #FFD700 !important;
        border: 1.5px solid #FF2A00 !important;
        border-radius: 6px !important;
        font-weight: 800 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #FF2A00 0%, #880000 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 16px rgba(255, 42, 0, 0.8) !important;
    }
    .status-badge-ok {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid #10B981;
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }
    .status-badge-err {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid #EF4444;
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }
    .sub-bar {
        display: inline-block;
        width: 24px;
        height: 12px;
        margin: 2px;
        border-radius: 3px;
        border: 1px solid #00F0FF;
    }
    .sub-filled { background-color: #00F0FF; box-shadow: 0 0 8px #00F0FF; }
    .sub-empty { background-color: #111827; }
    .stat-card-storm {
        background: rgba(13, 16, 28, 0.88);
        border: 1px solid rgba(255, 215, 0, 0.25);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .rogue-card {
        background: rgba(220, 38, 38, 0.1);
        border: 1px solid #DC2626;
        padding: 10px;
        border-radius: 6px;
        margin-top: 5px;
    }
</style>
"""
st.markdown(MANGA_STORM_CSS, unsafe_allow_html=True)

if "game_state" not in st.session_state:
    st.session_state.game_state = load_state()

if "messages" not in st.session_state:
    st.session_state.messages = []

state = st.session_state.game_state

# --- 3. شاشة التأسيس والإنشاء المتقدمة ---
if not state.get("is_created", False):
    st.markdown("<h1 style='text-align: center; color: #DC2626; font-weight:900;'>📜 NARUTO: SHIPPUDEN RPG v10.0 UNCUT</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8;'>المحرك الكامل للسرد الداكن، مسار النينجا الهارب، وأركات القصة الشاملة</p>", unsafe_allow_html=True)
    st.divider()
    
    col_a, col_b, col_c = st.columns([1, 2.2, 1])
    with col_b:
        with st.form("ultimate_uncut_creator"):
            st.subheader("🥷 الهوية والمسار")
            char_name = st.text_input("اسم النينجا:", value="أوتشيها شتوي")
            
            ninja_type = st.radio("مسار النينجا الحركي:", [
                "نينجا نظامي (يتبع قرية رسمية ومهمات رسمية)",
                "نينجا هارب (Nukenin - مطارد وتصنيف خطير)"
            ])
            
            rogue_background = "غير محدد"
            initial_bounty = 0
            initial_heat = 0
            
            if "نينجا هارب" in ninja_type:
                st.markdown("<div class='rogue-card'><b>⚠️ خيارات النينجا الهارب (Nukenin):</b>", unsafe_allow_html=True)
                rogue_choice = st.selectbox("طبيعة الهروب وخلفيتك:", [
                    "متمرد هارب مطارد من فرقة الأنبو والنينجا الصيادين (Hunter-nin)",
                    "نينجا مرتزق مستقل يعمل لحسابه الخاص مقابل المال",
                    "عضو رسمي في منظمة الأكاتسكي (Akatsuki Rogue)",
                    "هربت بعد تجارب بيولوجية سرية في مختبرات أوروتشيمارو"
                ])
                rogue_background = rogue_choice
                initial_bounty = st.slider("المكافأة المبدئية على رأسك (Ryo):", 50000, 50000000, 5000000, step=50000)
                initial_heat = st.slider("مستوى خطر ملاحقة الأنبو (Heat Level):", 10, 90, 40)
                st.markdown("</div>", unsafe_allow_html=True)
                st.write("")

            origin_village = st.selectbox("قرية المنشأ / العشيرة:", [
                "عشيرة الأوتشيها - قرية الورق (Konoha)",
                "عشيرة الهيوغا - قرية الورق",
                "قرية الضباب الدموية (Kirigakure)",
                "قرية السحاب (Kumogakure)",
                "قرية الرمل (Sunagakure)",
                "عشيرة السينجو - قرية الورق",
                "قرية الصخر (Iwagakure)"
            ])
            
            st.subheader("📜 أركات القصة والحقبة الزمنية (Full Canon Arcs)")
            era = st.selectbox("اختر نقطة البداية والآرك التاريخي:", [
                "آرك أرض الأمواج واختبارات التشونين (Part 1 - Land of Waves & Chunin Exams)",
                "آرك البحث عن تسونادي ومواجهة السانين (Part 1 - Search for Tsunade)",
                "آرك استرجاع ساسكي ومعركة وادي النهاية الأول (Part 1 - Sasuke Retrieval)",
                "آرك إنقاذ الكازيكاجي جارا (Shippuden - Kazekage Rescue)",
                "آرك مطاردة الأكاتسكي وانتقام شيكامارو - هيدان وكاكوزو (Shippuden - Akatsuki Suppression)",
                "آرك مطاردة إيتاشي ومعركة الأخوين (Shippuden - Itachi Pursuit)",
                "آرك غزو باين ودمار كونوها (Shippuden - Pain's Assault)",
                "آرك قمة الكاجي الخمسة وإعلان الحرب (Shippuden - Five Kage Summit)",
                "آرك حرب النينجا العظمى الرابعة: الجبهة الأولى (Shippuden - 4th Shinobi War)"
            ])
            
            st.subheader("👁️ القدرات والحد الجيني")
            kekkei_genkai = st.selectbox("الحد الجيني / القدرة العالية:", [
                "المانغيكيو شارينجان (Mangekyou Sharingan)",
                "عنصر البخار والبرق المضغوط (Steam & Lightning)",
                "خلايا سينجو هاشيراما وقوة التحمل (Hashirama Cells)",
                "البياكوغان الرائقة (Byakugan)",
                "عنصر الماجما أو العظام (Kaguya Shikotsumyaku)",
                "التحكم التكتيكي بالشاكرا والنينجوتسو الطبي"
            ])
            
            st.subheader("🔥 طريق النينجا والتقنيات (Nindo)")
            nindo = st.text_area("طريق النينجا (Nindo) وفلسفتك بالحياة:", value="حماية رؤيتي الخاصة وقوتي، ولا أسمح لأي قرية أو نظام بتحكيمي.")
            ultimate_jutsu = st.text_input("التقنية السرية الكبرى (Ougi):", value="إبادة البخار والبرق العظمى: Dragon Steam Ougi")
            awakening_type = st.selectbox("طور الصحوة الكبرى (Awakening):", [
                "تفجر المانغيكيو والبرق المضغوط",
                "السوسانو الكامل الجسد (Full Susanoo)",
                "طور نمط الرداء الكيوبي (KCM)",
                "طور الناسك الأسطوري (Sage Mode)",
                "طور ختم اللعنة الكامل (Curse Mark Level 2)"
            ])
            
            submit_btn = st.form_submit_button("📜 دخول عالم النينجا والمواجهة")
            
            if submit_btn:
                is_rogue = "نينجا هارب" in ninja_type
                new_state = {
                    "is_created": True,
                    "name": char_name,
                    "ninja_type": "Nukenin (نينجا هارب)" if is_rogue else "Shinobi (نينجا نظامي)",
                    "rogue_background": rogue_background,
                    "bounty": initial_bounty if is_rogue else 0,
                    "anbu_heat": initial_heat if is_rogue else 0,
                    "rank": "S-Rank Dangerous Rogue" if is_rogue else "Special Jonin",
                    "level": 1,
                    "exp": 0,
                    "origin_village": origin_village,
                    "era": era,
                    "location": f"أطراف {origin_village.split('-')[0].strip()}" if not is_rogue else "مخبأ سري في المنطق المحايدة",
                    "nindo": nindo,
                    "kekkei_genkai": kekkei_genkai,
                    "health": 100,
                    "chakra": 100,
                    "substitutions": 4,
                    "storm_gauge": 0,
                    "awakening_active": False,
                    "awakening_type": awakening_type,
                    "ultimate_jutsu": ultimate_jutsu,
                    "relationships": {
                        "فرق الأنبو والصيادين": "مطاردة قاسية ومستمرة" if is_rogue else "رقابة رسمية",
                        "إيتاشي أوتشيها": "يراقب خطواتك ببرود",
                        "تسونادي (الهوكاجي)": "تعتبرك خطراً كبيراً" if is_rogue else "تكلفك بمهمات حذرة"
                    },
                    "jutsus": ["تنين البخار الحراري", "البرق المضغوط (Chidori Stream)", "نسخ الظل (Kage Bunshin)"],
                    "inventory": ["10 كوناي مسمومة", "6 لفافات متفجرة", "2 حبوب شاكرا عالية"],
                    "current_situation": f"بدأت مغامرتك في آرك ({era}). {'أنت نينجا هارب مطارد ومحاط بالخطر.' if is_rogue else 'تقف مستعداً لتنفيذ خطوتك القادمة.'}",
                    "active_enemy": "فرقة أنبو صيادين" if is_rogue else "لا يوجد",
                    "enemy_health": 100,
                    "story_log": [f"انطلقت المغامرة في {era} بصفتك {ninja_type}."]
                }
                st.session_state.game_state = new_state
                save_state(new_state)
                st.rerun()

    st.stop()

# --- 4. القائمة الجانبية المتقدمة ومؤشر الـ API ---
with st.sidebar:
    st.markdown("<h2 style='color: #FF2A00; text-align: center; font-family:Orbitron;'>NINJA HUD v10.0</h2>", unsafe_allow_html=True)
    
    api_key = st.text_input("Gemini API Key:", type="password", value=st.session_state.get("saved_api_key", ""))
    
    # فحص ومؤشر الـ API الحي
    if api_key:
        st.session_state["saved_api_key"] = api_key
        is_valid = test_gemini_api_key(api_key)
        if is_valid:
            st.markdown("<div class='status-badge-ok'>🟢 API Key مفعل وجاهز للقتال</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='status-badge-err'>🔴 API Key غير صالح أو متوقف</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='status-badge-err'>⚠️ يرجى إدخال API Key للبدء</div>", unsafe_allow_html=True)
        
    st.divider()
    
    if state.get("awakening_active", False):
        st.markdown(f"<div style='background:linear-gradient(90deg,#FF0055,#FF5500); color:white; padding:8px; text-align:center; font-weight:bold; border-radius:6px;'>🔥 AWAKENING: {state.get('awakening_type')}</div>", unsafe_allow_html=True)
        st.write("")

    st.markdown(f"### 🥷 {state.get('name')} <span style='font-size:0.85rem; color:#FFD700;'>[Lvl {state.get('level', 1)}]</span>", unsafe_allow_html=True)
    st.caption(f"📜 **المسار:** {state.get('ninja_type')}")
    st.caption(f"🏰 **القرية/المنشأ:** {state.get('origin_village')}")
    st.caption(f"📍 **الموقع:** {state.get('location')}")
    
    if "Nukenin" in state.get("ninja_type", ""):
        st.markdown(f"<div style='color:#FF4444; font-weight:bold;'>💰 المكافأة: {state.get('bounty', 0):,} Ryo</div>", unsafe_allow_html=True)
        st.markdown(f"**🚨 خطر الأنبو (Heat): {state.get('anbu_heat', 0)}%**")
        st.progress(clamp(state.get('anbu_heat', 0)) / 100)
    
    st.markdown("---")
    
    health_val = clamp(state.get("health", 100))
    chakra_val = clamp(state.get("chakra", 100))
    sub_val = clamp(state.get("substitutions", 4), 0, 4)
    storm_val = clamp(state.get("storm_gauge", 0))
    
    st.markdown(f"**❤️ HEALTH ({health_val}%):**")
    st.progress(health_val / 100)
    
    st.markdown(f"**💙 CHAKRA ({chakra_val}%):**")
    st.progress(chakra_val / 100)
    
    sub_html = "<b>🛡️ KAWARIMI (الاستبدال):</b><br>"
    for i in range(4):
        sub_html += f"<span class='sub-bar {'sub-filled' if i < sub_val else 'sub-empty'}'></span>"
    st.markdown(sub_html, unsafe_allow_html=True)
    st.write("")
    
    st.markdown(f"**⚡ STORM GAUGE ({storm_val}%):**")
    st.progress(storm_val / 100)
    
    st.markdown("---")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("⚡ SHIFT CHAKRA"):
            state["chakra"] = clamp(state["chakra"] + 45)
            state["story_log"].append("شحنت الشاكرا الخاصة بك بتركيز خاطف (+45%).")
            save_state(state)
            st.rerun()
            
    with col_c2:
        if health_val <= 40 or storm_val >= 80:
            if st.button("🔥 AWAKEN!"):
                state["awakening_active"] = not state.get("awakening_active", False)
                state["story_log"].append(f"تغيرت حالة طور الصحوة: ({state.get('awakening_type')})!")
                save_state(state)
                st.rerun()

    st.divider()
    
    with st.expander("💾 إدارة الحفظ وإعادة التأسيس"):
        json_str = json.dumps(state, ensure_ascii=False, indent=2)
        st.download_button("📥 تصدير ملف الحفظ (JSON)", json_str, f"naruto_uncut_{state.get('name')}.json", "application/json")
        
        uploaded_file = st.file_uploader("📤 استرجاع حفظ سابق:", type=["json"])
        if uploaded_file:
            try:
                loaded = json.load(uploaded_file)
                if loaded.get("is_created"):
                    st.session_state.game_state = loaded
                    save_state(loaded)
                    st.success("تم استرجاع المغامرة بنجاح!")
                    st.rerun()
            except Exception:
                st.error("ملف غير صالح")
                
        if st.button("🗑️ إعادة تأسيس شخصية جديدة"):
            st.session_state.game_state = {"is_created": False}
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)
            st.session_state.messages = []
            st.rerun()

# --- 5. حلبة اللعب الرئيسية والتبويبات ---
tab_chat, tab_profile, tab_log = st.tabs(["⚔️ حلبة القتال والقصة", "📊 بيانات الشخصية والعلاقات", "📖 أرشيف السجل"])

with tab_chat:
    col_v1, col_v2, col_v3 = st.columns([2, 1, 2])
    with col_v1:
        st.markdown(f"<div class='stat-card-storm'><h3 style='color:#00F0FF; margin:0;'>{state.get('name')}</h3><p style='margin:0;'>HP: {health_val}% | الشاكرا: {chakra_val}%</p></div>", unsafe_allow_html=True)
    with col_v2:
        st.markdown("<h2 style='text-align:center; color:#FF2A00; font-family:Orbitron; margin:0;'>VS</h2>", unsafe_allow_html=True)
    with col_v3:
        st.markdown(f"<div class='stat-card-storm'><h3 style='color:#FF2A00; margin:0;'>{state.get('active_enemy', 'لا يوجد')}</h3><p style='margin:0;'>HP: {state.get('enemy_health', 100)}%</p></div>", unsafe_allow_html=True)

    st.write("")
    st.info(f"📍 **الموقع:** {state.get('location')} | 🎯 **الموقف:** {state.get('current_situation')}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.markdown("---")
    st.markdown("#### 🎮 لوحة الأوامر التكتيكية")
    
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    action_prompt = None

    with b_col1:
        selected_jutsu = st.selectbox("🌀 اختر النينجوتسو:", state.get("jutsus", []))
        if st.button("💥 إطلاق النينجوتسو"):
            action_prompt = f"أنفذ تقنية النينجوتسو: ({selected_jutsu}) بهجوم حاسم!"

    with b_col2:
        if st.button("💥 OUGI (التقنية السرية)"):
            if chakra_val >= 60:
                action_prompt = f"أطلق التقنية السرية الكبرى ULTIMATE JUTSU / OUGI: ({state.get('ultimate_jutsu')}) لإبادة الخصم!"
            else:
                st.warning("الشاكرا غير كافية للـ Ougi! (تحتاج 60%+)")

    with b_col3:
        if st.button("🗣️ حوار وتفاوض عميق"):
            action_prompt = "أحاول التحدث بذكاء ودهاء مع الشخصيات بالميدان واستغلال الموقف لصالحي."
        if "Nukenin" in state.get("ninja_type", ""):
            if st.button("🥷 اختفاء وتملص من الأنبو"):
                action_prompt = "أستخدم أساليب التمويه والاختفاء للهروب من أنظار فرق الأنبو والصيادين."

    with b_col4:
        if st.button("🛡️ KAWARIMI (استبدال)"):
            if sub_val > 0:
                state["substitutions"] -= 1
                action_prompt = "أستخدم شخطه استبدال (Substitution Kawarimi) للظهور خلف الخصم ومباغتته!"
                save_state(state)
            else:
                st.error("نفدت شخطات الاستبدال!")

    chat_input = st.chat_input("اكتب حوارك الحر أو قرارك التكتيكي هنا...")
    final_input = action_prompt or chat_input

    if final_input:
        if not api_key:
            st.error("أدخل Gemini API Key في القائمة الجانبية أولاً!")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": final_input})
        with st.chat_message("user"):
            st.markdown(final_input)

        client = genai.Client(api_key=api_key)

        contents = []
        for m in st.session_state.messages[-12:]:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))

        system_instruction = f"""
أنت Game Master خبير ومبدع بعالم مانجا Naruto Shippuden الرسمية للرولبلي العميق (طراز Character.AI + ميكانيكيات Storm 4).

قواعد السرد الحازمة والصارمة:
1. التزم بالـ Canon الرسمي لمانجا ماساشي كيشيموتو وأجوائها الداكنة.
2. إذا كان اللاعب "نينجا هارب" (Nukenin)، فعامله بقسوة عالم النينجا؛ فرق الأنبو والنينجا الصيادون يطاردونه، والقرى لا ترحمه. رفع مستوى `anbu_heat` أو زيادة `bounty` يجب أن يتغير حسب أفعاله.
3. لا تجامل اللاعب إطلاقاً؛ القرارات الخاطئة والكلمات المستفزة تؤدي إلى ردود فعل قاسية (هجوم مباغت، انقطاع ثقة، إصابات بليغة، أو وقوع في كمين).
4. الشخصيات (مثل كاكاشي، إيتاشي، باين، أوروتشيمارو، تسونادي، ساسكي) تتحدث بلسانها ونبرتها الرسمية الحقيقية بذكاء وعمق.
5. تحديث الـ EXP والمستوى: عند الفوز بمعركة أو تجاوز موقف حرج، زد نقاط الـ `exp`. وعند الوصول لـ 100، ارفع الـ `level` وأضف مهارة جديدة لـ `jutsus`.
6. يمكنك إضافة غنائم جديدة لـ `inventory` وتحديث `relationships` و `location` بشكل ديناميكي.

حالة اللعبة الحالية بـ Database:
{json.dumps(st.session_state.game_state, ensure_ascii=False)}

قم بإرجاع الرد كـ JSON يطابق GameResponse Schema حصراً.
"""

        with st.chat_message("assistant"):
            with st.spinner("جاري كتابة المشهد ومعالجة أحداث القصة..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.75,
                            response_mime_type="application/json",
                            response_schema=GameResponse,
                        )
                    )
                    
                    clean_str = clean_json_response(response.text)
                    game_res = GameResponse.model_validate_json(clean_str)
                    
                    new_state = game_res.updated_state.model_dump()
                    new_state["health"] = clamp(new_state["health"])
                    new_state["chakra"] = clamp(new_state["chakra"])
                    new_state["substitutions"] = clamp(new_state["substitutions"], 0, 4)
                    new_state["anbu_heat"] = clamp(new_state.get("anbu_heat", 0))
                    
                    st.session_state.game_state = new_state
                    save_state(new_state)
                    
                    story_text = game_res.story_narration
                    st.markdown(story_text)
                    st.session_state.messages.append({"role": "assistant", "content": story_text})
                    st.rerun()

                except Exception as e:
                    st.error(f"حدث خطأ أثناء معالجة القصة: {str(e)}")

with tab_profile:
    st.markdown("### 📊 بيانات الشخصية السريعة")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown(f"<div class='stat-card-storm'><h4>👁️ الحد الجيني والقدرة</h4><p>{state.get('kekkei_genkai')}</p></div>", unsafe_allow_html=True)
        st.write("")
        st.subheader("⚡ النينجوتسو والتقنيات:")
        for j in state.get("jutsus", []):
            st.markdown(f"• **{j}**")
        st.write("")
        st.subheader("💥 التقنية السرية والصلابة:")
        st.markdown(f"• **Ougi:** {state.get('ultimate_jutsu')}")
        st.markdown(f"• **Awakening:** {state.get('awakening_type')}")

    with col_p2:
        st.markdown(f"<div class='stat-card-storm'><h4>🎖️️ التصنيف والخبرة</h4><p>المستوى: {state.get('level', 1)} | EXP: {state.get('exp', 0)}/100</p></div>", unsafe_allow_html=True)
        st.write("")
        st.subheader("🎒 الحقيبة والعتاد الميداني:")
        for item in state.get("inventory", []):
            st.markdown(f"• **{item}**")
        st.write("")
        st.subheader("👥 شبكة العلاقات:")
        for npc, rel_status in state.get("relationships", {}).items():
            st.markdown(f"• **{npc}:** {rel_status}")

with tab_log:
    st.markdown("### 📖 أرشيف القصة وسجل القرارات")
    st.info(f"🎯 **الموقف الراهن:** {state.get('current_situation')}")
    st.caption(f"📜 **طريق النينجا (Nindo):** {state.get('nindo')}")
    st.divider()
    for log in state.get("story_log", []):
        st.markdown(f"• {log}")
