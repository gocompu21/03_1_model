# EC2 서버 업데이트 가이드: 수목생리학 용어집 추가

수목생리학 용어 데이터와 관련 기능이 Git 저장소에 업로드되었습니다.  
EC2 서버에서 다음 단계를 차례대로 실행하여 DB를 업데이트하세요.

## 1. 코드 및 데이터 업데이트
서버의 프로젝트 디렉토리로 이동하여 최신 코드를 받아옵니다.

```bash
cd /path/to/project  # 실제 프로젝트 경로로 이동 (예: /home/ubuntu/Django_BaseCamp/03_1_model)
git pull
```

## 2. 가상환경 활성화 (필요한 경우)
```bash
source venv/bin/activate
```

## 3. 용어 데이터 가져오기 (DB Import)
새로 추가된 엑셀 파일(`data/수목생리학_용어정리.xlsx`) 내용을 DB에 입력합니다.

```bash
python import_physiology_terms.py
```
> **예상 결과**: "Finished. Created: 2103..." 메시지가 출력됩니다.

## 4. 기출문제 연동 (DB Linking)
입력된 용어와 기존 기출문제를 자동으로 연결합니다.

```bash
python link_physiology_terms.py
```
> **예상 결과**: "Linking Completed for 수목생리학... Total links created: 4933" 등

## 5. (선택사항) 서버 재시작
코드 변경사항(HTML/View 등)이 바로 반영되지 않는 경우 서버를 재시작합니다.
```bash
sudo systemctl restart gunicorn
# 또는
sudo systemctl restart nginx
```
