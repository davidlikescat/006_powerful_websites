import discord
import asyncio
import re
from sub1 import extract_text_from_url, gemini_extract_notion_fields, flatten_fields_for_airtable
from sub2 import send_to_airtable, send_to_telegram, check_duplicate_url_airtable
from sub3 import process_script_to_tts_google_drive  # Google Drive TTS 사용
import os
from dotenv import load_dotenv
import json
import requests

# 환경 변수 로드
load_dotenv()

def simple_duplicate_check(api_key: str, base_id: str, table_name: str, url: str) -> bool:
    """간단한 중복 확인 - True면 중복 있음, False면 중복 없음"""
    try:
        print(f"🔍 간단 중복 확인: {url}")
        
        clean_url = url.strip().lower()
        if clean_url.startswith('http://'):
            clean_url = clean_url.replace('http://', 'https://', 1)
        
        headers = {"Authorization": f"Bearer {api_key}"}
        request_url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        response = requests.get(request_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Airtable 조회 실패")
            return False
        
        records = response.json().get('records', [])
        print(f"총 {len(records)}개 레코드 검사 중...")
        
        for record in records:
            existing_url = record.get('fields', {}).get('URL', '').strip().lower()
            if existing_url.startswith('http://'):
                existing_url = existing_url.replace('http://', 'https://', 1)
            
            if clean_url == existing_url:
                site_name = record.get('fields', {}).get('사이트 이름', 'N/A')
                print(f"⚠️ 중복 발견! 기존: {site_name}")
                return True
        
        print(f"✅ 중복 없음")
        return False
        
    except Exception as e:
        print(f"❌ 중복 확인 오류: {str(e)}")
        return False

# Discord 설정
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# API 키 설정
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Airtable 설정
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')

# 중복 처리 설정 (환경변수로 제어 가능)
CHECK_DUPLICATES = os.getenv('CHECK_DUPLICATES', 'true').lower() == 'true'
UPDATE_IF_DUPLICATE = os.getenv('UPDATE_IF_DUPLICATE', 'false').lower() == 'true'

# Discord 클라이언트 설정
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

async def handle_duplicate_url(message, url: str, duplicate_info: dict) -> bool:
    """
    중복 URL 발견 시 처리
    
    Returns:
        bool: 계속 진행할지 여부
    """
    existing_data = duplicate_info.get('existing_data', {})
    existing_site_name = existing_data.get('사이트 이름', 'N/A')
    existing_date = existing_data.get('등록일', 'N/A')
    existing_category = existing_data.get('카테고리', 'N/A')
    
    # 중복 알림 Embed 생성
    embed = discord.Embed(
        title="⚠️ 중복 URL 발견",
        description=f"이 URL은 이미 데이터베이스에 존재합니다.",
        color=0xffa500  # 주황색
    )
    embed.add_field(name="URL", value=url, inline=False)
    embed.add_field(name="기존 사이트 이름", value=existing_site_name, inline=True)
    embed.add_field(name="기존 등록일", value=existing_date, inline=True)
    embed.add_field(name="기존 카테고리", value=existing_category, inline=True)
    embed.add_field(
        name="처리 방법", 
        value="이 메시지에 🔄 (업데이트) 또는 ❌ (건너뛰기) 이모지로 반응해주세요.\n30초 내에 반응이 없으면 자동으로 건너뜁니다.", 
        inline=False
    )
    embed.set_footer(text="중복 처리 대기 중...")
    
    duplicate_msg = await message.channel.send(embed=embed)
    
    # 이모지 반응 추가
    await duplicate_msg.add_reaction('🔄')  # 업데이트
    await duplicate_msg.add_reaction('❌')  # 건너뛰기
    
    def check_reaction(reaction, user):
        return (user == message.author and 
                str(reaction.emoji) in ['🔄', '❌'] and 
                reaction.message.id == duplicate_msg.id)
    
    try:
        # 30초 대기
        reaction, user = await client.wait_for('reaction_add', timeout=30.0, check=check_reaction)
        
        if str(reaction.emoji) == '🔄':
            # 업데이트 선택
            embed.color = 0x00ff00  # 녹색
            embed.set_footer(text="업데이트 진행 중...")
            await duplicate_msg.edit(embed=embed)
            return True
        else:
            # 건너뛰기 선택
            embed.color = 0xff0000  # 빨간색
            embed.set_footer(text="건너뛰기 완료")
            await duplicate_msg.edit(embed=embed)
            return False
            
    except asyncio.TimeoutError:
        # 시간 초과 - 자동으로 건너뛰기
        embed.color = 0x808080  # 회색
        embed.set_footer(text="시간 초과 - 자동으로 건너뛰기됨")
        await duplicate_msg.edit(embed=embed)
        return False

async def process_url(url):
    try:
        print("=" * 50)
        print(f"URL 처리 시작: {url}")
        
        # 1. 중복 확인 (선택사항)
        if CHECK_DUPLICATES:
            print("1. 중복 URL 확인 중...")
            duplicate_check = check_duplicate_url_airtable(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, url)
            
            if duplicate_check.get('is_duplicate'):
                print(f"⚠️ 중복 URL 발견: {url}")
                if not UPDATE_IF_DUPLICATE:
                    print("중복 처리 설정: 건너뛰기")
                    return {"success": False, "message": "중복 URL - 건너뛰기"}
                else:
                    print("중복 처리 설정: 업데이트")
        
        # 2. 텍스트 추출
        print("2. 텍스트 추출 중...")
        text = extract_text_from_url(url)
        print(f"추출된 텍스트 길이: {len(text)}")
        
        # 3. Gemini 분석
        print("3. Gemini 분석 중...")
        notion_data = gemini_extract_notion_fields(text, url, GEMINI_API_KEY)
        print(f"Gemini 결과: {json.dumps(notion_data, ensure_ascii=False, indent=2)}")
        
        # 4. Airtable용 변환
        print("4. Airtable용 데이터 변환 중...")
        filtered_data = flatten_fields_for_airtable(notion_data)
        print(f"변환 후 카테고리: '{filtered_data.get('카테고리')}' (타입: {type(filtered_data.get('카테고리'))})")
        print(f"최종 전송 데이터: {json.dumps(filtered_data, ensure_ascii=False, indent=2)}")
        
        # 5. TTS 처리
        print("5. 영어 스크립트 TTS 변환 중...")
        english_script = filtered_data.get('Script', '')
        
        if english_script and english_script.strip():
            tts_result = process_script_to_tts_google_drive(
                english_script, 
                voice_name="en-US-Journey-F"  # 여성, 따뜻하고 자연스러운
            )
            
            if tts_result["success"]:
                print(f"✅ TTS 변환 성공: {tts_result['audio_url']}")
                # TTS URL을 데이터에 추가
                filtered_data["TTS_URL"] = tts_result["audio_url"]
                filtered_data["TTS_파일명"] = tts_result["filename"]
                filtered_data["Drive_파일ID"] = tts_result.get("file_id", "")
            else:
                print("❌ TTS 변환 실패")
                filtered_data["TTS_URL"] = "TTS 생성 실패"
                filtered_data["TTS_파일명"] = ""
                filtered_data["Drive_파일ID"] = ""
        else:
            print("⚠️ 영어 스크립트가 없어서 TTS 건너뜀")
            filtered_data["TTS_URL"] = "스크립트 없음"
            filtered_data["TTS_파일명"] = ""
            filtered_data["Drive_파일ID"] = ""
        
        # 6. Airtable 전송 (중복 확인 포함)
        print("6. Airtable 전송 중...")
        airtable_result = send_to_airtable(
            AIRTABLE_API_KEY, 
            AIRTABLE_BASE_ID, 
            AIRTABLE_TABLE_NAME, 
            filtered_data,
            check_duplicates=CHECK_DUPLICATES,
            update_if_duplicate=UPDATE_IF_DUPLICATE
        )
        
        # 7. 텔레그램 전송
        if airtable_result["success"]:
            print("7. 텔레그램 전송 중...")
            action_text = {
                "created": "새로 추가",
                "updated": "업데이트",
                "skipped": "중복으로 건너뜀"
            }.get(airtable_result["action"], "처리됨")
            
            telegram_msg = f"📝 웹사이트 정보 ({action_text})\n\n{filtered_data.get('요약 설명', '')}\n\n{filtered_data.get('URL', url)}"
            
            # TTS URL이 있으면 텔레그램 메시지에 추가
            if filtered_data.get("TTS_URL") and "http" in filtered_data.get("TTS_URL", ""):
                telegram_msg += f"\n\n🎙️ 영어 음성: {filtered_data['TTS_URL']}"
            
            telegram_success = send_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, telegram_msg)
            
            return {
                "success": True, 
                "airtable_result": airtable_result,
                "telegram_success": telegram_success,
                "data": filtered_data
            }
        else:
            print("❌ Airtable 저장 실패로 텔레그램 전송 건너뜀")
            return {
                "success": False, 
                "airtable_result": airtable_result,
                "telegram_success": False,
                "data": filtered_data
            }
            
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"success": False, "message": str(e)}

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    print(f'중복 확인 모드: {CHECK_DUPLICATES}')
    print(f'중복 시 업데이트: {UPDATE_IF_DUPLICATE}')
    print(f'환경변수 CHECK_DUPLICATES 값: {os.getenv("CHECK_DUPLICATES", "설정되지 않음")}')
    print(f'환경변수 UPDATE_IF_DUPLICATE 값: {os.getenv("UPDATE_IF_DUPLICATE", "설정되지 않음")}')

