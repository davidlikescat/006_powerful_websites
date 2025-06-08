# URL 자동 요약 및 전송 시스템

디스코드 채널에 올라오는 URL을 자동으로 감지하여 내용을 요약하고, Notion과 텔레그램으로 전송하는 시스템입니다.

## 기능

1. 디스코드 특정 채널의 URL 자동 감지
2. URL 본문 크롤링
3. Google Gemini API를 사용한 요약
4. Notion 데이터베이스에 저장
5. 텔레그램으로 전송

## 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정:
`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```
# Discord 설정
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# Gemini API 설정
GEMINI_API_KEY=your_gemini_api_key

# Notion 설정
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Telegram 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 실행 방법

```bash
python main.py
```

## 파일 구조

- `main.py`: 메인 실행 파일 (디스코드 봇 설정 및 URL 처리)
- `sub1.py`: 웹 크롤링 및 Gemini API 관련 함수
- `sub2.py`: Notion 및 Telegram API 관련 함수

## 주의사항

1. 각 API의 토큰과 키는 안전하게 보관하세요.
2. Gemini API는 유료일 수 있으니 사용량을 확인하세요.
3. 크롤링 대상 사이트에 따라 본문 추출 로직을 수정해야 할 수 있습니다. 