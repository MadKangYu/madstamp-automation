# 🔤 AI 한글 폰트 생성기

**43~256자 손글씨 샘플로 11,172자 한글 폰트 자동 생성**

네이버 클로바 AI의 MX-Font/DM-Font 기술 기반

---

## 📁 디렉토리 구조

```
font-generator/
├── colab/                    # Google Colab 노트북
│   └── MXFont_Korean_Font_Generator.ipynb
├── templates/                # 손글씨 템플릿
│   ├── template_8chars.pdf
│   ├── template_28chars.pdf
│   ├── template_43chars.pdf
│   ├── template_256chars.pdf
│   └── generate_template.py
├── samples/                  # 샘플 글자 세트
│   └── char_sets.json
└── docs/                     # 문서
    ├── font_sample_characters.md
    └── ai_font_services.md
```

---

## 🚀 빠른 시작

### 1단계: 템플릿 다운로드

`templates/` 폴더에서 원하는 글자 수의 PDF 템플릿을 다운로드합니다.

| 템플릿 | 글자 수 | 예상 품질 | 용도 |
|--------|--------|----------|------|
| template_8chars.pdf | 8자 | ⭐⭐ | 빠른 테스트 |
| template_28chars.pdf | 28자 | ⭐⭐⭐ | 기본 품질 |
| template_43chars.pdf | 43자 | ⭐⭐⭐⭐ | 좋은 품질 |
| template_256chars.pdf | 256자 | ⭐⭐⭐⭐⭐ | 최고 품질 |

### 2단계: 손글씨 작성

1. 템플릿 PDF를 인쇄합니다
2. 각 칸에 해당 글자를 손글씨로 작성합니다
3. 스캔 또는 촬영합니다 (300dpi 이상 권장)

### 3단계: Colab 노트북 실행

1. `colab/MXFont_Korean_Font_Generator.ipynb` 열기
2. Google Colab에서 열기 (Open in Colab)
3. 런타임 > 런타임 유형 변경 > GPU 선택
4. 셀 순서대로 실행
5. 손글씨 이미지 업로드
6. 폰트 생성 및 다운로드

---

## 📊 샘플 글자 세트

### 8자 세트 (빠른 테스트)

```
가 나 다 라 마 바 사 아
```

### 28자 세트 (기본 품질)

```
갈 같 강 개 걔 거 겨 계
고 과 괴 구 궈 귀 그 긔
기 깨 꺼 꼬 꾸 끼 냐 녀
노 뇨 누 뉴
```

### 43자 세트 (좋은 품질)

```
각 간 감 갑 객 건 걸 검
겁 게 격 견 결 경 곡 곤
골 공 관 광 국 군 굴 궁
권 균 극 근 글 금 급 긍
긴 길 김 깊 꽃 꿈 끝 낙
난 날 남
```

### 256자 세트 (최고 품질)

`samples/char_sets.json` 참조

---

## 🔧 기술 스택

| 기술 | 설명 |
|------|------|
| MX-Font | 네이버 클로바 AI 폰트 생성 모델 |
| DM-Font | 한글 조합 구조 활용 모델 |
| PyTorch | 딥러닝 프레임워크 |
| FontForge | 폰트 파일 생성 |
| Google Colab | 무료 GPU 환경 |

---

## ⚠️ 주의사항

1. **GPU 필수**: 폰트 생성에는 GPU가 필요합니다 (Colab 무료 GPU 사용 가능)
2. **학습 데이터**: MX-Font 학습에는 여러 TTF 폰트 파일이 필요합니다
3. **라이선스**: 상업적 사용 시 MX-Font 라이선스(MIT) 확인 필요

---

## 📚 참고 자료

- [MX-Font GitHub](https://github.com/clovaai/fewshot-font-generation)
- [DM-Font 논문](https://arxiv.org/abs/2005.10510)
- [LF-Font 논문](https://arxiv.org/abs/2009.11042)
- [네이버 클로바 나눔손글씨](https://clova.ai/handwriting)

---

## 📄 라이선스

MIT License (MX-Font 원본 라이선스 준수)
