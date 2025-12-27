# Madstamp 도장 이미지 자동화 시스템 - POD (Product Outline Document)

**버전**: 2.0  
**작성일**: 2025년 12월 27일  
**사업자등록번호**: 880-86-02373  
**소유**: Madstamp  

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목적

고객이 이메일로 보낸 다양한 형태의 이미지(손그림, 일반 사진, 로고 등)를 자동으로 분석하여 도장 제작 가능 여부를 판단하고, Lovart AI를 통해 4K 고해상도 도장 이미지를 생성한 후 EPS/AI 벡터 형식으로 변환하여 고객에게 전달하는 완전 자동화 시스템을 구축합니다.

### 1.2 핵심 가치

| 항목 | 기존 방식 | 자동화 시스템 |
|------|----------|--------------|
| 이미지 분석 | 수동 확인 (10-30분) | AI 자동 분석 (30초) |
| 제작 가능 여부 판단 | 담당자 경험 의존 | 일관된 AI 기준 적용 |
| 고객 응답 시간 | 1-24시간 | 5분 이내 |
| 폰트 깨짐 문제 | 빈번 발생 | 저작권 무료 폰트 자동 추천 |
| 벡터 파일 변환 | 수동 작업 | 자동 변환 |

### 1.3 대상 사용자

- **1차 사용자**: GOOPICK 내부 운영팀 (goopick@goopick.net)
- **최종 사용자**: 도장 제작을 요청하는 고객

---

## 2. 시스템 아키텍처

### 2.1 전체 워크플로우

```
[고객 이메일] → [Gmail MCP] → [이미지 분석] → [제작 가능 판단]
                                    ↓
                    [Lovart AI 이미지 생성] → [벡터 변환]
                                    ↓
                            [고객 결과 발송]
```

### 2.2 기술 스택

| 계층 | 기술 | 용도 |
|------|------|------|
| **이미지 분석** | OpenRouter Grok 4.1 Fast | 비전 AI 분석, 제작 가능 여부 판단 |
| **OCR** | OCR.space (무료) | 이미지 내 텍스트 추출 |
| **이미지 생성** | Lovart AI (Playwright 자동화) | 4K 도장 이미지 생성 |
| **벡터 변환** | Potrace + Inkscape | PNG → SVG → EPS/AI |
| **이메일** | Gmail MCP | 이메일 모니터링 및 발송 |
| **데이터베이스** | Supabase (PostgreSQL) | 고객 요청 및 처리 이력 저장 |
| **서버** | Railway / Docker | 자동화 파이프라인 호스팅 |

### 2.3 비용 최적화

| 서비스 | 월 비용 | 비고 |
|--------|---------|------|
| OCR.space | $0 | 무료 25,000회/월 |
| OpenRouter Grok 4.1 Fast | ~$5 | 사용량 기반 |
| Supabase | $0 | 무료 500MB |
| Railway | $0-5 | $5 크레딧 제공 |
| Lovart AI 365 Unlimited | ~$30 | 무제한 생성 |
| **총 예상 비용** | **~$35/월** | |

---

## 3. 핵심 기능

### 3.1 이미지 분석 및 제작 가능 여부 판단

**분석 기준:**

| 상태 | 조건 | 자동 응답 |
|------|------|----------|
| **제작 가능** (producible) | 명확한 로고/텍스트/심볼, 벡터화 가능한 디자인 | 제작 진행 안내 |
| **확인 필요** (needs_clarification) | 손그림 의도 불명확, 해상도 낮음, 일부 가려짐 | 추가 정보 요청 |
| **제작 불가** (not_producible) | 일반 사진, 저작권 문제, 너무 복잡함 | 대안 안내 |

**분석 항목:**
- 이미지 품질 (excellent/good/fair/poor)
- 감지된 요소 (로고, 텍스트, 심볼, 손그림 등)
- 감지된 텍스트 (OCR)
- 폰트 스타일 추정
- Lovart AI 추천 프롬프트 생성

### 3.2 폰트 깨짐 방지 시스템

**저작권 무료 폰트 자동 추천 (OFL 라이선스):**

| 폰트 | 스타일 | 용도 |
|------|--------|------|
| Noto Sans Korean | 고딕 | 범용 |
| Noto Serif Korean | 명조 | 전통적 |
| Pretendard | 모던 고딕 | UI/로고 |
| 나눔고딕 | 고딕 | 범용 |
| 나눔명조 | 명조 | 문서 |
| 나눔손글씨 펜 | 손글씨 | 서명/캐주얼 |
| IBM Plex Sans KR | 고딕 | 기업용 |

**폰트 매칭 로직:**
1. 이미지에서 폰트 스타일 감지 (serif, sans-serif, handwriting 등)
2. 감지된 스타일과 유사한 무료 폰트 추천
3. 고객에게 추천 폰트 목록 제공

### 3.3 Lovart AI 자동화

**자동화 워크플로우:**
1. Playwright로 Lovart AI 웹사이트 접속
2. 로그인 상태 확인 (세션 유지)
3. 새 프로젝트 생성
4. 분석 결과 기반 프롬프트 입력
5. 참조 이미지 업로드 (선택)
6. 이미지 생성 대기 (최대 2분)
7. 4K 해상도 이미지 다운로드

