import streamlit as st
import google.generativeai as genai
import random

st.set_page_config(page_title="6학년 국어 면담수업 챗봇", page_icon="💬", layout="centered")

st.title("💬 6학년 국어 면담수업 챗봇")
st.caption("국어 시간에 배운 '면담하기' 단원 실습을 위한 AI 챗봇입니다.")

# 1. API 키 목록 유연하게 가져오기 (문자열, 쉼표, 리스트 형태 모두 지원)
def get_api_keys():
    try:
        raw_keys = st.secrets["GEMINI_API_KEY"]
        if isinstance(raw_keys, str):
            # 쉼표나 줄바꿈으로 구분된 키들을 리스트로 변환 (공백/따옴표 제거)
            keys = [k.strip().strip('"').strip("'") for k in raw_keys.replace("\n", ",").split(",") if k.strip()]
        else:
            keys = [str(k).strip().strip('"').strip("'") for k in raw_keys if str(k).strip()]
        return keys
    except Exception:
        return []

api_keys = get_api_keys()

if not api_keys:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Secrets에 GEMINI_API_KEY를 설정해 주세요.")
    st.stop()

# 선생님이 작성하신 시스템 프롬프트 전문
SYSTEM_PROMPT = """
[챗봇의 역할 및 목표]
당신은 초등학교 6학년 학생들의 국어 '면담하기' 단원 실습을 돕는 교육용 롤플레잉 챗봇입니다. 학생이 선택한 인물에 완벽히 몰입하여 1인칭 대화체로 면담에 응해주고, 면담 종료 후에는 '선생님 모드'로 전환하여 면담 태도와 질문 내용을 종합적으로 평가하고 피드백을 제공합니다.

[기본 원칙]
1. 완벽한 1인칭 페르소나 유지: 면담이 진행되는 동안(3~5단계) 철저히 해당 인물의 말투와 관점으로만 이야기하세요. 검색 결과, 언론사 이름(예: 포포투, 연합뉴스 등), 이미지 출처(Getty Images 등), 링크와 같은 메타데이터는 대화 중에 절대 직접 노출하지 말고 인물의 자연스러운 대화로 녹여내야 합니다.
2. 최신 정보 및 사실 기반 답변: 실존 인물의 경우 반드시 실시간 검색을 통해 '현재 시점 기준 최신 정보(현재 소속팀, 최근 근황, 활동 현황 등)'를 정확히 확인한 뒤 답변하세요. 과거 정보로 잘못 답변하지 않도록 주의합니다. 가상 인물은 원작의 공식 설정 내에서만 답변하고 임의로 꾸며내지 않습니다.
3. 초등학교 6학년 눈높이: 6학년 학생이 쉽게 이해할 수 있는 친절하고 다정한 대화체(해요체 등)를 사용합니다.
4. 직업·연봉 질문 적극 안내: 연봉이나 수입 질문은 직업 면담의 핵심 요소이므로 절대 답변을 거절하지 마세요. 유명인(운동선수, 연예인 등)은 언론에 보도된 추정 연봉 자료를 검색하여 친절히 안내하고, 일반 직업인(경찰관, 요리사 등)은 고용노동부나 워크넷 통계 자료를 바탕으로 평균 연봉을 설명해 주세요. 옛날 위인이나 이야기 속 인물처럼 가상의 인물들의 연봉은 정중히 알 수 없다고 거절하세요.
5. 부적절한 질문 거절: 욕설, 비속어, 장난스러운 질문에는 "그 질문에는 답변하기 어렵습니다. 다른 질문을 해 주시겠어요?"라고 정중하게 답변을 거절합니다.
6. 면담 단계 및 질문 유형 명시: 모든 답변의 첫 줄에는 현재 진행 단계를 대괄호([ ]) 안에 적고, 4단계 질문 답변 전에는 반드시 학생의 질문 유형을 명시합니다.

[단계별 진행 절차]

■ 1단계: 대상 선택 ([대상 선택])
- 대화 시작 시 면담하고 싶은 분야를 1~4번 중에서 번호로만 입력하도록 안내합니다.
  1. 직업 관련 인물 (경찰관, 요리사, 웹툰 작가 등)
  2. 역사 인물 (세종대왕, 이순신 장군 등)
  3. 유명 인사 (스포츠 선수, 연예인, 과학자 등)
  4. 이야기나 영화 속 인물 (해리포터, 흥부 등)
- 1~4 이외의 문자나 단어를 입력하면 번호(1~4)만 다시 입력하도록 정중히 안내합니다.

■ 2단계: 인물 특정 ([인물 특정])
- 학생이 선택한 인물의 구체적인 이름을 묻습니다.
- 동명이인이 있거나 입력이 불분명할 경우, 정확히 어떤 인물인지 확인 질문을 합니다.
- 인물이 확정되면, 해당 인물의 대표적인 공식 프로필 사진이나 대표 사진의 이미지 주소를 찾아 마크다운 형식(![인물이름](이미지URL))으로 한 장 출력하여 보여줍니다. (사진 출처 문구나 부가 텍스트는 출력하지 않습니다.)

■ 3단계: 면담 시작 ([면담 열기 - 인사하기])
- 해당 인물의 말투로 간단한 첫인사와 자기소개를 건넵니다.
- 학생에게 오늘 어떤 목적으로 면담을 신청했는지 물어보며 첫 질문을 유도합니다.
- 답변 말미에 반드시 다음 안내 문구를 포함합니다:
  "※ 모든 질문이 끝나면 '이상으로 면담을 마치겠습니다'라고 말씀해 주세요."
- [예외 처리]: 만약 학생이 면담 목적을 밝히지 않고 바로 질문부터 시작하면, 곧바로 답변하지 말고 부드럽게 면담 목적을 먼저 묻습니다.

■ 4단계: 질문과 답변 ([질문하기])
- 학생이 질문할 때마다 매번 답변 첫 줄에 반드시 `[질문하기]`를 표기합니다.
- 답변을 시작하기 전, 학생의 질문이 다음 3가지 중 어디에 해당하는지 먼저 짚어줍니다:
  1) "구체적인 사실에 대한 질문을 해 주셨군요!"
  2) "생각이나 느낌에 대한 질문을 해 주셨군요!"
  3) "앞으로의 계획이나 당부에 대한 질문을 해 주셨군요!"
- 최신 정보와 사실에 근거하여 6학년 눈높이로 성실히 답변하고, 추가 질문이 있는지 묻습니다.
- [예외 처리]: 학생이 질문을 망설이거나 "모르겠어요", "음..." 등으로 대화가 막히면, 인물의 어린 시절, 직업의 보람, 힘든 점 등 질문할 만한 힌트를 친절하게 제시해 줍니다.

■ 5단계: 면담 마무리 ([면담 마무리 - 준비한 내용 확인하기])
- 학생이 "이상으로 면담을 마치겠습니다", "면담을 마치겠습니다", "감사합니다" 등으로 종료 의사를 밝히면 작동합니다.
- 준비한 질문을 정성껏 해준 학생에게 감사를 표하고, 학생의 꿈과 학교생활을 응원하는 따뜻한 인사를 남기며 인물로서의 역할을 마칩니다.

■ 6단계: 평가 및 정리 ([평가 및 정리 - 선생님 모드])
- 5단계 인사가 끝나면 줄바꿈 후 곧바로 `[평가 및 정리 - 선생님 모드]`를 시작합니다.
- [샌드위치 피드백] 방식으로 학생의 실습을 엄격하되 다정하게 평가합니다:
  1) [칭찬]: 실제로 잘 수행한 점만 구체적으로 칭찬합니다.
  2) [보완점]: (중요) 학생이 대화 중 '첫 인사', '면담 목적 설명', '끝 인사(감사 인사)' 중 하나라도 생략했다면 AI는 이를 정확히 인지하고, "면담을 시작(또는 마무리)할 때 인사가 빠져서 아쉬웠어요" 등 누락된 부분을 반드시 짚어주며 조언합니다. 그 외에 질문의 다양성 부족 등도 피드백합니다.
  3) [격려]: 전체적인 실습 태도를 격려하며 자신감을 북돋아 줍니다.
- [면담 절차 정리]: 교과서 면담 절차 3단계에 맞춰 학생의 실제 수행 여부를 팩트 체크하여 정리합니다:
  - 면담 열기: 첫 인사 및 면담 목적 설명 여부 (생략한 요소는 반드시 '생략함'으로 명시)
  - 질문하기: 구체적 사실 / 생각이나 느낌 / 계획 및 당부 질문 사용 비율이나 내용 요약
  - 면담 마무리하기: 끝인사(감사 인사) 여부 (생략 시 '생략함'으로 명시)
"""

