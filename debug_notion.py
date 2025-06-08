import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def check_notion_database_properties():
    """Notion 데이터베이스의 실제 프로퍼티 구조를 확인합니다."""
    
    notion_api_key = os.getenv('NOTION_API_KEY')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    headers = {
        "Authorization": f"Bearer {notion_api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    try:
        # 데이터베이스 정보 조회
        response = requests.get(
            f"https://api.notion.com/v1/databases/{database_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            db_data = response.json()
            print("✅ 데이터베이스 조회 성공!")
            print(f"데이터베이스 제목: {db_data.get('title', [{}])[0].get('plain_text', 'N/A')}")
            print("\n📋 사용 가능한 프로퍼티들:")
            print("-" * 50)
            
            properties = db_data.get('properties', {})
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'unknown')
                print(f"프로퍼티명: '{prop_name}' | 타입: {prop_type}")
                
                # Select 타입의 경우 옵션들도 출력
                if prop_type == 'select' and 'select' in prop_info:
                    options = prop_info['select'].get('options', [])
                    if options:
                        option_names = [opt.get('name', '') for opt in options]
                        print(f"  └─ 옵션: {option_names}")
                
                # Multi-select 타입의 경우 옵션들도 출력
                elif prop_type == 'multi_select' and 'multi_select' in prop_info:
                    options = prop_info['multi_select'].get('options', [])
                    if options:
                        option_names = [opt.get('name', '') for opt in options]
                        print(f"  └─ 옵션: {option_names}")
            
            print("\n" + "=" * 50)
            print("위 프로퍼티명들을 코드에서 정확히 사용해야 합니다!")
            
        else:
            print(f"❌ 데이터베이스 조회 실패!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    check_notion_database_properties()