**프롬프트 템플릿:**
- `traditional_korean`: 한국 전통 도장 (낙관)
- `modern_logo`: 현대적 로고 스타일
- `handwriting_style`: 손글씨 스타일
- `company_seal`: 회사 직인

### 3.4 벡터 변환

**변환 파이프라인:**
```
PNG → 전처리(이진화) → Potrace(SVG) → Inkscape(EPS/AI)
```

**출력 형식:**
- SVG: 웹용 벡터
- EPS: 인쇄용 벡터
- AI: Adobe Illustrator 호환 (PDF 기반)

---

## 4. 데이터베이스 스키마

### 4.1 주요 테이블

| 테이블 | 용도 |
|--------|------|
| `customers` | 고객 정보 |
| `stamp_requests` | 도장 제작 요청 |
| `image_analyses` | 이미지 분석 결과 |
| `generated_images` | 생성된 이미지 |
| `email_logs` | 이메일 발송 이력 |

### 4.2 ERD 요약

```
customers (1) ──< (N) stamp_requests (1) ──< (N) image_analyses
                           │
                           └──< (N) generated_images
                           │
                           └──< (N) email_logs
```

---

## 5. GitHub 저장소 구조

**저장소**: `MadKangYu/madstamp-automation`

```
madstamp-automation/
├── app/
│   ├── apis/                    # 외부 API 클라이언트
│   │   ├── openrouter_client.py # OpenRouter Grok 4.1 Fast
│   │   └── ocr_space_client.py  # OCR.space
│   ├── core/
│   │   └── config.py            # 환경 설정
│   ├── jobs/                    # 백그라운드 작업
│   │   ├── email_handler.py     # Gmail MCP 연동
│   │   ├── lovart_automator.py  # Lovart AI 자동화
│   │   └── vector_converter.py  # 벡터 변환
│   ├── models/                  # 데이터 모델
│   ├── services/
│   │   └── image_analyzer_service.py  # 이미지 분석 서비스
│   └── main.py                  # 메인 파이프라인
├── db/
│   └── schema.sql               # Supabase 스키마
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md   # 시스템 아키텍처
│   └── POD_FINAL.md             # 이 문서
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## 6. 네이밍 컨벤션

### 6.1 파일/디렉토리

| 유형 | 규칙 | 예시 |
|------|------|------|
| Python 모듈 | snake_case | `image_analyzer_service.py` |
| 클래스 | PascalCase | `ImageAnalyzerService` |
| 함수/변수 | snake_case | `analyze_customer_image` |
| 상수 | UPPER_SNAKE_CASE | `FREE_FONTS_DATABASE` |
| 환경변수 | UPPER_SNAKE_CASE | `OPENROUTER_API_KEY` |

### 6.2 데이터베이스

| 유형 | 규칙 | 예시 |
|------|------|------|
| 테이블 | snake_case (복수형) | `stamp_requests` |
| 컬럼 | snake_case | `created_at` |
| 인덱스 | `idx_{table}_{column}` | `idx_requests_status` |
| 외래키 | `fk_{table}_{ref_table}` | `fk_requests_customer` |

---

## 7. 실행 방법

### 7.1 환경 설정

```bash
# 저장소 클론
git clone https://github.com/MadKangYu/madstamp-automation.git
cd madstamp-automation

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력

# 의존성 설치
pip install -e .

# 벡터 변환 도구 설치
sudo apt-get install potrace inkscape
```

### 7.2 실행

```bash
# 1회 실행
python -m app.main --mode once

# 연속 모니터링 (60초 간격)
python -m app.main --mode continuous --interval 60

# 브라우저 표시 모드 (디버깅용)
python -m app.main --mode once --no-headless
```

---

## 8. 연락처 정보

| 항목 | 정보 |
|------|------|
| **회사명** | Madstamp |
| **사업자등록번호** | 880-86-02373 |
| **업무용 이메일** | goopick@goopick.net |
| **개인 이메일** | richardowen7212@gmail.com |
| **개인 연락처** | +82 10 8878 7212 |
| **회사 연락처** | +82 10 5911 2822 |
| **GitHub** | MadKangYu/madstamp-automation |

---

## 9. 향후 계획

### Phase 1 (현재)
- [x] 시스템 아키텍처 설계
- [x] 핵심 모듈 개발
- [x] GitHub 저장소 구축

### Phase 2 (예정)
- [ ] Supabase 데이터베이스 연동
- [ ] Railway 서버 배포
- [ ] Chrome 확장 프로그램 개발

### Phase 3 (예정)
- [ ] 고객 대시보드 웹 UI
- [ ] 결제 시스템 연동
- [ ] 다국어 지원

---

## 10. 라이선스

이 프로젝트는 Madstamp의 독점 소프트웨어입니다.  
무단 복제 및 배포를 금지합니다.

---

*이 문서는 2025년 12월 27일에 작성되었습니다.*