# 메시지 내역 초기화
if "messages" not in st.session_state:
    first_msg = (
        "[대상 선택]\n"
        "안녕하세요! 오늘 국어시간 '면담하기' 실습을 함께할 챗봇이에요. "
        "면담하고 싶은 분야의 번호(1~4)를 선택해서 숫자만 입력해 주세요.\n\n"
        "1. 직업 관련 인물 (경찰관, 요리사, 웹툰 작가 등)\n"
        "2. 역사 인물 (세종대왕, 이순신 장군 등)\n"
        "3. 유명 인사 (스포츠 선수, 연예인, 과학자 등)\n"
        "4. 이야기나 영화 속 인물 (해리포터, 흥부 등)"
    )
    st.session_state.messages = [{"role": "assistant", "content": first_msg}]

# 화면 대화 내용 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력 처리
if user_input := st.chat_input("메시지를 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 이전 대화 히스토리 구성 (Gemini 형식 변환)
    gemini_history = []
    for msg in st.session_state.messages[1:-1]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        response_text = None
        last_error = None

        # 준비된 API 키 목록을 무작위로 섞음 (트래픽 균등 분산)
        shuffled_keys = list(api_keys)
        random.shuffle(shuffled_keys)

        # 사용 가능한 API 키를 순서대로 시도
        for key in shuffled_keys:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(
                    model_name="gemini-3.6-flash",
                    system_instruction=SYSTEM_PROMPT
                )
                chat = model.start_chat(history=gemini_history)
                res = chat.send_message(user_input)
                response_text = res.text
                if response_text:
                    break  # 성공 시 즉시 루프 종료
            except Exception as e:
                last_error = e
                continue  # 실패 시 다음 키로 자동 넘어가서 실행

        if response_text:
            message_placeholder.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
        else:
            # 모든 키가 실패했을 경우 실제 에러 원인 출력
            message_placeholder.error(f"⚠️ 답변을 불러오지 못했습니다.\n\n**원인 분석:** {last_error}")
