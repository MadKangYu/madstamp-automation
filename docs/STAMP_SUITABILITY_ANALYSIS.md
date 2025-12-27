# 도장 제작 적합성 자동 판단 기능 분석

## 1. 개요

고객이 보내는 다양한 형태의 이미지(손그림, 일반 사진, 스캔 이미지, 로고 파일 등)를 자동으로 분석하여 **도장 제작 가능 여부**를 판단하는 기능을 구현하기 위한 기술 스택과 접근 방식을 분석합니다.

---

## 2. 문제 정의

### 2.1 고객이 보내는 이미지 유형

| 유형 | 특징 | 제작 난이도 |
|------|------|------------|
| **손그림** | 불규칙한 선, 낮은 해상도, 의도 불명확 | 높음 |
| **일반 사진** | 복잡한 배경, 그라데이션, 색상 다양 | 매우 높음 |
| **스캔 이미지** | 노이즈, 기울어짐, 배경 얼룩 | 중간 |
| **디지털 로고** | 명확한 선, 단순한 색상 | 낮음 |
| **텍스트 이미지** | 폰트 식별 필요, 깨짐 가능성 | 중간 |

### 2.2 도장 제작에 적합한 이미지 조건

도장 제작에 적합한 이미지는 다음 조건을 충족해야 합니다:

1. **명확한 윤곽선**: 선이 뚜렷하고 끊김이 없어야 함
2. **단순한 색상**: 흑백 또는 2-3색 이내
3. **충분한 해상도**: 최소 300 DPI 이상 권장
4. **배경 분리 가능**: 주요 요소와 배경이 명확히 구분
5. **적절한 복잡도**: 너무 세밀하지 않은 디자인
6. **벡터화 가능성**: 래스터 → 벡터 변환 시 품질 유지

---

## 3. 기술 스택 및 접근 방식

### 3.1 권장 기술 스택

#### 3.1.1 이미지 분류 및 분석 (AI 기반)

| 기술 | 용도 | 비용 | 권장도 |
|------|------|------|--------|
| **OpenRouter Grok-4.1-fast** | 이미지 종합 분석, 제작 가능성 판단 | ~$0.001/요청 | ⭐⭐⭐⭐⭐ |
| **OpenAI Vision (GPT-4o)** | 이미지 이해, 텍스트 추출 | ~$0.01/요청 | ⭐⭐⭐⭐ |
| **Google Gemini Pro Vision** | 멀티모달 분석 | 무료 티어 있음 | ⭐⭐⭐⭐ |

**권장**: OpenRouter Grok-4.1-fast를 기본으로 사용하고, 복잡한 케이스에 대해 OpenAI Vision으로 2차 검증

#### 3.1.2 이미지 전처리 (Python 기반)

| 라이브러리 | 용도 | 비용 |
|-----------|------|------|
| **OpenCV** | 이미지 전처리, 윤곽선 검출, 노이즈 제거 | 무료 |
| **Pillow (PIL)** | 기본 이미지 처리, 포맷 변환 | 무료 |
| **scikit-image** | 고급 이미지 분석, 특징 추출 | 무료 |
| **rembg** | AI 기반 배경 제거 | 무료 |

#### 3.1.3 OCR 및 텍스트 인식

| 서비스 | 용도 | 비용 | 권장도 |
|--------|------|------|--------|
| **OCR.space** | 한글/영문 텍스트 인식 | 25,000회/월 무료 | ⭐⭐⭐⭐⭐ |
| **Tesseract OCR** | 로컬 OCR 처리 | 무료 | ⭐⭐⭐⭐ |
| **EasyOCR** | 다국어 OCR, 손글씨 인식 | 무료 | ⭐⭐⭐⭐ |

#### 3.1.4 벡터화 품질 예측

| 도구 | 용도 | 비용 |
|------|------|------|
| **Potrace** | 비트맵 → 벡터 변환 | 무료 |
| **Inkscape (CLI)** | 벡터 변환 및 최적화 | 무료 |
| **Vector Magic API** | 고품질 벡터화 (선택적) | 유료 |

---

### 3.2 분석 파이프라인 설계

