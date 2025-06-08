import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import time
from typing import Optional
import json
from datetime import datetime

def extract_text_from_url(url: str) -> str:
    """
    URL에서 본문 텍스트를 추출합니다.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 메타 태그에서 제목 추출
        title = soup.find('title')
        title_text = title.get_text() if title else ''
        
        # 본문 텍스트 추출
        # 일반적인 본문 태그들
        content_tags = soup.find_all(['p', 'article', 'div', 'section'])
        content_text = ' '.join([tag.get_text().strip() for tag in content_tags])
        
        # 제목과 본문 결합
        full_text = f"{title_text}\n\n{content_text}"
        
        return full_text.strip()
    except Exception as e:
        print(f"Error extracting text from {url}: {str(e)}")
        return ""

def parse_gemini_text_fields(text: str) -> dict:
    """Gemini 응답을 파싱하여 딕셔너리로 변환 (디버깅 강화)"""
    print(f"parse_gemini_text_fields 입력 텍스트:")
    print("=" * 40)
    print(text)
    print("=" * 40)
    
    result = {}
    for line in text.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            print(f"파싱 중 - 키: '{key}', 값: '{value}'")
            
            # 빈 값 처리
            if not value or value.lower() in ['없음', 'none', '-', '정보 없음']:
                if key in ["카테고리", "태그"]:
                    result[key] = []
                elif key == "전송됨":
                    result[key] = True
                elif key == "등록일":
                    result[key] = datetime.now().strftime('%Y-%m-%d')
                elif key == "출처":
                    result[key] = "Discord"
                else:
                    result[key] = ""
            else:
                result[key] = value
    
    # 리스트로 변환이 필요한 항목 처리
    for k in ["카테고리", "태그"]:
        if k in result and isinstance(result[k], str):
            print(f"리스트 변환 전 - {k}: '{result[k]}' (타입: {type(result[k])})")
            
            # JSON 배열 문자열인지 확인
            if result[k].startswith('[') and result[k].endswith(']'):
                try:
                    parsed = json.loads(result[k])
                    if isinstance(parsed, list):
                        result[k] = [item.strip() for item in parsed if item and str(item).strip()]
                        print(f"JSON 배열로 파싱 성공 - {k}: {result[k]}")
                        continue
                except (json.JSONDecodeError, TypeError):
                    print(f"JSON 파싱 실패, 쉼표 분리로 처리 - {k}")
            
            # 쉼표로 분리하고 각 항목을 정리
            items = [v.strip() for v in result[k].split(',') if v.strip()]
            # 너무 긴 항목은 제거 (100자 제한)
            result[k] = [item for item in items if len(item) <= 100]
            print(f"리스트 변환 후 - {k}: {result[k]} (타입: {type(result[k])})")
    
    # 전송됨(체크박스) 처리
    if "전송됨" in result:
        result["전송됨"] = str(result["전송됨"]).lower() == "true"
    
    # URL 정리
    if "URL" not in result:
        result["URL"] = ""
    
    print(f"parse_gemini_text_fields 최종 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

def flatten_fields_for_airtable(data: dict) -> dict:
    """
    Airtable에 보낼 때 리스트 필드를 쉼표로 연결된 문자열로 변환합니다.
    JSON 문자열로 된 배열도 처리합니다.
    """
    print(f"flatten_fields_for_airtable 입력 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    result = data.copy()
    
    for k in ["카테고리", "태그"]:
        if k in result:
            value = result[k]
            print(f"flatten_fields_for_airtable - {k} 원본값: {value} (타입: {type(value)})")
            
            if isinstance(value, list):
                # 이미 리스트인 경우
                if value:  # 빈 리스트가 아닌 경우만
                    result[k] = ", ".join(str(item) for item in value if item)
                    print(f"flatten_fields_for_airtable - {k} 리스트->문자열 변환: '{result[k]}'")
                else:
                    result[k] = ""
                    print(f"flatten_fields_for_airtable - {k} 빈 리스트->빈 문자열")
                    
            elif isinstance(value, str):
                # 문자열인 경우, JSON 배열 문자열인지 확인
                if value.startswith('[') and value.endswith(']'):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            result[k] = ", ".join(str(item) for item in parsed if item)
                            print(f"flatten_fields_for_airtable - {k} JSON문자열->문자열 변환: '{result[k]}'")
                        else:
                            print(f"flatten_fields_for_airtable - {k} JSON이지만 리스트가 아님: {parsed}")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"flatten_fields_for_airtable - {k} JSON 파싱 실패: {e}")
                        # JSON이 아닌 일반 문자열은 그대로 유지
                else:
                    print(f"flatten_fields_for_airtable - {k} 일반 문자열 유지: '{value}'")
            else:
                print(f"flatten_fields_for_airtable - {k} 예상치 못한 타입: {type(value)}")
    
    print(f"flatten_fields_for_airtable 최종 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result

def gemini_extract_notion_fields(text: str, url: str, api_key: str) -> dict:
    """
    Gemini API를 사용하여 Airtable용 6개 필드만 추출합니다.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = f"""
아래 웹사이트({url})에 대해 다음 정보를 한국어로 자세히 정리해줘.
각 항목은 반드시 한 줄에 하나씩, "키: 값" 형태로만 출력해줘.

**중요 지침:**
1. 카테고리는 JSON 형태로 출력하지 말고, 단순히 쉼표로 구분된 텍스트로만 출력해줘.
2. 평가/효용성은 반드시 '높음', '보통', '낮음' 중 하나만 써줘.
3. 요약 설명은 최소 200자 이상으로 상세하게 작성해줘. 다음 내용을 포함해야 함:
   - 서비스/도구의 주요 기능과 특징
   - 어떤 문제를 해결하는지
   - 사용 방법이나 특별한 장점
   - 누가 사용하면 좋은지
   - 비슷한 서비스와의 차이점이나 독특한 점

4. **중요**: 스크립트는 60초 영상 기준으로 작성해줘!
   - 한국어 스크립트: 400-500자 분량 (60초 기준)
   - 영어 스크립트: 400-500자 분량 (60초 기준)
   - 더 자세한 설명과 예시를 포함해서 작성

**출력 형식:**
사이트 이름: [웹사이트나 서비스의 정확한 이름]
URL: [제공된 URL 그대로]
카테고리: [관련 카테고리들을 쉼표로 구분하여 최대 5개까지]
활용 사례: [구체적인 사용 사례나 시나리오를 150자 이상으로 상세히 설명]
평가/효용성: [높음/보통/낮음 중 하나만]
요약 설명: [200자 이상의 상세한 설명으로, 위에서 언급한 모든 요소를 포함하여 작성]
스크립트: [유튜브 60초 길이의 매력적인 스크립트 형태로 작성. 시작은 강력한 hook으로, 핵심 기능 소개, 구체적인 사용 예시, 장점 설명, 마무리는 구독 유도나 액션 콜까지 포함하여 400-500자 분량으로 작성]
Script: [영어로 된 유튜브 60초 길이의 매력적인 스크립트. 영어권 시청자를 대상으로 자연스러운 영어 표현을 사용하여 작성. Hook - Feature Introduction - Detailed Use Case - Benefits - Call to Action 순서로 400-500자 분량]

**예시 (참고용):**
사이트 이름: ChatGPT
URL: https://chat.openai.com
카테고리: AI, 챗봇, 생산성, 업무 도구
활용 사례: 업무용 문서 작성 시 초안 생성, 코딩 문제 해결을 위한 코드 리뷰 및 디버깅 지원, 학습 과정에서 복잡한 개념 설명 요청, 창작 활동을 위한 아이디어 브레인스토밍, 이메일이나 보고서 작성 시 문체 교정 및 개선 제안 등 다양한 텍스트 기반 업무에서 AI 어시스턴트로 활용 가능
평가/효용성: 높음
요약 설명: OpenAI에서 개발한 대화형 인공지능 서비스로, 자연어 처리 기술을 바탕으로 사용자의 질문에 대화 형식으로 답변을 제공합니다. 텍스트 생성, 번역, 요약, 코딩 지원, 창작 등 매우 다양한 작업을 수행할 수 있어 개인 사용자부터 기업까지 폭넓게 활용되고 있습니다. 특히 복잡한 업무를 단순화하고 창의적 사고를 돕는 데 탁월하며, 24시간 언제든지 접근 가능한 점이 큰 장점입니다. 기존의 검색 엔진과 달리 맥락을 이해하고 개인화된 답변을 제공하여 업무 효율성을 크게 향상시킬 수 있습니다.
스크립트: "여러분, 업무 효율을 획기적으로 높이고 싶으신가요? 🚀 오늘 소개할 ChatGPT는 단순한 검색을 넘어선 진짜 AI 동료입니다! 복잡한 보고서 작성부터 코딩 문제 해결까지, 질문만 하면 즉시 맞춤형 답변을 받을 수 있어요. 예를 들어, '마케팅 전략 보고서 초안을 작성해줘'라고 하면 구체적인 내용까지 제안해줍니다. 24시간 언제든 접근 가능하고, 맥락을 이해하는 대화 방식이 정말 혁신적이죠! 기존 도구들과 달리 창의적 사고까지 도와주니까 업무가 완전히 달라집니다. 지금 바로 사용해보시고, 더 많은 생산성 도구가 궁금하다면 구독 버튼 눌러주세요!"
Script: "Want to revolutionize your productivity? 🚀 Meet ChatGPT - your AI colleague that goes way beyond simple searches! From writing complex reports to debugging code, just ask and get instant, personalized answers. For example, ask 'Help me draft a marketing strategy report' and it'll provide detailed suggestions with context. What makes it revolutionary is the 24/7 availability and conversational understanding that feels natural. Unlike traditional tools, it actually helps with creative thinking and complex problem-solving. It's like having a smart assistant who never sleeps and always understands what you need. Try ChatGPT today and transform how you work. Don't forget to subscribe for more productivity game-changers!"

본문:
{text[:8000]}
"""
        print("Gemini 프롬프트:")
        print("=" * 40)
        print(prompt)
        print("=" * 40)
        
        response = model.generate_content(prompt)
        print("Gemini 응답 원문:")
        print("=" * 40)
        print(response.text)
        print("=" * 40)
        
        parsed_data = parse_gemini_text_fields(response.text)
        
        # 8개 필드만 추출 (영어 스크립트 필드 추가)
        fields = ["사이트 이름", "URL", "카테고리", "활용 사례", "평가/효용성", "요약 설명", "스크립트", "Script"]
        filtered_data = {}
        
        for field in fields:
            if field in parsed_data:
                filtered_data[field] = parsed_data[field]
            else:
                # 기본값 설정
                if field == "카테고리":
                    filtered_data[field] = []
                elif field == "URL":
                    filtered_data[field] = url
                else:
                    filtered_data[field] = ""
        
        print(f"필터링된 6개 필드 데이터: {json.dumps(filtered_data, ensure_ascii=False, indent=2)}")
        
        return filtered_data
        
    except Exception as e:
        print(f"Error extracting notion fields: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        # 에러 발생 시 기본 데이터 반환
        return {
            "사이트 이름": "제목 없음",
            "URL": url,
            "카테고리": [],
            "활용 사례": "",
            "평가/효용성": "보통",
            "요약 설명": "요약 생성 실패",
            "스크립트": "스크립트 생성 실패",
            "Script": "Script generation failed"
        }