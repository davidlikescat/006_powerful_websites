# sub3.py 파일의 수정된 부분

import re
import os
from datetime import datetime
import uuid

def sanitize_filename(text, max_length=50):
    """파일명으로 사용할 수 없는 문자 제거 및 길이 제한"""
    if not text:
        return "unknown"
    
    # 파일명으로 사용할 수 없는 문자 제거
    sanitized = re.sub(r'[<>:"/\\|?*]', '', text)
    # 연속된 공백을 하나로 합치고 앞뒤 공백 제거
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    # 길이 제한
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()
    
    return sanitized if sanitized else "unknown"

def get_next_sequence_number():
    """오늘 날짜 기준으로 시퀀스 번호 생성"""
    # 간단한 구현: 현재 시간의 초와 마이크로초 조합
    now = datetime.now()
    sequence = f"{now.hour:02d}{now.minute:02d}"
    return sequence

def process_script_to_tts_google_drive(english_script, voice_name="en-US-Journey-F", site_name=""):
    """영어 스크립트를 TTS로 변환하고 Google Drive에 저장"""
    
    try:
        from google.cloud import texttospeech
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        from google.oauth2.service_account import Credentials
        import io
        
        print(f"🎵 TTS 변환 시작: {voice_name}")
        print(f"📝 스크립트 길이: {len(english_script)}자")
        print(f"🏢 사이트 이름: {site_name}")
        
        # Google Cloud TTS 클라이언트 생성
        client = texttospeech.TextToSpeechClient()
        
        # TTS 요청 설정
        synthesis_input = texttospeech.SynthesisInput(text=english_script)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # TTS 실행
        print("🔄 Google Cloud TTS 변환 중...")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # 파일명 생성 - 새로운 형식
        today = datetime.now().strftime("%Y-%m-%d")
        sequence = get_next_sequence_number()
        site_title = sanitize_filename(site_name, max_length=30)
        
        filename = f"[{today}] {sequence} {site_title}.mp3"
        
        print(f"✅ Google Cloud TTS 변환 성공")
        print(f"📁 생성된 파일명: {filename}")
        
        # Google Drive에 업로드
        print("☁️ Google Drive 업로드 중...")
        
        # Drive API 클라이언트 생성
        credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_file:
            print("❌ Google 인증 파일이 설정되지 않았습니다")
            return {
                "success": False,
                "error": "Google 인증 파일 없음",
                "filename": filename,
                "audio_url": "",
                "file_id": ""
            }
        
        scope = ['https://www.googleapis.com/auth/drive.file']
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 파일 메타데이터
        file_metadata = {
            'name': filename,
            'parents': [os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'root')]  # 폴더 ID 설정 가능
        }
        
        # 파일 업로드
        media = MediaIoBaseUpload(
            io.BytesIO(response.audio_content),
            mimetype='audio/mpeg',
            resumable=True
        )
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # 공유 링크 생성
        drive_service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        # 다운로드 가능한 URL 생성
        audio_url = f"https://drive.google.com/uc?id={file_id}"
        
        print(f"✅ Google Drive 업로드 성공!")
        print(f"🔗 파일 ID: {file_id}")
        print(f"🔗 다운로드 URL: {audio_url}")
        
        return {
            "success": True,
            "filename": filename,
            "audio_url": audio_url,
            "file_id": file_id,
            "error": ""
        }
        
    except ImportError as e:
        print(f"❌ 필요한 라이브러리가 설치되지 않았습니다: {str(e)}")
        return {
            "success": False,
            "error": f"라이브러리 누락: {str(e)}",
            "filename": "",
            "audio_url": "",
            "file_id": ""
        }
    except Exception as e:
        print(f"❌ TTS 처리 중 오류 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "filename": "",
            "audio_url": "",
            "file_id": ""
        }