```
┌─────────────────────────────────────────────────────────────────┐
│                    이미지 입력 (이메일 첨부)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   1단계: 기본 이미지 분석                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 해상도 확인  │  │ 포맷 확인   │  │ 파일 크기   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   2단계: AI 기반 이미지 분류                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ OpenRouter Grok-4.1-fast                                 │   │
│  │ - 이미지 유형 분류 (손그림/사진/로고/텍스트)              │   │
│  │ - 주요 요소 식별                                         │   │
│  │ - 제작 의도 추론                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   3단계: 기술적 분석                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 윤곽선 분석  │  │ 색상 분석   │  │ 복잡도 분석  │             │
│  │ (OpenCV)    │  │ (PIL)       │  │ (scikit)    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   4단계: 텍스트 분석 (해당 시)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ OCR.space / EasyOCR                                      │   │
│  │ - 텍스트 추출                                            │   │
│  │ - 폰트 스타일 추정                                       │   │
│  │ - 깨짐 여부 확인                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   5단계: 벡터화 테스트                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Potrace 시뮬레이션                                       │   │
│  │ - 벡터 변환 품질 예측                                    │   │
│  │ - 예상 노드 수 계산                                      │   │
│  │ - 세부 손실 예측                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   6단계: 종합 판단                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 적합성 점수 계산 (0-100)                                 │   │
│  │ ┌───────────┬───────────┬───────────┐                   │   │
│  │ │ 제작 가능  │ 확인 필요  │ 제작 불가  │                   │   │
│  │ │ (80-100)  │ (50-79)   │ (0-49)    │                   │   │
│  │ └───────────┴───────────┴───────────┘                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.3 적합성 점수 계산 알고리즘

#### 3.3.1 평가 항목 및 가중치

| 평가 항목 | 가중치 | 설명 |
|----------|--------|------|
| **해상도 점수** | 15% | 300 DPI 이상 = 100점, 150 DPI = 50점, 72 DPI 이하 = 0점 |
| **윤곽선 명확도** | 25% | 엣지 검출 결과의 연속성 및 선명도 |
| **색상 단순도** | 20% | 사용된 색상 수 (2색 이하 = 100점, 5색 이상 = 0점) |
| **배경 분리도** | 15% | 주요 요소와 배경의 대비 |
| **복잡도 적정성** | 15% | 노드 수 기준 (적정 범위 내 = 100점) |
| **AI 판단 점수** | 10% | Grok-4.1-fast의 종합 판단 |

#### 3.3.2 점수 계산 공식

```python
def calculate_suitability_score(analysis_result):
    weights = {
        'resolution': 0.15,
        'edge_clarity': 0.25,
        'color_simplicity': 0.20,
        'background_separation': 0.15,
        'complexity': 0.15,
        'ai_judgment': 0.10
    }
    
    total_score = sum(
        analysis_result[key] * weight 
        for key, weight in weights.items()
    )
    
    return round(total_score, 2)
```

---

### 3.4 판단 결과 분류

#### 3.4.1 제작 가능 (80-100점)

**조건:**
- 명확한 윤곽선
- 단순한 색상 구성
- 충분한 해상도
- 배경 분리 용이

**자동 처리:**
- 즉시 Lovart AI로 전달
- 자동 벡터화 진행
- 고객에게 예상 결과물 미리보기 전송

#### 3.4.2 확인 필요 (50-79점)

**조건:**
- 손그림이지만 의도가 명확
- 해상도가 낮지만 보정 가능
- 일부 복잡한 요소 존재

**처리 방식:**
- 고객에게 확인 이메일 발송
- 개선 제안 사항 안내
- 수동 검토 후 진행

**확인 이메일 예시:**
```
안녕하세요, Madstamp입니다.

보내주신 이미지를 분석한 결과, 다음 사항에 대한 확인이 필요합니다:

[분석 결과]
- 이미지 유형: 손그림
- 해상도: 150 DPI (권장: 300 DPI 이상)
- 복잡도: 중간

[개선 제안]
1. 가능하시다면 더 선명한 이미지를 보내주세요
2. 배경이 깨끗한 흰색이면 더 좋습니다
3. 원하시는 텍스트가 있다면 별도로 알려주세요

