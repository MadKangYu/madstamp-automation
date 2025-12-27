"""
Madstamp Automation - OpenRouter API 클라이언트

OpenRouter Grok 4.1 Fast 모델을 사용한 이미지 분석 및 제작 가능 여부 판단
"""

import base64
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class ImageQuality(str, Enum):
    """이미지 품질 등급"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class ProducibilityStatus(str, Enum):
    """제작 가능 상태"""
    PRODUCIBLE = "producible"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_PRODUCIBLE = "not_producible"


@dataclass
class ImageAnalysisResult:
    """이미지 분석 결과"""
    status: ProducibilityStatus
    confidence: float
    reason: str
    image_quality: ImageQuality
    detected_elements: list[str]
    suggestions: list[str]
    recommended_prompt: Optional[str] = None
    detected_text: Optional[str] = None
    detected_font_style: Optional[str] = None
    raw_response: Optional[dict] = None


class OpenRouterClient:
    """
    OpenRouter API 클라이언트
    
    OpenRouter Grok 4.1 Fast 모델을 사용하여 고객이 보낸 이미지를 분석하고
    도장 제작 가능 여부를 판단합니다.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "x-ai/grok-4.1-fast",
        fallback_model: str = "cerebras/llama-3.3-70b",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()

    def _encode_image_to_base64(self, image_path: str) -> str:
        """이미지를 Base64로 인코딩"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, image_path: str) -> str:
        """이미지 MIME 타입 반환"""
        suffix = Path(image_path).suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mime_types.get(suffix, "image/png")

    async def analyze_image(
        self,
        image_path: str,
        additional_context: Optional[str] = None,
    ) -> ImageAnalysisResult:
        """
        이미지를 분석하여 도장 제작 가능 여부를 판단합니다.
        
        Args:
            image_path: 분석할 이미지 파일 경로
            additional_context: 추가 컨텍스트 (고객 요청 내용 등)
            
        Returns:
            ImageAnalysisResult: 분석 결과
        """
        # 이미지 인코딩
        image_base64 = self._encode_image_to_base64(image_path)
        mime_type = self._get_mime_type(image_path)

        # 분석 프롬프트 구성
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(additional_context)

        # API 요청
        try:
            result = await self._call_api(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                image_base64=image_base64,
                mime_type=mime_type,
            )
        except Exception as e:
            logger.warning(f"Primary model failed: {e}, trying fallback model")
            result = await self._call_api(
                model=self.fallback_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                image_base64=image_base64,
                mime_type=mime_type,
            )

        return self._parse_response(result)

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 구성"""
        return """당신은 도장(스탬프) 제작 전문가입니다. 고객이 보낸 이미지를 분석하여 도장 제작 가능 여부를 판단합니다.

## 분석 기준

### 제작 가능 (producible)
- 명확한 로고, 텍스트, 심볼이 있는 이미지
- 벡터화가 가능한 선명한 디자인
- 도장으로 적합한 단순하고 명확한 형태

### 확인 필요 (needs_clarification)
- 손그림이지만 의도가 명확하지 않은 경우
- 여러 요소가 있어 어떤 것을 도장으로 만들지 불명확한 경우
- 텍스트가 있지만 일부가 가려지거나 불명확한 경우
- 해상도가 낮아 세부 사항 확인이 필요한 경우

### 제작 불가 (not_producible)
- 일반 사진 (풍경, 인물 등)으로 도장 제작 의도가 없는 경우
- 저작권 문제가 있는 유명 브랜드 로고
- 너무 복잡하여 도장으로 제작 불가능한 이미지
- 완전히 흐리거나 인식 불가능한 이미지

## 응답 형식

반드시 다음 JSON 형식으로 응답하세요:

```json
{
    "status": "producible" | "needs_clarification" | "not_producible",
    "confidence": 0.0 ~ 1.0,
    "reason": "판단 이유 설명",
    "image_quality": "excellent" | "good" | "fair" | "poor",
    "detected_elements": ["감지된 요소 목록"],
    "suggestions": ["개선 제안 사항"],
    "recommended_prompt": "Lovart AI에 전달할 추천 프롬프트 (제작 가능한 경우)",
    "detected_text": "감지된 텍스트 (있는 경우)",
    "detected_font_style": "감지된 폰트 스타일 (serif, sans-serif, handwriting 등)"
}
```"""

    def _build_user_prompt(self, additional_context: Optional[str]) -> str:
        """사용자 프롬프트 구성"""
        base_prompt = """이 이미지를 분석하여 도장 제작 가능 여부를 판단해주세요.

다음 사항을 확인해주세요:
1. 이미지에 어떤 요소가 있는지 (로고, 텍스트, 심볼, 손그림 등)
2. 도장으로 제작하기에 적합한지
3. 이미지 품질이 충분한지
4. 텍스트가 있다면 어떤 내용인지
5. 폰트 스타일이 있다면 어떤 종류인지

JSON 형식으로 응답해주세요."""

        if additional_context:
            base_prompt += f"\n\n## 고객 요청 내용\n{additional_context}"

        return base_prompt

    async def _call_api(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        image_base64: str,
        mime_type: str,
    ) -> dict:
        """OpenRouter API 호출"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://madstamp.com",
            "X-Title": "Madstamp Automation",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            },
                        },
                    ],
                },
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _parse_response(self, response: dict) -> ImageAnalysisResult:
        """API 응답 파싱"""
        try:
            content = response["choices"][0]["message"]["content"]
            
            # JSON 블록 추출
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            data = json.loads(json_str)

            return ImageAnalysisResult(
                status=ProducibilityStatus(data.get("status", "needs_clarification")),
                confidence=float(data.get("confidence", 0.5)),
                reason=data.get("reason", "분석 결과를 파싱할 수 없습니다."),
                image_quality=ImageQuality(data.get("image_quality", "fair")),
                detected_elements=data.get("detected_elements", []),
                suggestions=data.get("suggestions", []),
                recommended_prompt=data.get("recommended_prompt"),
                detected_text=data.get("detected_text"),
                detected_font_style=data.get("detected_font_style"),
                raw_response=response,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse response: {e}")
            return ImageAnalysisResult(
                status=ProducibilityStatus.NEEDS_CLARIFICATION,
                confidence=0.0,
                reason=f"응답 파싱 실패: {str(e)}",
                image_quality=ImageQuality.FAIR,
                detected_elements=[],
                suggestions=["이미지를 다시 분석해주세요."],
                raw_response=response,
            )


async def analyze_customer_image(
    image_path: str,
    api_key: str,
    customer_request: Optional[str] = None,
) -> ImageAnalysisResult:
    """
    고객 이미지 분석 헬퍼 함수
    
    Args:
        image_path: 이미지 파일 경로
        api_key: OpenRouter API 키
        customer_request: 고객 요청 내용
        
    Returns:
        ImageAnalysisResult: 분석 결과
    """
    client = OpenRouterClient(api_key=api_key)
    try:
        return await client.analyze_image(
            image_path=image_path,
            additional_context=customer_request,
        )
    finally:
        await client.close()
