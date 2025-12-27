# MadStamp Automation

한글 도장 및 폰트 자동 생성 시스템

---

## 📁 프로젝트 구조

```
madstamp-automation/
├── stamp-generator/          # 도장 생성기
│   ├── circle/              # 원형 도장
│   ├── square/              # 정사각형 도장
│   └── templates/           # 도장 템플릿
│
├── font-generator/           # AI 폰트 생성기
│   ├── colab/               # Google Colab 노트북
│   ├── templates/           # 손글씨 템플릿 (256자)
│   ├── samples/             # 샘플 글자 세트
│   └── docs/                # 문서
│
├── assets/                   # 공통 자산
│   ├── fonts/               # 폰트 파일
│   └── images/              # 이미지 파일
│
├── chrome-extension/         # 크롬 확장 프로그램
│
└── docs/                     # 전체 문서
```

---

## 🔴 도장 생성기 (Stamp Generator)

### 원형 도장
- 5글자 배치 (상단 2 + 하단 3)
- 중심선 기준 좌우 대칭

```bash
cd stamp-generator/circle
python stamp_generator.py
```

### 정사각형 도장
- 6~20글자 지원
- 자동 행/열 배치

```bash
cd stamp-generator/square
python stamp_square.py
```

---

## 🔤 AI 폰트 생성기 (Font Generator)

### 기능
- 43~256자 손글씨 샘플로 11,172자 한글 폰트 생성
- MX-Font (네이버 클로바 AI) 기반
- Google Colab에서 무료 GPU 사용

### 사용 방법

1. **템플릿 다운로드**
   - `font-generator/templates/` 에서 256자 템플릿 PDF 다운로드

2. **손글씨 작성**
   - 템플릿에 맞춰 손글씨 작성
   - 스캔 또는 촬영

3. **Colab 노트북 실행**
   - `font-generator/colab/` 의 노트북 열기
   - 이미지 업로드 → 폰트 생성 → TTF 다운로드

### 샘플 글자 세트

| 세트 | 글자 수 | 용도 |
|------|--------|------|
| 8자 | 8 | 빠른 테스트 |
| 28자 | 28 | 기본 품질 |
| 43자 | 43 | 좋은 품질 |
| 256자 | 256 | 최고 품질 |

---

## 🚀 빠른 시작

### 요구사항
- Python 3.8+
- Pillow
- (폰트 생성) Google Colab 또는 GPU

### 설치

```bash
git clone https://github.com/MadKangYu/madstamp-automation.git
cd madstamp-automation
pip install pillow fonttools
```

---

## 📄 라이선스

MIT License

---

## 🙏 크레딧

- [MX-Font](https://github.com/clovaai/fewshot-font-generation) - 네이버 클로바 AI
- [DM-Font](https://github.com/clovaai/dmfont) - 네이버 클로바 AI