현재 이미지로도 제작이 가능하지만, 일부 세부 사항이 
손실될 수 있습니다. 진행하시겠습니까?
```

#### 3.4.3 제작 불가 (0-49점)

**조건:**
- 일반 사진 (풍경, 인물 등)
- 저작권 문제 가능성
- 너무 복잡한 이미지
- 해상도가 너무 낮음

**처리 방식:**
- 제작 불가 사유 안내
- 대안 제시 (새 이미지 요청, 텍스트 기반 제작 등)

---

## 4. 구현 코드 예시

### 4.1 이미지 분석 서비스 (확장)

```python
# app/services/stamp_suitability_analyzer.py

import cv2
import numpy as np
from PIL import Image
from collections import Counter
import requests
import base64
from typing import Dict, Tuple, List
from dataclasses import dataclass
from enum import Enum

class SuitabilityLevel(Enum):
    SUITABLE = "suitable"           # 제작 가능 (80-100)
    NEEDS_REVIEW = "needs_review"   # 확인 필요 (50-79)
    NOT_SUITABLE = "not_suitable"   # 제작 불가 (0-49)

@dataclass
class AnalysisResult:
    score: float
    level: SuitabilityLevel
    image_type: str
    details: Dict
    recommendations: List[str]
    can_auto_process: bool

