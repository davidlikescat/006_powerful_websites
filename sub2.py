import requests
from typing import Optional, Dict, List
import json
from datetime import datetime
import re
import urllib.parse

# 프로퍼티 매핑 (코드에서 사용하는 이름 -> 실제 Notion 프로퍼티명)
PROPERTY_MAPPING = {
    "사이트 이름": "사이트 이름",
    "URL": "URL",
    "카테고리": "카테고리",
    "활용 사례": "활용 사례",
    "평가/효용성": "평가/효용성",
    "요약 설명": "요약 설명 (Gemini)",
    "추천 대상": "추천 대상",
    "태그": "태그 (키워드)",
    "출처": "출처",
    "추가 참고 링크": "추가 참고 링크",
    "등록일": "등록일",
    "전송됨": "전송됨 (텔레그램)"
}

def normalize_url(url: str) -> str:
    """URL을 정규화하여 비교 가능한 형태로 만듭니다."""
    if not url:
        return ""
    
    # 기본적인 정리
    url = url.strip().lower()
    
    # http/https 통일 (https로)
    if url.startswith('http://'):
        url = url.replace('http://', 'https://', 1)
    
    # www. 제거
    if '://www.' in url:
        url = url.replace('://www.', '://')
    
    # 끝의 슬래시 제거
    if url.endswith('/'):
        url = url.rstrip('/')
    
    # URL 쿼리 파라미터 제거 (선택적 - 필요에 따라 주석 처리)
    # parsed = urllib.parse.urlparse(url)
    # url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    return url

