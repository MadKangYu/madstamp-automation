"""
Madstamp Automation - 핵심 설정 모듈

환경변수 로드 및 애플리케이션 설정 관리
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # ==========================================================================
    # 서버 설정
    # ==========================================================================
    environment: str = Field(default="development", description="실행 환경")
    port: int = Field(default=8000, description="서버 포트")
    log_level: str = Field(default="INFO", description="로그 레벨")

    # ==========================================================================
    # Supabase 설정
    # ==========================================================================
    supabase_url: str = Field(..., description="Supabase 프로젝트 URL")
    supabase_key: str = Field(..., description="Supabase Anon 키")
    supabase_service_key: Optional[str] = Field(
        default=None, description="Supabase Service Role 키"
    )

    # ==========================================================================
    # OpenRouter API 설정 (AI 이미지 분석)
    # ==========================================================================
    openrouter_api_key: str = Field(..., description="OpenRouter API 키")
    openrouter_model: str = Field(
        default="x-ai/grok-4.1-fast",
        description="OpenRouter 기본 모델 (OpenRouter Grok 4.1 Fast)",
    )
    openrouter_fallback_model: str = Field(
        default="cerebras/llama-3.3-70b",
        description="OpenRouter 대체 모델 (Grok-4.1-fast 문제 시)",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API 기본 URL",
    )

    # ==========================================================================
    # OCR.space API 설정
    # ==========================================================================
    ocr_space_api_key: str = Field(
        default="helloworld",  # 무료 테스트 키
        description="OCR.space API 키",
    )
    ocr_space_endpoint: str = Field(
        default="https://api.ocr.space/parse/image",
        description="OCR.space API 엔드포인트",
    )

    # ==========================================================================
    # Gmail 설정
    # ==========================================================================
    target_email: str = Field(
        default="goopick@goopick.net",
        description="모니터링할 이메일 주소",
    )
    admin_email: str = Field(
        default="richardowen7212@gmail.com",
        description="관리자 알림 이메일",
    )

    # ==========================================================================
    # Lovart AI 설정
    # ==========================================================================
    lovart_session_cookie: Optional[str] = Field(
        default=None, description="Lovart AI 세션 쿠키"
    )
    lovart_base_url: str = Field(
        default="https://www.lovart.ai",
        description="Lovart AI 기본 URL",
    )

    # ==========================================================================
    # 이미지 처리 설정
    # ==========================================================================
    default_resolution: str = Field(
        default="4K", description="기본 이미지 해상도"
    )
    max_image_size_mb: int = Field(
        default=10, description="최대 이미지 크기 (MB)"
    )
    supported_image_formats: list[str] = Field(
        default=["png", "jpg", "jpeg", "gif", "webp", "bmp"],
        description="지원 이미지 형식",
    )

    # ==========================================================================
    # 회사 정보
    # ==========================================================================
    company_name: str = Field(default="Madstamp", description="회사명")
    business_number: str = Field(
        default="880-86-02373", description="사업자등록번호"
    )
    company_phone: str = Field(
        default="+82 10 5911 2822", description="회사 연락처"
    )

    # ==========================================================================
    # 시스템 설정
    # ==========================================================================
    max_retries: int = Field(default=3, description="최대 재시도 횟수")
    auto_reply_enabled: bool = Field(
        default=True, description="자동 응답 활성화"
    )
    polling_interval_seconds: int = Field(
        default=60, description="이메일 폴링 간격 (초)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