class StampSuitabilityAnalyzer:
    """도장 제작 적합성 분석기"""
    
    def __init__(self, openrouter_api_key: str, ocr_api_key: str):
        self.openrouter_api_key = openrouter_api_key
        self.ocr_api_key = ocr_api_key
        
        # 가중치 설정
        self.weights = {
            'resolution': 0.15,
            'edge_clarity': 0.25,
            'color_simplicity': 0.20,
            'background_separation': 0.15,
            'complexity': 0.15,
            'ai_judgment': 0.10
        }
    
    async def analyze(self, image_path: str) -> AnalysisResult:
        """이미지 종합 분석"""
        
        # 1. 기본 이미지 정보 분석
        basic_info = self._analyze_basic_info(image_path)
        
        # 2. AI 기반 이미지 분류
        ai_analysis = await self._ai_classify_image(image_path)
        
        # 3. 기술적 분석
        technical_analysis = self._technical_analysis(image_path)
        
        # 4. 텍스트 분석 (필요시)
        text_analysis = None
        if ai_analysis.get('has_text', False):
            text_analysis = await self._analyze_text(image_path)
        
        # 5. 벡터화 품질 예측
        vector_quality = self._predict_vector_quality(image_path)
        
        # 6. 종합 점수 계산
        scores = {
            'resolution': basic_info['resolution_score'],
            'edge_clarity': technical_analysis['edge_clarity'],
            'color_simplicity': technical_analysis['color_simplicity'],
            'background_separation': technical_analysis['background_separation'],
            'complexity': vector_quality['complexity_score'],
            'ai_judgment': ai_analysis['suitability_score']
        }
        
        total_score = self._calculate_total_score(scores)
        level = self._determine_level(total_score)
        
        # 7. 권장 사항 생성
        recommendations = self._generate_recommendations(
            scores, ai_analysis, technical_analysis
        )
        
        return AnalysisResult(
            score=total_score,
            level=level,
            image_type=ai_analysis['image_type'],
            details={
                'basic_info': basic_info,
                'ai_analysis': ai_analysis,
                'technical_analysis': technical_analysis,
                'text_analysis': text_analysis,
                'vector_quality': vector_quality,
                'individual_scores': scores
            },
            recommendations=recommendations,
            can_auto_process=(level == SuitabilityLevel.SUITABLE)
        )
    
    def _analyze_basic_info(self, image_path: str) -> Dict:
        """기본 이미지 정보 분석"""
        img = Image.open(image_path)
        
        width, height = img.size
        dpi = img.info.get('dpi', (72, 72))
        avg_dpi = (dpi[0] + dpi[1]) / 2
        
        # 해상도 점수 계산
        if avg_dpi >= 300:
            resolution_score = 100
        elif avg_dpi >= 150:
            resolution_score = 50 + (avg_dpi - 150) / 3
        else:
            resolution_score = max(0, avg_dpi / 1.5)
        
        return {
            'width': width,
            'height': height,
            'dpi': avg_dpi,
            'format': img.format,
            'mode': img.mode,
            'resolution_score': resolution_score
        }
    
    async def _ai_classify_image(self, image_path: str) -> Dict:
        """AI 기반 이미지 분류 (OpenRouter Grok-4.1-fast)"""
        
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = """이 이미지를 도장 제작 관점에서 분석해주세요.

다음 항목을 JSON 형식으로 응답해주세요:
{
    "image_type": "손그림/일반사진/로고/텍스트/스캔이미지/기타",
    "main_elements": ["주요 요소 목록"],
    "has_text": true/false,
    "detected_text": "감지된 텍스트 (있는 경우)",
    "design_intent": "추정되는 디자인 의도",
    "suitability_score": 0-100,
    "suitability_reason": "적합성 판단 이유",
    "concerns": ["우려 사항 목록"],
    "suggestions": ["개선 제안 목록"]
}"""

        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {self.openrouter_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'x-ai/grok-vision-beta',  # Vision 지원 모델
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/png;base64,{image_data}'
                                }
                            }
                        ]
                    }
                ]
            }
        )
        
        result = response.json()
        # JSON 파싱 및 반환
        return self._parse_ai_response(result)
    
    def _technical_analysis(self, image_path: str) -> Dict:
        """기술적 이미지 분석"""
        
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. 윤곽선 명확도 분석
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Hough 변환으로 선 연속성 확인
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, 
                                 minLineLength=30, maxLineGap=10)
        line_continuity = len(lines) if lines is not None else 0
        
        edge_clarity = min(100, edge_density * 500 + line_continuity * 0.5)
        
        # 2. 색상 단순도 분석
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pixels = img_rgb.reshape(-1, 3)
        
        # K-means로 주요 색상 추출
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=min(10, len(pixels)//100), random_state=42)
        kmeans.fit(pixels)
        
        unique_colors = len(set(kmeans.labels_))
        
        if unique_colors <= 2:
            color_simplicity = 100
        elif unique_colors <= 4:
            color_simplicity = 80
        elif unique_colors <= 6:
            color_simplicity = 50
        else:
            color_simplicity = max(0, 100 - unique_colors * 10)
        
        # 3. 배경 분리도 분석
        # Otsu's thresholding으로 배경/전경 분리
        _, binary = cv2.threshold(gray, 0, 255, 
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        foreground_ratio = np.sum(binary == 0) / binary.size
        
        # 이상적인 전경 비율: 10-40%
        if 0.1 <= foreground_ratio <= 0.4:
            background_separation = 100
        elif 0.05 <= foreground_ratio <= 0.5:
            background_separation = 70
        else:
            background_separation = 40
        
        return {
            'edge_clarity': edge_clarity,
            'color_simplicity': color_simplicity,
            'background_separation': background_separation,
            'unique_colors': unique_colors,
            'foreground_ratio': foreground_ratio
        }
    
    def _predict_vector_quality(self, image_path: str) -> Dict:
        """벡터화 품질 예측"""
        
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        
        # 윤곽선 검출
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, 
                                        cv2.CHAIN_APPROX_SIMPLE)
        
        total_points = sum(len(c) for c in contours)
        num_contours = len(contours)
        
        # 복잡도 점수 계산
        # 적정 범위: 100-1000 포인트
        if 100 <= total_points <= 1000:
            complexity_score = 100
        elif 50 <= total_points <= 2000:
            complexity_score = 70
        elif total_points < 50:
            complexity_score = 50  # 너무 단순
        else:
            complexity_score = max(0, 100 - (total_points - 1000) / 50)
        
        return {
            'total_points': total_points,
            'num_contours': num_contours,
            'complexity_score': complexity_score,
            'estimated_nodes': total_points * 0.3  # 벡터 노드 추정
        }
    
    def _calculate_total_score(self, scores: Dict) -> float:
        """종합 점수 계산"""
        total = sum(scores[key] * self.weights[key] 
                   for key in self.weights)
        return round(total, 2)
    
    def _determine_level(self, score: float) -> SuitabilityLevel:
        """적합성 레벨 결정"""
        if score >= 80:
            return SuitabilityLevel.SUITABLE
        elif score >= 50:
            return SuitabilityLevel.NEEDS_REVIEW
        else:
            return SuitabilityLevel.NOT_SUITABLE
    
    def _generate_recommendations(self, scores: Dict, 
                                   ai_analysis: Dict,
                                   technical: Dict) -> List[str]:
        """권장 사항 생성"""
        recommendations = []
        
        if scores['resolution'] < 70:
            recommendations.append(
                "더 높은 해상도(300 DPI 이상)의 이미지를 권장합니다."
            )
        
        if scores['edge_clarity'] < 70:
            recommendations.append(
                "윤곽선이 더 명확한 이미지를 권장합니다. "
                "펜으로 다시 그리거나 디지털 도구로 정리해주세요."
            )
        
        if scores['color_simplicity'] < 70:
            recommendations.append(
                f"현재 {technical['unique_colors']}개의 색상이 감지되었습니다. "
                "도장 제작을 위해 2-3색 이내로 단순화를 권장합니다."
            )
        
        if scores['background_separation'] < 70:
            recommendations.append(
                "배경이 깨끗한 흰색인 이미지를 권장합니다. "
                "배경 제거 후 재전송해주세요."
            )
        
        if ai_analysis.get('image_type') == '일반사진':
            recommendations.append(
                "일반 사진은 도장 제작에 적합하지 않습니다. "
                "로고나 심볼 형태의 이미지를 보내주세요."
            )
        
        return recommendations
```

---

## 5. Chrome 확장 프로그램 통합

### 5.1 Gmail Content Script 확장

```javascript
// gmail-integration.js 확장

class StampSuitabilityChecker {
  constructor() {
    this.apiEndpoint = 'YOUR_BACKEND_API_ENDPOINT';
  }
  
  async checkSuitability(imageUrl) {
    try {
      const response = await fetch(`${this.apiEndpoint}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_url: imageUrl })
      });
      
      return await response.json();
    } catch (error) {
      console.error('적합성 분석 실패:', error);
      return null;
    }
  }
  
  renderSuitabilityBadge(result) {
    const badge = document.createElement('div');
    badge.className = 'madstamp-suitability-badge';
    
    const levelColors = {
      'suitable': '#4CAF50',
      'needs_review': '#FF9800',
      'not_suitable': '#F44336'
    };
    
    const levelTexts = {
      'suitable': '제작 가능',
      'needs_review': '확인 필요',
      'not_suitable': '제작 불가'
    };
    
    badge.style.backgroundColor = levelColors[result.level];
    badge.innerHTML = `
      <span class="score">${result.score}점</span>
      <span class="level">${levelTexts[result.level]}</span>
    `;
    
    return badge;
  }
}
```

---

## 6. 비용 분석

### 6.1 예상 월간 비용 (1,000건 처리 기준)

| 항목 | 단가 | 월간 비용 |
|------|------|----------|
| OpenRouter Grok-4.1-fast | ~$0.001/요청 | ~$1 |
| OCR.space | 무료 (25,000회) | $0 |
| 서버 (Railway) | $5 크레딧 | ~$5 |
| **총계** | - | **~$6/월** |

---

## 7. 결론 및 권장 사항

### 7.1 핵심 권장 사항

1. **OpenRouter Grok-4.1-fast 활용**: 비용 효율적이면서 정확한 이미지 분석 가능
2. **다단계 분석 파이프라인**: AI 분석 + 기술적 분석 조합으로 정확도 향상
3. **자동화와 수동 검토 병행**: 명확한 케이스는 자동 처리, 애매한 케이스는 확인 요청
4. **고객 피드백 루프**: 분석 결과를 고객에게 명확히 전달하여 재전송 유도

### 7.2 구현 우선순위

1. **1단계**: 기본 이미지 분석 + AI 분류 (OpenRouter)
2. **2단계**: 기술적 분석 (OpenCV) 추가
3. **3단계**: 자동 응답 이메일 시스템
4. **4단계**: Chrome 확장 프로그램 통합

---

**문서 작성**: Manus AI  
**최종 수정**: 2024년 12월 27일
