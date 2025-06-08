# migration_test.py - 5개 제한 테스트용 마이그레이션 스크립트

import gspread
from google.oauth2.service_account import Credentials
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
import os
import json
from urllib.parse import urlparse
from sub1 import extract_text_from_url, gemini_extract_notion_fields, flatten_fields_for_airtable
from sub2 import send_to_airtable
from sub3 import process_script_to_tts_google_drive
import sys

# 환경 변수 로드
load_dotenv()

# 설정값
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
GOOGLE_SHEET_ID = os.getenv('MIGRATION_SHEET_ID')
GOOGLE_SHEET_NAME = os.getenv('MIGRATION_SHEET_NAME', 'migration_tooly')  # 시트 이름 수정

# Gemini 및 Airtable 설정
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')

# 처리 간격 (초) - 테스트용으로 짧게
PROCESS_DELAY = 10  # 10초 간격

class TestMigrationProcessor:
    def __init__(self):
        self.sheet = None
        self.processed_urls = set()
        self.success_count = 0
        self.error_count = 0
        self.duplicate_count = 0
        self.setup_google_sheets()
        self.load_existing_urls()
        
    def setup_google_sheets(self):
        """구글 시트 연결"""
        try:
            print(f"🔍 디버깅 정보:")
            print(f"   SHEET_ID: {GOOGLE_SHEET_ID}")
            print(f"   SHEET_NAME: {GOOGLE_SHEET_NAME}")
            print(f"   CREDENTIALS: {GOOGLE_CREDENTIALS_FILE}")
            
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
            self.sheet = spreadsheet.worksheet(GOOGLE_SHEET_NAME)
            print("✅ 구글 시트 연결 성공!")
        except Exception as e:
            print(f"❌ 구글 시트 연결 실패: {str(e)}")
            import traceback
            print("상세 오류:")
            print(traceback.format_exc())
            sys.exit(1)
    
    def load_existing_urls(self):
        """Airtable에서 기존 URL들을 불러와서 중복 체크용으로 저장"""
        try:
            print("🔍 Airtable에서 기존 URL 목록 확인 중...")
            
            url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
            headers = {
                "Authorization": f"Bearer {AIRTABLE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, params={"pageSize": 100})
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                
                for record in records:
                    fields = record.get('fields', {})
                    existing_url = fields.get('URL', '')
                    if existing_url:
                        normalized_url = self.normalize_url(existing_url)
                        self.processed_urls.add(normalized_url)
                
                print(f"📋 기존 URL {len(self.processed_urls)}개 확인 완료")
            else:
                print(f"⚠️ Airtable 조회 실패: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ 기존 URL 확인 중 오류: {str(e)}")
    
    def normalize_url(self, url):
        """URL 정규화 (중복 체크용)"""
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url.lower())
            normalized = f"{parsed.netloc}{parsed.path}".rstrip('/')
            return normalized
        except:
            return url.lower().strip()
    
    def get_urls_from_sheet(self, limit=5):
        """구글 시트에서 제한된 수의 URL 목록 가져오기"""
        try:
            all_values = self.sheet.get_all_values()
            urls_to_process = []
            
            for i, row in enumerate(all_values):
                if i == 0:  # 헤더 건너뛰기
                    continue
                
                row_number = i + 1
                
                if len(row) > 0:
                    url = row[0].strip()  # A열이 URL
                    status = row[1] if len(row) > 1 else ""  # B열이 상태
                    
                    # URL이 있고, 아직 처리되지 않은 경우
                    if url and url.startswith('http') and status.lower() not in ['완료', 'done', 'processed', '중복', '처리중']:
                        # 중복 체크
                        normalized_url = self.normalize_url(url)
                        if normalized_url in self.processed_urls:
                            print(f"⚠️ 중복 URL 발견: {url}")
                            self.mark_status(row_number, "중복")
                            self.duplicate_count += 1
                        else:
                            urls_to_process.append((row_number, url))
                            self.processed_urls.add(normalized_url)
                            
                            # 제한 수에 도달하면 중단
                            if len(urls_to_process) >= limit:
                                break
            
            return urls_to_process
            
        except Exception as e:
            print(f"❌ 시트 데이터 읽기 실패: {str(e)}")
            return []
    
    def mark_status(self, row_number, status):
        """시트에 처리 상태 표시 (B열)"""
        try:
            # 올바른 gspread 문법 사용
            self.sheet.update_cell(row_number, 2, status)  # 2는 B열
            print(f"📝 상태 업데이트: 행 {row_number} → {status}")
        except Exception as e:
            print(f"❌ 상태 업데이트 실패 (행 {row_number}): {str(e)}")
    
    def process_single_url(self, url, row_number, include_tts=True):
        """단일 URL 처리"""
        try:
            print(f"\n{'='*60}")
            print(f"🔄 처리 중: {url}")
            print(f"📍 시트 행: {row_number}")
            
            # 1. 웹사이트 분석
            print("1. 웹사이트 크롤링 중...")
            text = extract_text_from_url(url)
            
            if not text.strip():
                print("⚠️ 텍스트 추출 실패, Gemini로 URL만 분석...")
            
            # 2. Gemini 분석
            print("2. Gemini 분석 중...")
            notion_data = gemini_extract_notion_fields(text, url, GEMINI_API_KEY)
            
            if not notion_data or not notion_data.get('사이트 이름'):
                print("❌ Gemini 분석 실패")
                return False
            
            print(f"✅ 사이트 이름: {notion_data.get('사이트 이름')}")
            print(f"✅ 카테고리: {notion_data.get('카테고리')}")
            
            # 3. 데이터 변환
            filtered_data = flatten_fields_for_airtable(notion_data)
            
            # 4. TTS 처리 (옵션)
            if include_tts:
                print("3. TTS 음성 생성 중...")
                english_script = filtered_data.get('Script', '')
                
                if english_script and english_script.strip():
                    tts_result = process_script_to_tts_google_drive(
                        english_script, 
                        voice_name="en-US-Journey-F"
                    )
                    
                    if tts_result["success"]:
                        filtered_data["TTS_URL"] = tts_result["audio_url"]
                        filtered_data["TTS_파일명"] = tts_result["filename"]
                        filtered_data["Drive_파일ID"] = tts_result.get("file_id", "")
                        print("✅ TTS 생성 성공")
                    else:
                        print("⚠️ TTS 생성 실패")
                        filtered_data["TTS_URL"] = "TTS 생성 실패"
                        filtered_data["TTS_파일명"] = ""
                        filtered_data["Drive_파일ID"] = ""
                else:
                    print("⚠️ 영어 스크립트 없음")
                    filtered_data["TTS_URL"] = "스크립트 없음"
                    filtered_data["TTS_파일명"] = ""
                    filtered_data["Drive_파일ID"] = ""
            
            # 5. Airtable 저장
            print("4. Airtable 저장 중...")
            airtable_result = send_to_airtable(
                AIRTABLE_API_KEY, 
                AIRTABLE_BASE_ID, 
                AIRTABLE_TABLE_NAME, 
                filtered_data,
                check_duplicates=False,
                update_if_duplicate=False
            )
            
            if airtable_result.get("success", False):
                print("✅ 처리 완료!")
                return True
            else:
                print("❌ Airtable 저장 실패")
                return False
                
        except Exception as e:
            print(f"❌ 처리 중 오류: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
    
    def run_test_migration(self, limit=5, include_tts=True):
        """테스트 마이그레이션 실행 (제한된 수량)"""
        print("🧪 테스트 마이그레이션 시작!")
        print(f"처리 제한: {limit}개")
        print(f"TTS 생성: {'포함' if include_tts else '제외'}")
        print(f"처리 간격: {PROCESS_DELAY}초")
        
        # URL 목록 가져오기
        urls_to_process = self.get_urls_from_sheet(limit=limit)
        
        if not urls_to_process:
            print("📭 처리할 URL이 없습니다.")
            return
        
        print(f"\n📋 총 {len(urls_to_process)}개 URL 처리 예정")
        print(f"⏱️ 예상 소요 시간: {(len(urls_to_process) * PROCESS_DELAY) // 60}분")
        
        # 처리할 URL 목록 미리보기
        print(f"\n📋 처리 예정 URL 목록:")
        for i, (row_number, url) in enumerate(urls_to_process):
            print(f"  {i+1}. 행 {row_number}: {url}")
        
        confirm = input(f"\n계속 진행하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("🛑 테스트 마이그레이션 취소")
            return
        
        # URL 순차 처리
        start_time = datetime.now()
        
        for i, (row_number, url) in enumerate(urls_to_process):
            current_progress = f"[{i+1}/{len(urls_to_process)}]"
            print(f"\n{current_progress} 진행률: {((i+1)/len(urls_to_process)*100):.1f}%")
            
            try:
                self.mark_status(row_number, "처리중")
                success = self.process_single_url(url, row_number, include_tts)
                
                if success:
                    self.mark_status(row_number, "완료")
                    self.success_count += 1
                    print(f"✅ {current_progress} 성공: {url}")
                else:
                    self.mark_status(row_number, "실패")
                    self.error_count += 1
                    print(f"❌ {current_progress} 실패: {url}")
                
            except KeyboardInterrupt:
                print("\n⏹️ 사용자가 중단했습니다.")
                self.mark_status(row_number, "중단")
                break
            except Exception as e:
                print(f"❌ {current_progress} 예외 발생: {str(e)}")
                self.mark_status(row_number, "오류")
                self.error_count += 1
            
            # 마지막이 아니면 대기
            if i < len(urls_to_process) - 1:
                print(f"⏳ {PROCESS_DELAY}초 대기 중...")
                time.sleep(PROCESS_DELAY)
        
        # 완료 보고서
        end_time = datetime.now()
        elapsed = end_time - start_time
        
        print(f"\n{'='*60}")
        print("🎉 테스트 마이그레이션 완료!")
        print(f"⏱️ 소요 시간: {elapsed}")
        print(f"✅ 성공: {self.success_count}개")
        print(f"❌ 실패: {self.error_count}개") 
        print(f"🔄 중복: {self.duplicate_count}개")
        print(f"📊 총 처리: {self.success_count + self.error_count}개")

def main():
    """메인 실행 함수"""
    print("🧪 테스트 마이그레이션 도구 (5개 제한)")
    print("=" * 50)
    
    # 환경변수 체크
    required_vars = [
        'MIGRATION_SHEET_ID', 'GEMINI_API_KEY', 
        'AIRTABLE_API_KEY', 'AIRTABLE_BASE_ID', 'AIRTABLE_TABLE_NAME'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ 환경변수 누락: {', '.join(missing_vars)}")
        return
    
    # 처리 개수 선택
    print("\n📋 처리할 개수를 선택해주세요:")
    print("1. 3개 처리")
    print("2. 5개 처리") 
    print("3. 10개 처리")
    print("4. 사용자 지정")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        limit = 3
    elif choice == "2":
        limit = 5
    elif choice == "3":
        limit = 10
    elif choice == "4":
        try:
            limit = int(input("처리할 개수 입력: "))
        except ValueError:
            print("❌ 잘못된 입력입니다.")
            return
    else:
        limit = 3  # 기본값을 3으로 변경
    
    # TTS 옵션
    print(f"\n🎵 TTS 생성 옵션:")
    print("1. TTS 포함 (시간 오래 걸림)")
    print("2. TTS 제외 (빠른 테스트)")
    
    tts_choice = input("\n선택 (1-2): ").strip()
    include_tts = tts_choice != "2"
    
    # 마이그레이션 실행
    processor = TestMigrationProcessor()
    processor.run_test_migration(limit=limit, include_tts=include_tts)

if __name__ == "__main__":
    main()