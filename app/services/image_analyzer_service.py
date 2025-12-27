"""
Madstamp Automation - 이미지 분석 서비스

고객이 보낸 이미지를 종합적으로 분석하여 도장 제작 가능 여부를 판단합니다.
- OpenRouter Grok 4.1 Fast: 이미지 비전 분석
- OCR.space: 텍스트 추출
- 폰트 매칭: 저작권 무료 폰트 추천
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from app.apis.ocr_space_client import OCRResult, OCRSpaceClient
from app.apis.openrouter_client import (
    ImageAnalysisResult,
    ImageQuality,
    OpenRouterClient,
    ProducibilityStatus,
)

logger = logging.getLogger(__name__)


class AnalysisStage(str, Enum):
    """분석 단계"""
    PENDING = "pending"
    VISION_ANALYSIS = "vision_analysis"
    OCR_EXTRACTION = "ocr_extraction"
    FONT_MATCHING = "font_matching"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FontRecommendation:
    """폰트 추천"""
    name: str
    family: str
    style: str
    license_type: str
    cdn_url: Optional[str] = None
    similarity_score: float = 0.0


@dataclass
class ComprehensiveAnalysisResult:
    """종합 분석 결과"""
    # 기본 정보
    image_path: str
    stage: AnalysisStage
    
    # 제작 가능 여부
    is_producible: bool
    producibility_status: ProducibilityStatus
    producibility_reason: str
    confidence: float
    
    # 이미지 품질
    image_quality: ImageQuality
    
    # 감지된 요소
    detected_elements: list[str] = field(default_factory=list)
    detected_text: Optional[str] = None
    detected_font_style: Optional[str] = None
    
    # 폰트 추천
    recommended_fonts: list[FontRecommendation] = field(default_factory=list)
    
    # Lovart AI 프롬프트
    recommended_prompt: Optional[str] = None
    
    # 개선 제안
    suggestions: list[str] = field(default_factory=list)
    
    # 원본 분석 결과
    vision_result: Optional[ImageAnalysisResult] = None
    ocr_result: Optional[OCRResult] = None
    
    # 오류 정보
    error_message: Optional[str] = None


# 저작권 무료 폰트 데이터베이스 (OFL 라이선스)
FREE_FONTS_DATABASE = [
    FontRecommendation(
        name="Noto Sans Korean",
        family="Noto Sans KR",
        style="sans-serif",
        license_type="OFL",
        cdn_url="https://fonts.googleapis.com/css2?family=Noto+Sans+KR",
    ),
    FontRecommendation(
        name="Noto Serif Korean",
        family="Noto Serif KR",
        style="serif",
        license_type="OFL",
        cdn_url="https://fonts.googleapis.com/css2?family=Noto+Serif+KR",
    ),
    FontRecommendation(
        name="Pretendard",
        family="Pretendard",
        style="sans-serif",
        license_type="OFL",
        cdn_url="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css",
    ),
    FontRecommendation(
        name="나눔고딕",
        family="Nanum Gothic",
        style="sans-serif",
        license_type="OFL",
        cdn_url="https://fonts.googleapis.com/css2?family=Nanum+Gothic",
    ),
    FontRecommendation(
        name="나눔명조",
        family="Nanum Myeongjo",
        style="serif",
        license_type="OFL",
        cdn_url="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo",
    ),
    FontRecommendation(
        name="나눔손글씨 펜",
        family="Nanum Pen Script",
        style="handwriting",
        license_type="OFL",
        cdn_url="https://fonts.googleapis.com/css2?family=Nanum+Pen+Script",
    ),
    FontRecommendation(
        name="마루 부리",
        family="MaruBuri",
        style="serif",
        license_type="OFL",
    ),
    FontRecommendation(
        name="IBM Plex Sans KR",
        family="IBM Plex Sans KR",
        style="sans-serif",
        license_type="OFL",
        cdn_url="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR",
    ),
    FontRecommendation(
        name="Gmarket Sans",
        family="GmarketSans",
        style="sans-serif",
        license_type="Free",
    ),
    FontRecommendation(
        name="배달의민족 주아",
        family="BMJUA",
        style="display",
        license_type="OFL",
    ),
]


class ImageAnalyzerService:
    """
    이미지 분석 서비스
    
    고객 이미지를 종합적으로 분석하여 도장 제작 가능 여부를 판단합니다.
    """

    def __init__(
        self,
        openrouter_api_key: str,
        openrouter_model: str = "x-ai/grok-4.1-fast",
        openrouter_fallback_model: str = "cerebras/llama-3.3-70b",
        ocr_api_key: str = "helloworld",
    ):
        self.openrouter_client = OpenRouterClient(
            api_key=openrouter_api_key,
            model=openrouter_model,
            fallback_model=openrouter_fallback_model,
        )
        self.ocr_client = OCRSpaceClient(api_key=ocr_api_key)

    async def close(self):
        """클라이언트 종료"""
        await self.openrouter_client.close()
        await self.ocr_client.close()

    async def analyze(
        self,
        image_path: str,
        customer_request: Optional[str] = None,
        perform_ocr: bool = True,
    ) -> ComprehensiveAnalysisResult:
        """
        이미지를 종합적으로 분석합니다.
        
        Args:
            image_path: 이미지 파일 경로
            customer_request: 고객 요청 내용
            perform_ocr: OCR 수행 여부
            
        Returns:
            ComprehensiveAnalysisResult: 종합 분석 결과
        """
        # 파일 존재 확인
        if not Path(image_path).exists():
            return ComprehensiveAnalysisResult(
                image_path=image_path,
                stage=AnalysisStage.FAILED,
                is_producible=False,
                producibility_status=ProducibilityStatus.NOT_PRODUCIBLE,
                producibility_reason="이미지 파일을 찾을 수 없습니다.",
                confidence=0.0,
                image_quality=ImageQuality.POOR,
                error_message=f"파일 없음: {image_path}",
            )

        try:
            # 1단계: Vision 분석 (OpenRouter Grok 4.1 Fast)
            logger.info(f"Starting vision analysis for: {image_path}")
            vision_result = await self.openrouter_client.analyze_image(
                image_path=image_path,
                additional_context=customer_request,
            )

            # 2단계: OCR 텍스트 추출 (선택적)
            ocr_result = None
            if perform_ocr:
                logger.info(f"Starting OCR extraction for: {image_path}")
                ocr_result = await self.ocr_client.extract_text_multilang(
                    image_path=image_path,
                    languages=["kor", "eng"],
                )

            # 3단계: 폰트 매칭
            recommended_fonts = self._match_fonts(
                detected_style=vision_result.detected_font_style
            )

            # 4단계: 종합 결과 생성
            return self._build_comprehensive_result(
                image_path=image_path,
                vision_result=vision_result,
                ocr_result=ocr_result,
                recommended_fonts=recommended_fonts,
            )

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return ComprehensiveAnalysisResult(
                image_path=image_path,
                stage=AnalysisStage.FAILED,
                is_producible=False,
                producibility_status=ProducibilityStatus.NEEDS_CLARIFICATION,
                producibility_reason="분석 중 오류가 발생했습니다.",
                confidence=0.0,
                image_quality=ImageQuality.FAIR,
                error_message=str(e),
            )

    def _match_fonts(
        self,
        detected_style: Optional[str],
    ) -> list[FontRecommendation]:
        """
        감지된 폰트 스타일에 맞는 저작권 무료 폰트를 추천합니다.
        """
        if not detected_style:
            # 기본 추천: 범용 폰트
            return [
                f for f in FREE_FONTS_DATABASE
                if f.name in ["Noto Sans Korean", "Pretendard", "나눔고딕"]
            ]

        style_lower = detected_style.lower()
        matched_fonts = []

        # 스타일 매칭
        style_mapping = {
            "serif": ["serif"],
            "sans-serif": ["sans-serif"],
            "sans": ["sans-serif"],
            "gothic": ["sans-serif"],
            "고딕": ["sans-serif"],
            "명조": ["serif"],
            "handwriting": ["handwriting"],
            "손글씨": ["handwriting"],
            "script": ["handwriting"],
            "display": ["display"],
            "decorative": ["display"],
        }

        target_styles = []
        for keyword, styles in style_mapping.items():
            if keyword in style_lower:
                target_styles.extend(styles)

        if not target_styles:
            target_styles = ["sans-serif"]  # 기본값

        # 매칭된 폰트 찾기
        for font in FREE_FONTS_DATABASE:
            if font.style in target_styles:
                font.similarity_score = 0.8 if font.style == target_styles[0] else 0.6
                matched_fonts.append(font)

        # 유사도 순으로 정렬
        matched_fonts.sort(key=lambda f: f.similarity_score, reverse=True)

        return matched_fonts[:5]  # 상위 5개 반환

    def _build_comprehensive_result(
        self,
        image_path: str,
        vision_result: ImageAnalysisResult,
        ocr_result: Optional[OCRResult],
        recommended_fonts: list[FontRecommendation],
    ) -> ComprehensiveAnalysisResult:
        """종합 분석 결과 생성"""
        
        # OCR 결과 병합
        detected_text = vision_result.detected_text
        if ocr_result and ocr_result.success and ocr_result.detected_text:
            # OCR 결과가 더 상세하면 사용
            if not detected_text or len(ocr_result.detected_text) > len(detected_text):
                detected_text = ocr_result.detected_text

        # 제작 가능 여부 결정
        is_producible = vision_result.status == ProducibilityStatus.PRODUCIBLE

        # 프롬프트 생성/개선
        recommended_prompt = vision_result.recommended_prompt
        if recommended_prompt and detected_text:
            # 감지된 텍스트를 프롬프트에 포함
            if detected_text not in recommended_prompt:
                recommended_prompt = f"{recommended_prompt}, 텍스트: '{detected_text}'"

        # 제안 사항 병합
        suggestions = list(vision_result.suggestions)
        if ocr_result and not ocr_result.success:
            suggestions.append("텍스트 인식에 실패했습니다. 더 선명한 이미지를 제공해주세요.")
        
        # 폰트 추천 제안 추가
        if recommended_fonts and detected_text:
            font_names = ", ".join([f.name for f in recommended_fonts[:3]])
            suggestions.append(f"추천 폰트: {font_names}")

        return ComprehensiveAnalysisResult(
            image_path=image_path,
            stage=AnalysisStage.COMPLETED,
            is_producible=is_producible,
            producibility_status=vision_result.status,
            producibility_reason=vision_result.reason,
            confidence=vision_result.confidence,
            image_quality=vision_result.image_quality,
            detected_elements=vision_result.detected_elements,
            detected_text=detected_text,
            detected_font_style=vision_result.detected_font_style,
            recommended_fonts=recommended_fonts,
            recommended_prompt=recommended_prompt,
            suggestions=suggestions,
            vision_result=vision_result,
            ocr_result=ocr_result,
        )


async def analyze_customer_image_comprehensive(
    image_path: str,
    openrouter_api_key: str,
    ocr_api_key: str = "helloworld",
    customer_request: Optional[str] = None,
) -> ComprehensiveAnalysisResult:
    """
    고객 이미지 종합 분석 헬퍼 함수
    
    Args:
        image_path: 이미지 파일 경로
        openrouter_api_key: OpenRouter API 키
        ocr_api_key: OCR.space API 키
        customer_request: 고객 요청 내용
        
    Returns:
        ComprehensiveAnalysisResult: 종합 분석 결과
    """
    service = ImageAnalyzerService(
        openrouter_api_key=openrouter_api_key,
        ocr_api_key=ocr_api_key,
    )
    try:
        return await service.analyze(
            image_path=image_path,
            customer_request=customer_request,
        )
    finally:
        await service.close()
