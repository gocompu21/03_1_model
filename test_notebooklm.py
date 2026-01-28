"""
NotebookLM-Py 테스트 스크립트
CLI 인증 완료 후 실행 가능
"""
import asyncio
from notebooklm.auth import AuthTokens
from notebooklm.client import NotebookLMClient, NotebooksAPI, ChatAPI

async def test_notebooklm():
    print("=== NotebookLM-Py 테스트 ===")
    
    # 저장된 인증 정보 로드 (async)
    tokens = await AuthTokens.from_storage()
    if not tokens:
        print("❌ 인증 정보가 없습니다. 먼저 'notebooklm login'을 실행하세요.")
        return
    
    print("✅ 인증 정보 로드됨")
    
    # NotebookLM 클라이언트 초기화
    async with NotebookLMClient(auth=tokens) as nlm:
        print("✅ NotebookLM 클라이언트 연결됨")
        
        # NotebooksAPI로 노트북 목록 조회
        notebooks_api = NotebooksAPI(nlm)
        notebooks = await notebooks_api.list()
        print(f"📚 노트북 목록: {len(notebooks)}개")
        
        for nb in notebooks[:10]:  # 최대 10개만 표시
            print(f"  - {nb.title}")
        
        # 테스트: 수목생리학 노트북이 있는지 확인
        physiology_notebooks = [nb for nb in notebooks if "수목생리학" in nb.title]
        
        if physiology_notebooks:
            nb = physiology_notebooks[0]
            print(f"\n🌳 수목생리학 노트북 발견: {nb.title}")
            
            # ChatAPI로 질문해보기
            chat_api = ChatAPI(nlm, nb.id)
            question = "광합성에 대해 자세히 설명해줘"
            print(f"❓ 질문: {question}")
            
            response = await chat_api.send(question)
            response_text = getattr(response, 'text', str(response))
            print(f"💬 답변:\n{response_text[:500]}...")
            
            if hasattr(response, 'sources') and response.sources:
                print(f"\n📖 출처: {len(response.sources)}개")
                for src in response.sources[:3]:
                    print(f"  - {getattr(src, 'title', str(src))}")
        else:
            print("\n⚠️ '수목생리학' 노트북을 찾을 수 없습니다.")
            print("위 목록에서 사용 가능한 노트북 이름을 확인하세요.")

if __name__ == "__main__":
    asyncio.run(test_notebooklm())