@client.event
async def on_message(message):
    print("on_message 이벤트 감지됨")
    if message.channel.id == CHANNEL_ID and message.author != client.user:
        print(f"메시지 감지: {message.content}")
        urls = re.findall(r'(https?://[^\s]+)', message.content)
        for url in urls:
            print(f"URL 감지: {url}")
            status_msg = await message.channel.send(f'🔄 **웹사이트 요약을 시작합니다!**\nURL: {url}')
            
            try:
                print("=" * 50)
                print(f"URL 처리 시작: {url}")
                
                # 1. 간단한 중복 확인
                print("1. 간단 중복 확인 시작")
                if simple_duplicate_check(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, url):
                    embed = discord.Embed(
                        title="⚠️ 중복 URL 발견",
                        description=f"이 URL은 이미 데이터베이스에 존재합니다.\n{url}",
                        color=0xffa500
                    )
                    embed.set_footer(text="중복으로 인해 처리를 건너뛰었습니다.")
                    await status_msg.edit(content=None, embed=embed)
                    continue
                
                # 2. 텍스트 추출
                print("2. 본문 크롤링 시작")
                await status_msg.edit(content=f'📄 **웹사이트 내용 추출 중...**\nURL: {url}')
                text = extract_text_from_url(url)
                print(f"추출된 텍스트 길이: {len(text)}")
                
                # 3. Gemini 분석
                print("3. Gemini 요약 시작")
                await status_msg.edit(content=f'🤖 **AI 분석 중...**\nURL: {url}')
                notion_data = gemini_extract_notion_fields(text, url, GEMINI_API_KEY)
                print(f"Gemini 원본 결과: {json.dumps(notion_data, ensure_ascii=False, indent=2)}")
                
                # 4. Airtable용 변환
                print("4. Airtable용 데이터 변환")
                filtered_data = flatten_fields_for_airtable(notion_data)
                print("=" * 30)
                print(f"최종 Airtable 전송 데이터:")
                print(f"카테고리: '{filtered_data.get('카테고리')}' (타입: {type(filtered_data.get('카테고리'))})")
                print(f"전체 데이터: {json.dumps(filtered_data, ensure_ascii=False, indent=2)}")
                print("=" * 30)
                
                # 5. TTS 처리
                print("5. 영어 스크립트 TTS 변환 중...")
                english_script = filtered_data.get('Script', '')
                
                if english_script and english_script.strip():
                    await status_msg.edit(content=f'🎙️ **TTS 음성 생성 중...**\nURL: {url}')
                    
                    tts_result = process_script_to_tts_google_drive(
                        english_script, 
                        voice_name="en-US-Journey-F"  # 여성, 따뜻하고 자연스러운
                    )
                    
                    if tts_result["success"]:
                        print(f"✅ TTS 변환 성공: {tts_result['audio_url']}")
                        # TTS URL을 데이터에 추가
                        filtered_data["TTS_URL"] = tts_result["audio_url"]
                        filtered_data["TTS_파일명"] = tts_result["filename"]
                        filtered_data["Drive_파일ID"] = tts_result.get("file_id", "")
                    else:
                        print("❌ TTS 변환 실패")
                        filtered_data["TTS_URL"] = "TTS 생성 실패"
                        filtered_data["TTS_파일명"] = ""
                        filtered_data["Drive_파일ID"] = ""
                else:
                    print("⚠️ 영어 스크립트가 없어서 TTS 건너뜀")
                    filtered_data["TTS_URL"] = "스크립트 없음"
                    filtered_data["TTS_파일명"] = ""
                    filtered_data["Drive_파일ID"] = ""
                
                # 6. Airtable 전송
                print("6. Airtable 전송 시도")
                await status_msg.edit(content=f'💾 **데이터 저장 중...**\nURL: {url}')
                
                airtable_result = send_to_airtable(
                    AIRTABLE_API_KEY, 
                    AIRTABLE_BASE_ID, 
                    AIRTABLE_TABLE_NAME, 
                    filtered_data,
                    check_duplicates=False,  # 이미 위에서 확인했으므로 false
                    update_if_duplicate=False
                )
                
                if not airtable_result["success"]:
                    print("❌ Airtable 저장 실패!")
                    await status_msg.edit(content=f"❌ 데이터 저장에 실패했습니다.\n{airtable_result.get('message', '알 수 없는 오류')}")
                    continue
                
                print("✅ Airtable 저장 성공!")
                
                # 7. 텔레그램 전송
                print("7. 텔레그램 전송 시도")
                action_text = {
                    "created": "새로 추가",
                    "updated": "업데이트됨",
                    "skipped": "중복으로 건너뜀"
                }.get(airtable_result["action"], "처리됨")
                
                telegram_msg = f"📝 웹사이트 정보 ({action_text})\n\n{filtered_data.get('요약 설명', '')}\n\n{filtered_data.get('URL', url)}"
                
                # TTS URL이 있으면 텔레그램 메시지에 추가
                if filtered_data.get("TTS_URL") and "http" in filtered_data.get("TTS_URL", ""):
                    telegram_msg += f"\n\n🎙️ 영어 음성: {filtered_data['TTS_URL']}"
                
                telegram_success = send_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, telegram_msg)
                
                print("8. 모든 작업 완료")
                
                # 8. 성공 메시지(Embed) - 중복 처리 정보 포함
                action_color = {
                    "created": 0x2ecc71,   # 녹색 - 새 생성
                    "updated": 0x3498db,   # 파란색 - 업데이트
                    "skipped": 0x95a5a6    # 회색 - 건너뛰기
                }.get(airtable_result["action"], 0x2ecc71)
                
                action_emoji = {
                    "created": "✅",
                    "updated": "🔄", 
                    "skipped": "⏭️"
                }.get(airtable_result["action"], "✅")
                
                embed = discord.Embed(
                    title=f"{action_emoji} 웹사이트 처리 완료! ({action_text})",
                    description=f"**{filtered_data.get('사이트 이름', '')}**\n{filtered_data.get('요약 설명', '')}",
                    color=action_color
                )
                embed.add_field(name="카테고리", value=filtered_data.get('카테고리', '-') or "-", inline=True)
                embed.add_field(name="평가/효용성", value=filtered_data.get('평가/효용성', '-') or "-", inline=True)
                embed.add_field(name="활용 사례", value=filtered_data.get('활용 사례', '-') or "-", inline=True)
                embed.add_field(name="한국어 스크립트", value="✅ 완료", inline=True)
                embed.add_field(name="영어 스크립트", value="✅ 완료", inline=True)
                
                # TTS 결과 표시
                tts_status = "✅ 완료" if filtered_data.get("TTS_URL") and "http" in filtered_data.get("TTS_URL", "") else "❌ 실패"
                embed.add_field(name="영어 TTS 음성", value=tts_status, inline=True)
                
                embed.add_field(name="데이터 저장", value=f"✅ {action_text}", inline=False)
                embed.add_field(name="텔레그램 전송", value="✅ 성공" if telegram_success else "❌ 실패", inline=False)
                
                # TTS URL이 있으면 임베드에 추가
                if filtered_data.get("TTS_URL") and "http" in filtered_data.get("TTS_URL", ""):
                    embed.add_field(name="🎙️ 영어 음성 파일", value=f"[재생하기]({filtered_data['TTS_URL']})", inline=False)
                
                # 중복 처리 정보 추가
                if airtable_result.get("is_duplicate"):
                    embed.add_field(name="ℹ️ 처리 정보", value=airtable_result.get("message", ""), inline=False)
                
                embed.set_footer(text=f"URL: {filtered_data.get('URL', url)}")
                await status_msg.edit(content=None, embed=embed)
                
            except Exception as e:
                print(f"❌ 에러 발생: {str(e)}")
                import traceback
                print(traceback.format_exc())
                await status_msg.edit(content=f"❌ 처리 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    client.run(TOKEN)