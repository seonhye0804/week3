# app.py
import requests
import streamlit as st
from datetime import datetime

from openai import OpenAI


# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="날씨 기반 심리 테스트",
    page_icon="🌦️",
    layout="wide",
)

st.title("🌦️ 날씨 기반 심리 테스트")
st.caption("오늘의 날씨 + 당신의 선택을 분석해서 성격과 잘 맞는 '날씨 타입'을 알려드려요 ☁️✨")


# =========================
# 사이드바: API 키 입력
# =========================
with st.sidebar:
    st.header("🔑 API 설정")

    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="심리 분석 결과 생성에 필요합니다.",
    )

    owm_api_key = st.text_input(
        "OpenWeatherMap API Key",
        type="password",
        placeholder="OpenWeatherMap key",
        help="오늘의 날씨 정보를 불러올 때 필요합니다.",
    )

    st.divider()
    st.caption("⚙️ 키가 없으면 앱은 동작하지만, 날씨/AI 분석은 제한됩니다.")


# =========================
# 날씨 API 함수
# =========================
def get_weather(city: str, api_key: str):
    """
    OpenWeatherMap 현재 날씨 가져오기
    - 한국어
    - 섭씨
    실패 시 None 반환
    """
    if not api_key:
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "kr",
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200:
            return None

        data = res.json()

        weather_desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind = data.get("wind", {}).get("speed", None)

        return {
            "city": city,
            "description": weather_desc,
            "temp_c": float(temp),
            "feels_like_c": float(feels_like),
            "humidity": int(humidity),
            "wind_mps": wind,
        }

    except Exception:
        return None


# =========================
# OpenAI 분석 함수
# =========================
def generate_psychology_result(openai_key: str, weather: dict | None, answers: dict):
    """
    - 답변 5개 + 날씨를 입력으로 받아
    - 심리 결과 + 어울리는 날씨 타입 + 잘 맞는 성격 설명
    """
    if not openai_key:
        return None

    # 날씨 텍스트
    if weather:
        wind_txt = f"{weather['wind_mps']}m/s" if weather.get("wind_mps") is not None else "정보 없음"
        weather_text = (
            f"- 도시: {weather['city']}\n"
            f"- 날씨: {weather['description']}\n"
            f"- 기온: {weather['temp_c']:.1f}°C (체감 {weather['feels_like_c']:.1f}°C)\n"
            f"- 습도: {weather['humidity']}%\n"
            f"- 바람: {wind_txt}\n"
        )
    else:
        weather_text = "날씨 정보 없음"

    # 답변 텍스트
    answers_text = "\n".join([f"- Q{i+1}: {a}" for i, a in enumerate(answers.values())])

    system_prompt = """
너는 '날씨 기반 심리 테스트' 전문가다.
사용자의 5개 답변과 오늘의 날씨를 종합해서,
심리 분석 결과를 흥미롭고 설득력 있게 제시한다.

조건:
- 절대 단정적으로 진단하지 말고, 심리테스트 느낌으로 재미있게.
- 과장하지 말고, 현실적인 조언을 포함.
- 한국어로 작성.
- 너무 길지 않게(약 15~25줄).
"""

    user_prompt = f"""
아래는 사용자의 심리테스트 답변과 오늘의 날씨다.

[오늘의 날씨]
{weather_text}

[사용자 답변 5개]
{answers_text}

요구 출력 형식(반드시 지켜라):

[당신의 핵심 성격 요약]
- 한 줄 요약

[심리 분석]
- 4~6줄

[오늘의 날씨가 당신에게 주는 의미]
- 2~4줄

[당신과 가장 잘 어울리는 날씨 타입]
- (예: 맑고 선선한 날 / 비 오는 밤 / 눈 오는 새벽 등)

[그 날씨와 잘 맞는 사람의 성격]
- 4~6줄

[오늘의 추천 행동 3가지]
- 3줄 (구체적으로)

[한 문장 엔딩]
- 한 줄
""".strip()

    try:
        client = OpenAI(api_key=openai_key)
        res = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
        )
        return res.choices[0].message.content.strip()

    except Exception:
        return None


# =========================
# UI: 도시 선택 + 오늘 날짜
# =========================
st.subheader("📍 오늘의 날씨 설정")

city_list = [
    "Seoul",
    "Busan",
    "Incheon",
    "Daegu",
    "Daejeon",
    "Gwangju",
    "Suwon",
    "Ulsan",
    "Jeju",
    "Changwon",
]

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    city = st.selectbox("도시 선택", city_list, index=0)

with col2:
    st.write("🗓️ 오늘 날짜")
    st.info(datetime.now().strftime("%Y-%m-%d (%a)"))


# =========================
# 날씨 가져오기 버튼
# =========================
weather = None
if "weather_cache" not in st.session_state:
    st.session_state.weather_cache = None

get_weather_btn = st.button("🌦️ 오늘의 날씨 불러오기", use_container_width=True)