def check_duplicate_url_airtable(api_key: str, base_id: str, table_name: str, url: str) -> Dict:
    """
    Airtable에서 URL 중복을 확인합니다.
    
    Returns:
        dict: {
            "is_duplicate": bool,
            "record_id": str or None,
            "existing_data": dict or None,
            "error": str or None
        }
    """
    try:
        print(f"🔍 중복 URL 확인 중: {url}")
        
        # URL 정규화
        normalized_url = normalize_url(url)
        print(f"   정규화된 URL: {normalized_url}")
        
        # Airtable API 요청 준비
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 필터 조건 생성 - URL 필드에서 검색
        # Airtable formula를 사용하여 정규화된 URL로 검색
        filter_formula = f"LOWER(SUBSTITUTE(SUBSTITUTE({{URL}}, 'http://', 'https://'), 'www.', '')) = '{normalized_url}'"
        
        url_encoded_formula = urllib.parse.quote(filter_formula)
        request_url = f"https://api.airtable.com/v0/{base_id}/{table_name}?filterByFormula={url_encoded_formula}"
        
        print(f"   검색 URL: {request_url}")
        print(f"   필터 공식: {filter_formula}")
        
        response = requests.get(request_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Airtable 검색 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            return {
                "is_duplicate": False,
                "record_id": None,
                "existing_data": None,
                "error": f"Airtable API 오류: {response.status_code}"
            }
        
        data = response.json()
        records = data.get('records', [])
        
        if records:
            # 중복 발견
            existing_record = records[0]  # 첫 번째 레코드 사용
            record_id = existing_record.get('id')
            existing_data = existing_record.get('fields', {})
            
            print(f"⚠️ 중복 URL 발견!")
            print(f"   레코드 ID: {record_id}")
            print(f"   기존 사이트 이름: {existing_data.get('사이트 이름', 'N/A')}")
            print(f"   기존 등록일: {existing_data.get('등록일', 'N/A')}")
            
            return {
                "is_duplicate": True,
                "record_id": record_id,
                "existing_data": existing_data,
                "error": None
            }
        else:
            # 중복 없음
            print(f"✅ 새로운 URL - 중복 없음")
            return {
                "is_duplicate": False,
                "record_id": None,
                "existing_data": None,
                "error": None
            }
            
    except Exception as e:
        print(f"❌ 중복 확인 중 오류: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "is_duplicate": False,
            "record_id": None,
            "existing_data": None,
            "error": str(e)
        }

def update_airtable_record(api_key: str, base_id: str, table_name: str, record_id: str, data: dict) -> bool:
    """
    Airtable의 기존 레코드를 업데이트합니다.
    """
    try:
        print(f"🔄 기존 레코드 업데이트 중: {record_id}")
        
        url = f"https://api.airtable.com/v0/{base_id}/{table_name}/{record_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 데이터 검증 및 정리
        cleaned_data = {}
        for key, value in data.items():
            if value is not None and value != "":
                # 문자열 길이 제한
                if isinstance(value, str) and len(value) > 100000:
                    value = value[:100000]
                cleaned_data[key] = value
        
        payload = {
            "fields": cleaned_data
        }
        
        print(f"업데이트할 데이터: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.patch(url, headers=headers, json=payload)
        
        print(f"Airtable 업데이트 응답: {response.status_code}")
        print(f"응답 내용: {response.text}")
        
        if response.status_code == 200:
            print("✅ Airtable 레코드 업데이트 성공!")
            return True
        else:
            print(f"❌ Airtable 레코드 업데이트 실패!")
            return False
            
    except Exception as e:
        print(f"❌ 레코드 업데이트 중 오류: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def is_valid_url(url: str) -> bool:
    """URL 유효성 검사"""
    if not url or url.lower() in ['없음', 'none', '', '-']:
        return False
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def format_date_for_notion(date_str: str) -> Optional[str]:
    """Notion용 날짜 형식으로 변환"""
    if not date_str or date_str.lower() in ['정보 없음', 'none', '', '-']:
        return datetime.now().strftime('%Y-%m-%d')
    
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    return datetime.now().strftime('%Y-%m-%d')

def clean_select_value(value: str) -> str:
    """Select 필드용 값 정리 (첫 번째 값만 사용)"""
    if not value or value.lower() in ['없음', 'none', '', '-']:
        return "기타"
    
    # 쉼표로 구분된 경우 첫 번째 값만 사용
    if ',' in value:
        value = value.split(',')[0].strip()
    
    # 길이 제한
    if len(value) > 100:
        value = value[:100-3] + "..."
    
    return value

def truncate_select_value(value: str, max_length: int = 100) -> str:
    """Select 필드용 값 길이 제한 (기존 함수 유지)"""
    return clean_select_value(value)

def send_to_notion_flexible(notion_api_key: str, database_id: str, notion_data: dict, property_mapping: dict = None) -> bool:
    """
    유연한 프로퍼티 매핑을 사용하여 Notion에 데이터를 저장합니다.
    """
    if property_mapping is None:
        property_mapping = PROPERTY_MAPPING
    
    try:
        headers = {
            "Authorization": f"Bearer {notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # 기본 데이터 구조
        data = {
            "parent": {"database_id": database_id},
            "properties": {}
        }
        
        # 사이트 이름 (Title 타입)
        site_name_prop = property_mapping.get("사이트 이름", "Name")
        data["properties"][site_name_prop] = {
            "title": [{"text": {"content": notion_data.get("사이트 이름", "제목 없음")}}]
        }
        
        # URL 필드
        url_prop = property_mapping.get("URL", "URL")
        main_url = notion_data.get("URL", "")
        if is_valid_url(main_url):
            data["properties"][url_prop] = {"url": main_url}
        
        # 카테고리 (Multi-select)
        category_prop = property_mapping.get("카테고리", "Category")
        categories = notion_data.get("카테고리", [])
        if categories:
            data["properties"][category_prop] = {
                "multi_select": [{"name": str(c)[:100]} for c in categories if c and str(c).strip()]
            }
        
        # 활용 사례 (Rich text)
        use_case_prop = property_mapping.get("활용 사례", "Use Cases")
        if notion_data.get("활용 사례"):
            data["properties"][use_case_prop] = {
                "rich_text": [{"text": {"content": str(notion_data.get("활용 사례", ""))[:2000]}}]
            }
        
        # 평가/효용성 (Select)
        rating_prop = property_mapping.get("평가/효용성", "Rating")
        evaluation = truncate_select_value(notion_data.get("평가/효용성", ""))
        if evaluation and evaluation != "기타":
            data["properties"][rating_prop] = {"select": {"name": evaluation}}
        
        # 요약 설명 (Rich text)
        summary_prop = property_mapping.get("요약 설명", "Summary")
        if notion_data.get("요약 설명"):
            data["properties"][summary_prop] = {
                "rich_text": [{"text": {"content": str(notion_data.get("요약 설명", ""))[:2000]}}]
            }
        
        # 추천 대상 (Select)
        target_prop = property_mapping.get("추천 대상", "Target")
        target = truncate_select_value(notion_data.get("추천 대상", ""))
        if target and target != "기타":
            data["properties"][target_prop] = {"select": {"name": target}}
        
        # 태그 (Multi-select)
        tags_prop = property_mapping.get("태그", "Tags")
        tags = notion_data.get("태그", [])
        if tags:
            data["properties"][tags_prop] = {
                "multi_select": [{"name": str(t)[:100]} for t in tags if t and str(t).strip()]
            }
        
        # 출처 (Select)
        source_prop = property_mapping.get("출처", "Source")
        source = truncate_select_value(notion_data.get("출처", "Discord"))
        if source:
            data["properties"][source_prop] = {"select": {"name": source}}
        
        # 추가 참고 링크 (URL)
        additional_link_prop = property_mapping.get("추가 참고 링크", "Additional Links")
        additional_url = notion_data.get("추가 참고 링크", "")
        if is_valid_url(additional_url):
            data["properties"][additional_link_prop] = {"url": additional_url}
        
        # 등록일 (Date)
        date_prop = property_mapping.get("등록일", "Date")
        formatted_date = format_date_for_notion(notion_data.get("등록일", ""))
        if formatted_date:
            data["properties"][date_prop] = {"date": {"start": formatted_date}}
        
        # 전송됨 (Checkbox)
        sent_prop = property_mapping.get("전송됨", "Sent")
        data["properties"][sent_prop] = {"checkbox": notion_data.get("전송됨", True)}
        
        print(f"Notion에 전송할 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            print("✅ Notion 저장 성공!")
            return True
        else:
            print(f"❌ Notion 저장 실패!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending to Notion: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

# 기존 함수는 새로운 함수를 호출하도록 수정
def send_to_notion(notion_api_key: str, database_id: str, notion_data: dict) -> bool:
    return send_to_notion_flexible(notion_api_key, database_id, notion_data)

def send_to_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    """텔레그램으로 메시지를 전송합니다."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print("✅ 텔레그램 전송 성공!")
            return True
        else:
            print(f"❌ 텔레그램 전송 실패: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending to Telegram: {str(e)}")
        return False

def send_to_airtable(api_key: str, base_id: str, table_name: str, data: dict, 
                    check_duplicates: bool = True, update_if_duplicate: bool = False) -> Dict:
    """
    Airtable에 데이터를 저장합니다. 중복 확인 기능 포함.
    
    Args:
        api_key: Airtable API 키
        base_id: Airtable Base ID
        table_name: 테이블 이름
        data: 저장할 데이터
        check_duplicates: 중복 확인 여부
        update_if_duplicate: 중복 시 업데이트 여부
    
    Returns:
        dict: {
            "success": bool,
            "is_duplicate": bool,
            "action": str,  # "created", "updated", "skipped", "error"
            "record_id": str or None,
            "message": str
        }
    """
    try:
        print(f"Airtable 전송 시도 (중복확인: {check_duplicates}, 업데이트: {update_if_duplicate})")
        print(f"Base ID: {base_id}")
        print(f"Table Name: {table_name}")
        print(f"전송할 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # 1. 중복 확인 (옵션)
        if check_duplicates and data.get('URL'):
            duplicate_check = check_duplicate_url_airtable(api_key, base_id, table_name, data['URL'])
            
            if duplicate_check.get('error'):
                return {
                    "success": False,
                    "is_duplicate": False,
                    "action": "error",
                    "record_id": None,
                    "message": f"중복 확인 실패: {duplicate_check['error']}"
                }
            
            if duplicate_check['is_duplicate']:
                existing_record_id = duplicate_check['record_id']
                existing_data = duplicate_check['existing_data']
                
                if update_if_duplicate:
                    # 기존 레코드 업데이트
                    print(f"🔄 중복 레코드 업데이트 모드")
                    success = update_airtable_record(api_key, base_id, table_name, existing_record_id, data)
                    
                    if success:
                        return {
                            "success": True,
                            "is_duplicate": True,
                            "action": "updated",
                            "record_id": existing_record_id,
                            "message": f"기존 레코드가 업데이트되었습니다. (레코드 ID: {existing_record_id})"
                        }
                    else:
                        return {
                            "success": False,
                            "is_duplicate": True,
                            "action": "error",
                            "record_id": existing_record_id,
                            "message": "기존 레코드 업데이트에 실패했습니다."
                        }
                else:
                    # 중복으로 스킵
                    existing_site_name = existing_data.get('사이트 이름', 'N/A')
                    existing_date = existing_data.get('등록일', 'N/A')
                    
                    return {
                        "success": True,
                        "is_duplicate": True,
                        "action": "skipped",
                        "record_id": existing_record_id,
                        "message": f"이미 존재하는 URL입니다.\n기존 항목: {existing_site_name} (등록일: {existing_date})"
                    }
        
        # 2. 새 레코드 생성
        url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 데이터 검증 및 정리
        cleaned_data = {}
        for key, value in data.items():
            print(f"필드 '{key}': {value} (타입: {type(value)})")
            
            # 빈 값이나 None 값 처리
            if value is None or value == "":
                print(f"  -> 빈 값이므로 제외")
                continue
                
            # 문자열 길이 제한 (Airtable 제한 고려)
            if isinstance(value, str) and len(value) > 100000:
                value = value[:100000]
                print(f"  -> 문자열 길이 제한으로 자름")
            
            cleaned_data[key] = value
            print(f"  -> 최종값: {value}")
        
        payload = {
            "fields": cleaned_data
        }
        
        print(f"최종 Airtable 페이로드: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"Airtable 응답 상태코드: {response.status_code}")
        print(f"Airtable 응답 내용: {response.text}")
        
        if response.status_code in [200, 201]:
            response_data = response.json()
            new_record_id = response_data.get('id')
            
            print("✅ Airtable 저장 성공!")
            return {
                "success": True,
                "is_duplicate": False,
                "action": "created",
                "record_id": new_record_id,
                "message": "새 레코드가 성공적으로 생성되었습니다."
            }
        else:
            print(f"❌ Airtable 저장 실패!")
            return {
                "success": False,
                "is_duplicate": False,
                "action": "error",
                "record_id": None,
                "message": f"Airtable 저장 실패: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        print(f"❌ Error sending to Airtable: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "success": False,
            "is_duplicate": False,
            "action": "error",
            "record_id": None,
            "message": f"오류 발생: {str(e)}"
        }

# 하위 호환성을 위한 래퍼 함수 (기존 코드가 동작하도록)
def send_to_airtable_legacy(api_key: str, base_id: str, table_name: str, data: dict) -> bool:
    """기존 함수와 호환되는 래퍼 함수"""
    result = send_to_airtable(api_key, base_id, table_name, data, check_duplicates=True, update_if_duplicate=False)
    return result["success"]