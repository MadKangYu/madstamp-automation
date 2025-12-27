# Madstamp Automation

**도장 이미지 자동 제작 및 고객 전달 시스템**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

## 개요

Madstamp Automation은 고객이 이메일로 보낸 도장 제작 요청을 자동으로 처리하는 시스템입니다. AI 기반 이미지 분석으로 제작 가능 여부를 판단하고, Lovart AI를 통해 고품질 도장 이미지를 생성한 후, 벡터 파일(EPS/AI)로 변환하여 고객에게 전달합니다.

## 주요 기능

- **이메일 자동 모니터링**: Gmail MCP를 통한 실시간 이메일 수신 감지
- **AI 이미지 분석**: OpenRouter Grok-4.1-fast를 활용한 제작 가능 여부 자동 판단
- **OCR 텍스트 추출**: OCR.space API를 통한 이미지 내 텍스트 인식
- **자동 이미지 생성**: Lovart AI 브라우저 자동화 (Playwright)
- **벡터 변환**: PNG → EPS/AI 형식 자동 변환
- **자동 이메일 발송**: 완성된 결과물 고객 전달

## 기술 스택

| 구성요소 | 기술 |
|---------|------|
| 백엔드 | Python 3.11+, FastAPI |
| 데이터베이스 | Supabase (PostgreSQL) |
| 브라우저 자동화 | Playwright |
| AI 분석 | OpenRouter (Grok-4.1-fast) |
| OCR | OCR.space API |
| 이미지 생성 | Lovart AI |
| 벡터 변환 | Potrace, Inkscape |
| 이메일 | Gmail MCP |

## 프로젝트 구조

```
madstamp-automation/
├── app/                    # 핵심 애플리케이션 로직
│   ├── main.py             # FastAPI 진입점
│   ├── core/               # 설정, 로깅
│   ├── services/           # 비즈니스 로직
│   ├── models/             # 데이터 모델
│   ├── apis/               # 외부 API 클라이언트
│   └── jobs/               # 백그라운드 작업
├── db/                     # 데이터베이스 스키마
├── docs/                   # 문서
├── scripts/                # 유틸리티 스크립트
└── tests/                  # 테스트
```

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/MadKangYu/madstamp-automation.git
cd madstamp-automation
```

### 2. 의존성 설치

```bash
pip install poetry
poetry install
```

### 3. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 API 키 등 설정
```

### 4. 데이터베이스 마이그레이션

```bash
# Supabase 대시보드에서 db/schema.sql 실행
```

### 5. 실행

```bash
poetry run python -m app.main
```

## 환경변수

| 변수명 | 설명 |
|--------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase API 키 |
| `OPENROUTER_API_KEY` | OpenRouter API 키 |
| `OCR_SPACE_API_KEY` | OCR.space API 키 |
| `GMAIL_CREDENTIALS` | Gmail 인증 정보 |
| `TARGET_EMAIL` | 모니터링할 이메일 주소 |

## 라이선스

이 프로젝트는 Madstamp의 독점 소프트웨어입니다.

## 연락처

- **회사**: Madstamp
- **사업자등록번호**: 880-86-02373
- **이메일**: goopick@goopick.net
- **연락처**: +82 10 5911 2822
