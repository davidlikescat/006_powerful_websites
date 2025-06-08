# test_duplicate_check.py
# 중복 확인 함수만 따로 테스트하는 스크립트

import os
from dotenv import load_dotenv
from sub2 import check_duplicate_url_airtable

# 환경 변수 로드
load_dotenv()

# Airtable 설정
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')

def test_duplicate_check():
    print("=" * 50)
    print("중복 확인 함수 테스트")
    print("=" * 50)
    
    # 환경변수 확인
    print(f"AIRTABLE_API_KEY: {'설정됨' if AIRTABLE_API_KEY else '❌ 없음'}")
    print(f"AIRTABLE_BASE_ID: {AIRTABLE_BASE_ID}")
    print(f"AIRTABLE_TABLE_NAME: {AIRTABLE_TABLE_NAME}")
    print()
    
    # 중복 확인 테스트
    test_url = "https://glasp.co/"
    print(f"테스트 URL: {test_url}")
    print()
    
    try:
        result = check_duplicate_url_airtable(
            AIRTABLE_API_KEY, 
            AIRTABLE_BASE_ID, 
            AIRTABLE_TABLE_NAME, 
            test_url
        )
        
        print("중복 확인 결과:")
        print(f"  is_duplicate: {result.get('is_duplicate')}")
        print(f"  record_id: {result.get('record_id')}")
        print(f"  error: {result.get('error')}")
        
        if result.get('existing_data'):
            existing = result['existing_data']
            print(f"  기존 데이터:")
            print(f"    사이트 이름: {existing.get('사이트 이름')}")
            print(f"    등록일: {existing.get('등록일')}")
        
        return result
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    test_duplicate_check()