if get_weather_btn:
    with st.spinner("날씨를 불러오는 중..."):
        st.session_state.weather_cache = get_weather(city, owm_api_key)

weather = st.session_state.weather_cache


# =========================
# 날씨 카드 출력
# =========================
st.markdown("---")
st.subheader("🌤️ 오늘의 날씨")

if weather:
    c1, c2, c3, c4 = st.columns(4, gap="medium")

    c1.metric("도시", weather["city"])
    c2.metric("날씨", weather["description"])
    c3.metric("기온(°C)", f"{weather['temp_c']:.1f}")
    c4.metric("체감(°C)", f"{weather['feels_like_c']:.1f}")

    st.caption(
        f"습도 {weather['humidity']}% / "
        f"바람 {weather['wind_mps']}m/s" if weather.get("wind_mps") is not None else "바람 정보 없음"
    )
else:
    st.warning("날씨 정보가 아직 없어요. (API Key 입력 후 버튼을 눌러주세요)")


# =========================
# 심리 테스트 질문 5개
# =========================
st.markdown("---")
st.subheader("🧠 심리 테스트 (총 5문항)")

st.write("아래 질문에 답하면 AI가 당신의 성격과 어울리는 '날씨 타입'을 분석해줘요!")

questions = [
    {
        "q": "Q1. 갑자기 하루가 통째로 비었다! 당신은?",
        "options": [
            "계획부터 짠다. 효율적으로 꽉 채운다.",
            "그때그때 끌리는 대로 움직인다.",
            "집에서 푹 쉬면서 에너지를 충전한다.",
            "친구를 불러서 같이 놀자고 한다.",
        ],
    },
    {
        "q": "Q2. 스트레스를 받았을 때 당신의 방식은?",
        "options": [
            "운동/산책처럼 몸을 움직이며 푼다.",
            "혼자 조용히 생각하며 정리한다.",
            "누군가에게 털어놓고 공감받는다.",
            "맛있는 걸 먹거나 쇼핑으로 풀어버린다.",
        ],
    },
    {
        "q": "Q3. 새로운 사람을 만날 때 나는?",
        "options": [
            "먼저 말을 걸고 분위기를 만든다.",
            "상대가 편해질 때까지 천천히 본다.",
            "상대 성향을 파악한 뒤 맞춰준다.",
            "필요할 때만 사회력을 발동한다.",
        ],
    },
    {
        "q": "Q4. 일이 꼬였을 때 당신의 반응은?",
        "options": [
            "원인을 분석하고 해결 루트를 찾는다.",
            "일단 감정이 올라오고 잠깐 멈춘다.",
            "‘될 대로 되라’ 모드로 흘려보낸다.",
            "주변 도움을 받아 빠르게 수습한다.",
        ],
    },
    {
        "q": "Q5. 당신이 가장 끌리는 하루의 분위기는?",
        "options": [
            "햇살 좋은 낮, 가볍게 바쁘게 움직이는 날",
            "비 오는 밤, 조용히 감성적인 날",
            "바람 부는 날, 뭔가 새로 시작하고 싶은 날",
            "눈 오는 날, 따뜻한 곳에서 포근한 날",
        ],
    },
]

answers = {}

for i, item in enumerate(questions):
    answers[f"Q{i+1}"] = st.radio(
        item["q"],
        item["options"],
        index=0,
        key=f"q_{i}",
    )


# =========================
# 분석 버튼
# =========================
st.markdown("---")
st.subheader("📌 결과 보기")

analyze_btn = st.button("✨ 답변 분석 & 결과 생성", type="primary", use_container_width=True)

if "result_cache" not in st.session_state:
    st.session_state.result_cache = None

if analyze_btn:
    with st.spinner("AI가 날씨와 답변을 종합 분석 중..."):
        result = generate_psychology_result(
            openai_key=openai_api_key,
            weather=weather,
            answers=answers,
        )
        st.session_state.result_cache = result

result = st.session_state.result_cache


# =========================
# 결과 출력
# =========================
if result:
    st.markdown("## 🎯 당신의 결과")
    st.markdown(result)

    st.markdown("---")
    st.subheader("📤 공유용 텍스트")
    share_text = f"""
[날씨 기반 심리 테스트 결과]

- 도시: {city}
- 날씨: {weather['description'] if weather else '날씨 정보 없음'}
- 기온: {weather['temp_c']:.1f}°C (체감 {weather['feels_like_c']:.1f}°C) if weather else '-'

[내 답변]
1) {answers['Q1']}
2) {answers['Q2']}
3) {answers['Q3']}
4) {answers['Q4']}
5) {answers['Q5']}

--- 결과 ---
{result}
""".strip()

    st.code(share_text, language="text")

elif analyze_btn:
    st.error("결과를 생성하지 못했어요. (OpenAI API Key 확인 / 날씨는 없어도 가능)")


# =========================
# 하단: 안내
# =========================
st.markdown("---")
with st.expander("📌 API 안내 / 실행 방법"):
    st.markdown(
      

