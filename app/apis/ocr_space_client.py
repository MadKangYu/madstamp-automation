"""
Madstamp Automation - OCR.space API 클라이언트

이미지에서 텍스트를 추출하는 OCR 서비스 클라이언트
무료 티어: 월 25,000회 호출 가능
"""

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR 결과"""
    success: bool
    detected_text: str
    confidence: float
    language: str
    lines: list[str]
    words: list[dict]
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class OCRSpaceClient:
    """
    OCR.space API 클라이언트
    
    이미지에서 텍스트를 추출합니다.
    한국어, 영어, 일본어, 중국어 등 다양한 언어를 지원합니다.
    """

    def __init__(
        self,
        api_key: str = "helloworld",  # 무료 테스트 키
        endpoint: str = "https://api.ocr.space/parse/image",
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()

    def _encode_image_to_base64(self, image_path: str) -> str:
        """이미지를 Base64로 인코딩"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_file_type(self, image_path: str) -> str:
        """파일 확장자 반환"""
        suffix = Path(image_path).suffix.lower()
        return suffix.replace(".", "").upper()

    async def extract_text(
        self,
        image_path: str,
        language: str = "kor",  # 한국어 기본
        detect_orientation: bool = True,
        scale: bool = True,
        ocr_engine: int = 2,  # OCR Engine 2: 한국어 지원
    ) -> OCRResult:
        """
        이미지에서 텍스트를 추출합니다.
        
        Args:
            image_path: 이미지 파일 경로
            language: OCR 언어 코드 (kor, eng, jpn, chs 등)
            detect_orientation: 이미지 방향 자동 감지
            scale: 이미지 스케일링 활성화
            ocr_engine: OCR 엔진 (1: 빠름, 2: 정확/한국어지원, 3: 테이블)
            
        Returns:
            OCRResult: OCR 결과
        """
        try:
            # 이미지 인코딩
            image_base64 = self._encode_image_to_base64(image_path)
            file_type = self._get_file_type(image_path)

            # API 요청 데이터
            payload = {
                "apikey": self.api_key,
                "base64Image": f"data:image/{file_type.lower()};base64,{image_base64}",
                "language": language,
                "detectOrientation": str(detect_orientation).lower(),
                "scale": str(scale).lower(),
                "OCREngine": str(ocr_engine),
                "isTable": "false",
            }

            # API 호출
            response = await self.client.post(
                self.endpoint,
                data=payload,
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_response(data, language)

        except httpx.HTTPStatusError as e:
            logger.error(f"OCR API HTTP error: {e}")
            return OCRResult(
                success=False,
                detected_text="",
                confidence=0.0,
                language=language,
                lines=[],
                words=[],
                error_message=f"HTTP 오류: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"OCR API error: {e}")
            return OCRResult(
                success=False,
                detected_text="",
                confidence=0.0,
                language=language,
                lines=[],
                words=[],
                error_message=str(e),
            )

    async def extract_text_multilang(
        self,
        image_path: str,
        languages: list[str] = ["kor", "eng"],
    ) -> OCRResult:
        """
        여러 언어로 OCR을 시도하여 최상의 결과를 반환합니다.
        
        Args:
            image_path: 이미지 파일 경로
            languages: 시도할 언어 목록
            
        Returns:
            OCRResult: 가장 높은 신뢰도의 OCR 결과
        """
        best_result: Optional[OCRResult] = None

        for lang in languages:
            result = await self.extract_text(image_path, language=lang)
            
            if result.success:
                if best_result is None or result.confidence > best_result.confidence:
                    best_result = result

        if best_result is None:
            return OCRResult(
                success=False,
                detected_text="",
                confidence=0.0,
                language="unknown",
                lines=[],
                words=[],
                error_message="모든 언어에서 텍스트를 감지하지 못했습니다.",
            )

        return best_result

    def _parse_response(self, data: dict, language: str) -> OCRResult:
        """API 응답 파싱"""
        # 오류 확인
        if data.get("IsErroredOnProcessing", False):
            error_msg = data.get("ErrorMessage", ["알 수 없는 오류"])
            return OCRResult(
                success=False,
                detected_text="",
                confidence=0.0,
                language=language,
                lines=[],
                words=[],
                error_message=str(error_msg),
                raw_response=data,
            )

        # 결과 파싱
        parsed_results = data.get("ParsedResults", [])
        if not parsed_results:
            return OCRResult(
                success=False,
                detected_text="",
                confidence=0.0,
                language=language,
                lines=[],
                words=[],
                error_message="파싱된 결과가 없습니다.",
                raw_response=data,
            )

        # 첫 번째 결과 사용
        result = parsed_results[0]
        parsed_text = result.get("ParsedText", "").strip()
        
        # 텍스트 오버레이에서 상세 정보 추출
        text_overlay = result.get("TextOverlay", {})
        lines_data = text_overlay.get("Lines", [])
        
        lines = []
        words = []
        total_confidence = 0.0
        word_count = 0

        for line in lines_data:
            line_text = line.get("LineText", "")
            lines.append(line_text)
            
            for word in line.get("Words", []):
                word_text = word.get("WordText", "")
                word_conf = float(word.get("Confidence", 0))
                words.append({
                    "text": word_text,
                    "confidence": word_conf,
                    "left": word.get("Left", 0),
                    "top": word.get("Top", 0),
                    "width": word.get("Width", 0),
                    "height": word.get("Height", 0),
                })
                total_confidence += word_conf
                word_count += 1

        # 평균 신뢰도 계산
        avg_confidence = total_confidence / word_count if word_count > 0 else 0.0

        return OCRResult(
            success=bool(parsed_text),
            detected_text=parsed_text,
            confidence=avg_confidence / 100.0,  # 0-1 범위로 정규화
            language=language,
            lines=lines,
            words=words,
            raw_response=data,
        )


async def extract_text_from_image(
    image_path: str,
    api_key: str = "helloworld",
    language: str = "kor",
) -> OCRResult:
    """
    이미지에서 텍스트 추출 헬퍼 함수
    
    Args:
        image_path: 이미지 파일 경로
        api_key: OCR.space API 키
        language: OCR 언어 코드
        
    Returns:
        OCRResult: OCR 결과
    """
    client = OCRSpaceClient(api_key=api_key)
    try:
        return await client.extract_text(image_path, language=language)
    finally:
        await client.close()
