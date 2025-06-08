# test_sheets.py - 구글 시트 연결 테스트

import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

load_dotenv()

def test_sheets_connection():
    try:
        print("🔍 환경변수 확인:")
        credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        sheet_id = os.getenv('MIGRATION_SHEET_ID')
        sheet_name = os.getenv('MIGRATION_SHEET_NAME', 'Sheet1')
        
        print(f"  인증 파일: {credentials_file}")
        print(f"  시트 ID: {sheet_id}")
        print(f"  시트 이름: {sheet_name}")
        
        # 파일 존재 확인
        if not os.path.exists(credentials_file):
            print(f"❌ 인증 파일이 없습니다: {credentials_file}")
            return False
        
        print("\n🔐 Google Sheets API 인증 중...")
        
        # 인증 설정
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        
        print("✅ 인증 성공!")
        
        # 시트 열기
        print(f"\n📊 시트 연결 중 (ID: {sheet_id})...")
        spreadsheet = client.open_by_key(sheet_id)
        
        print(f"✅ 시트 연결 성공!")
        print(f"  시트 제목: {spreadsheet.title}")
        
        # 워크시트 열기
        worksheet = spreadsheet.worksheet(sheet_name)
        print(f"✅ 워크시트 연결 성공!")
        print(f"  워크시트 이름: {worksheet.title}")
        
        # 데이터 읽기 테스트
        print(f"\n📋 데이터 읽기 테스트...")
        all_values = worksheet.get_all_values()
        
        print(f"  총 행 수: {len(all_values)}")
        if len(all_values) > 0:
            print(f"  첫 번째 행: {all_values[0]}")
        if len(all_values) > 1:
            print(f"  두 번째 행: {all_values[1]}")
            
        # URL 개수 확인
        url_count = 0
        for i, row in enumerate(all_values):
            if i == 0:  # 헤더 건너뛰기
                continue
            if len(row) > 0 and row[0].strip() and row[0].startswith('http'):
                url_count += 1
        
        print(f"  유효한 URL 개수: {url_count}개")
        
        print("\n🎉 모든 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        print("\n상세 오류:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🧪 Google Sheets 연결 테스트")
    print("=" * 40)
    test_sheets_connection()