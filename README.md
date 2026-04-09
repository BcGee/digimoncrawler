# digimoncrawler

디지몬 카드게임 덱 레시피 크롤러. [digimon-cg-guide.com](https://digimon-cg-guide.com)에서 카드 이미지를 가져와 인쇄용 문서를 생성합니다.

## 기능

- 덱 레시피 URL에서 카드 ID/수량 자동 파싱
- 카드 이미지 다운로드 및 63×88mm (300DPI) 리사이즈
- 일러스트 버전(P1, P2...) 자동 감지 및 선택
- CLI: Word 문서(.docx) 생성 (2×4, 3×3 레이아웃)
- 웹앱: 브라우저에서 PDF 다운로드

## 구조

```
digimoncrawler/
├── digimoncrawler.py          # CLI 도구
├── template.yaml              # AWS SAM 인프라 정의
├── deploy.sh                  # 수동 배포 스크립트
├── .github/workflows/
│   └── deploy.yml             # GitHub Actions 자동 배포
├── lambda/
│   ├── app.py                 # Lambda 핸들러 (API)
│   └── requirements.txt
└── frontend/
    └── index.html             # 웹 UI (SPA)
```

## CLI 사용법

### 설치

```bash
pip install requests Pillow python-docx
```

### 실행

```bash
python digimoncrawler.py "https://digimon-cg-guide.com/recipe-creater/?recipe=bt14-0014_bt22-0083&deckname=MyDeck"
```

`--use-cached` 옵션으로 이미 다운로드한 이미지를 재사용할 수 있습니다.

```bash
python digimoncrawler.py --use-cached "https://digimon-cg-guide.com/recipe-creater/?recipe=bt14-0014_bt22-0083&deckname=MyDeck"
```

결과물은 `digimon_cards/<덱이름>/` 디렉토리에 저장됩니다.

## 웹앱 사용법

1. 레시피 URL을 붙여넣고 "불러오기" 클릭
2. 덱 리스트를 직접 수정하거나 수량 조절
3. 일러스트 버전이 있는 카드는 드롭다운에서 선택
4. 2×4 또는 3×3 레이아웃으로 PDF 다운로드

## 배포

### 사전 요구사항

- AWS CLI, SAM CLI
- ACM 인증서 (us-east-1 리전)
- Route53 호스팅 영역

### 수동 배포

```bash
cp samconfig.toml.example samconfig.toml
# samconfig.toml에 실제 값 입력
./deploy.sh
```

### GitHub Actions 자동 배포

`main` 브랜치에 push하면 자동 배포됩니다. 다음 GitHub Secrets 설정이 필요합니다:

| Secret | 설명 |
|--------|------|
| `AWS_ROLE_ARN` | GitHub OIDC용 IAM 역할 ARN |
| `DOMAIN_NAME` | 커스텀 도메인 |
| `HOSTED_ZONE_ID` | Route53 호스팅 영역 ID |
| `CERTIFICATE_ARN` | ACM 인증서 ARN (us-east-1) |
| `CARD_BUCKET_NAME` | 카드 이미지 S3 버킷명 |

## 아키텍처

```
CloudFront ─┬─ /          → S3 (프론트엔드)
             ├─ /api/*     → API Gateway → Lambda (Python 3.12)
             └─ /cards/*   → S3 (카드 이미지 캐시)
```

Lambda가 카드 이미지를 원본 사이트에서 가져와 S3에 캐싱하고, 프론트엔드에서 jsPDF로 PDF를 생성합니다.
