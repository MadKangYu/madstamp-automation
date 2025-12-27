"""
Madstamp Automation - 이미지 처리 및 흑백 변환 모듈

도장 제작에 최적화된 이미지 처리:
- 컬러 이미지 → 흑백 변환
- 펜툴 선 처리 (도장 적합화)
- 색상 비우기 (채움 제거)
- 선 굵기 최적화
- 노이즈 제거
- 해상도 조정

모든 오류 케이스 처리 및 품질 보증
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageEnhance

logger = logging.getLogger(__name__)


class ImageQuality(str, Enum):
    """이미지 품질 등급"""
    EXCELLENT = "excellent"     # 4K 이상, 선명
    GOOD = "good"               # 1080p 이상
    FAIR = "fair"               # 720p 이상
    POOR = "poor"               # 720p 미만


class ProcessingMode(str, Enum):
    """처리 모드"""
    LOGO = "logo"               # 로고/심볼 (선명한 경계)
    HANDWRITING = "handwriting" # 손글씨 (부드러운 선)
    PHOTO = "photo"             # 사진 (디더링 적용)
    LINE_ART = "line_art"       # 선화 (펜툴 스타일)
    TEXT = "text"               # 텍스트 (OCR 최적화)


@dataclass
class ProcessingSettings:
    """이미지 처리 설정"""
    mode: ProcessingMode = ProcessingMode.LOGO
    target_dpi: int = 300               # 출력 DPI
    target_width_px: int = 1200         # 목표 너비 (픽셀)
    target_height_px: int = 1200        # 목표 높이 (픽셀)
    threshold: int = 128                # 이진화 임계값 (0-255)
    adaptive_threshold: bool = True     # 적응형 임계값 사용
    noise_reduction: bool = True        # 노이즈 제거
    edge_enhancement: bool = True       # 엣지 강화
    line_thickness_adjust: float = 1.0  # 선 굵기 조정 (1.0 = 원본)
    invert_colors: bool = False         # 색상 반전
    remove_background: bool = True      # 배경 제거
    maintain_aspect_ratio: bool = True  # 원본 비율 유지 (필수)


@dataclass
class ProcessingResult:
    """처리 결과"""
    success: bool
    input_path: str
    output_path: Optional[str] = None
    original_size: Tuple[int, int] = None
    processed_size: Tuple[int, int] = None
    quality_score: float = 0.0          # 0-100
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_log: list[str] = field(default_factory=list)


class ImageProcessor:
    """
    도장 제작용 이미지 처리기
    
    컬러 이미지를 흑백으로 변환하고 도장 제작에 적합하게 처리합니다.
    """

    def __init__(
        self,
        output_dir: str = "/home/ubuntu/madstamp_output/processed",
    ):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    async def process(
        self,
        input_path: str,
        settings: ProcessingSettings = None,
        output_filename: str = None,
    ) -> ProcessingResult:
        """
        이미지 처리 메인 함수
        
        Args:
            input_path: 입력 이미지 경로
            settings: 처리 설정
            output_filename: 출력 파일명 (None이면 자동 생성)
            
        Returns:
            ProcessingResult: 처리 결과
        """
        if settings is None:
            settings = ProcessingSettings()
        
        result = ProcessingResult(
            success=False,
            input_path=input_path,
        )
        
        try:
            # 1. 이미지 로드
            result.processing_log.append("이미지 로드 시작")
            img = Image.open(input_path)
            result.original_size = img.size
            result.processing_log.append(f"원본 크기: {img.size}, 모드: {img.mode}")
            
            # 2. 품질 검사
            quality_issues = self._check_quality(img)
            result.issues.extend(quality_issues)
            
            # 3. 전처리 (크기 조정, 비율 유지)
            img = self._preprocess(img, settings)
            result.processing_log.append(f"전처리 완료: {img.size}")
            
            # 4. 모드별 처리
            if settings.mode == ProcessingMode.LOGO:
                img = self._process_logo(img, settings)
            elif settings.mode == ProcessingMode.HANDWRITING:
                img = self._process_handwriting(img, settings)
            elif settings.mode == ProcessingMode.PHOTO:
                img = self._process_photo(img, settings)
            elif settings.mode == ProcessingMode.LINE_ART:
                img = self._process_line_art(img, settings)
            elif settings.mode == ProcessingMode.TEXT:
                img = self._process_text(img, settings)
            
            result.processing_log.append(f"모드별 처리 완료: {settings.mode.value}")
            
            # 5. 흑백 변환
            img = self._convert_to_bw(img, settings)
            result.processing_log.append("흑백 변환 완료")
            
            # 6. 후처리 (노이즈 제거, 엣지 강화)
            img = self._postprocess(img, settings)
            result.processing_log.append("후처리 완료")
            
            # 7. 품질 점수 계산
            result.quality_score = self._calculate_quality_score(img)
            result.processing_log.append(f"품질 점수: {result.quality_score:.1f}")
            
            # 8. 저장
            if output_filename is None:
                base_name = Path(input_path).stem
                output_filename = f"{base_name}_processed.png"
            
            output_path = os.path.join(self.output_dir, output_filename)
            img.save(output_path, "PNG", dpi=(settings.target_dpi, settings.target_dpi))
            
            result.output_path = output_path
            result.processed_size = img.size
            result.success = True
            result.processing_log.append(f"저장 완료: {output_path}")
            
        except Exception as e:
            result.issues.append(f"처리 오류: {str(e)}")
            logger.error(f"Image processing error: {e}")
        
        return result

    def _check_quality(self, img: Image.Image) -> list[str]:
        """이미지 품질 검사"""
        issues = []
        
        width, height = img.size
        
        # 해상도 검사
        if width < 100 or height < 100:
            issues.append("이미지 해상도가 너무 낮습니다 (최소 100x100 권장)")
        elif width < 300 or height < 300:
            issues.append("이미지 해상도가 낮습니다 (300x300 이상 권장)")
        
        # 비율 검사
        aspect_ratio = width / height
        if aspect_ratio > 5 or aspect_ratio < 0.2:
            issues.append("이미지 비율이 극단적입니다 (도장 제작에 부적합할 수 있음)")
        
        # 색상 모드 검사
        if img.mode == "RGBA":
            # 투명도 검사
            alpha = img.split()[-1]
            if alpha.getextrema()[0] < 255:
                issues.append("이미지에 투명 영역이 있습니다 (배경 처리 필요)")
        
        return issues

    def _preprocess(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """전처리: 크기 조정 및 모드 변환"""
        # RGBA → RGB 변환 (투명 배경을 흰색으로)
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # 크기 조정 (비율 유지 필수)
        if settings.maintain_aspect_ratio:
            img.thumbnail(
                (settings.target_width_px, settings.target_height_px),
                Image.Resampling.LANCZOS,
            )
        else:
            # 비율 유지하지 않는 경우 (권장하지 않음)
            img = img.resize(
                (settings.target_width_px, settings.target_height_px),
                Image.Resampling.LANCZOS,
            )
        
        return img

    def _process_logo(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """로고/심볼 처리: 선명한 경계 유지"""
        # 대비 강화
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # 샤프닝
        img = img.filter(ImageFilter.SHARPEN)
        
        return img

    def _process_handwriting(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """손글씨 처리: 부드러운 선 유지"""
        # 약간의 블러로 노이즈 제거
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # 대비 조정
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)
        
        return img

    def _process_photo(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """사진 처리: 디더링 적용"""
        # 그레이스케일 변환
        img = img.convert("L")
        
        # 엣지 검출
        edges = img.filter(ImageFilter.FIND_EDGES)
        
        # 원본과 엣지 합성
        img = Image.blend(img.convert("RGB"), edges.convert("RGB"), 0.3)
        
        return img

    def _process_line_art(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """선화 처리: 펜툴 스타일"""
        # 그레이스케일 변환
        gray = img.convert("L")
        
        # 엣지 검출
        edges = gray.filter(ImageFilter.FIND_EDGES)
        
        # 반전 (흰 배경에 검은 선)
        edges = ImageOps.invert(edges)
        
        # 대비 강화
        enhancer = ImageEnhance.Contrast(edges)
        edges = enhancer.enhance(2.0)
        
        return edges.convert("RGB")

    def _process_text(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """텍스트 처리: OCR 최적화"""
        # 대비 강화
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)
        
        # 샤프닝
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(ImageFilter.SHARPEN)
        
        return img

    def _convert_to_bw(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """흑백 변환 (이진화)"""
        # 그레이스케일 변환
        gray = img.convert("L")
        
        if settings.adaptive_threshold:
            # 적응형 임계값 (로컬 영역 기반)
            img_array = np.array(gray)
            
            # 블록 크기 계산
            block_size = max(img_array.shape) // 10
            if block_size % 2 == 0:
                block_size += 1
            block_size = max(block_size, 11)
            
            # 로컬 평균 계산
            from scipy import ndimage
            local_mean = ndimage.uniform_filter(
                img_array.astype(float),
                size=block_size,
            )
            
            # 적응형 이진화
            threshold_offset = 10
            binary = img_array > (local_mean - threshold_offset)
            
            result = Image.fromarray((binary * 255).astype(np.uint8))
        else:
            # 고정 임계값
            result = gray.point(lambda x: 255 if x > settings.threshold else 0, "1")
            result = result.convert("L")
        
        # 색상 반전 (필요시)
        if settings.invert_colors:
            result = ImageOps.invert(result)
        
        return result.convert("RGB")

    def _postprocess(
        self,
        img: Image.Image,
        settings: ProcessingSettings,
    ) -> Image.Image:
        """후처리: 노이즈 제거, 엣지 강화"""
        # 노이즈 제거
        if settings.noise_reduction:
            # 미디언 필터로 노이즈 제거
            img = img.filter(ImageFilter.MedianFilter(size=3))
        
        # 엣지 강화
        if settings.edge_enhancement:
            img = img.filter(ImageFilter.EDGE_ENHANCE)
        
        # 선 굵기 조정
        if settings.line_thickness_adjust != 1.0:
            if settings.line_thickness_adjust > 1.0:
                # 선 굵게 (팽창)
                img = img.filter(ImageFilter.MaxFilter(size=3))
            else:
                # 선 얇게 (침식)
                img = img.filter(ImageFilter.MinFilter(size=3))
        
        return img

    def _calculate_quality_score(self, img: Image.Image) -> float:
        """품질 점수 계산 (0-100)"""
        score = 100.0
        
        # 해상도 점수
        width, height = img.size
        if width < 300 or height < 300:
            score -= 20
        elif width < 600 or height < 600:
            score -= 10
        
        # 대비 점수
        gray = img.convert("L")
        histogram = gray.histogram()
        
        # 흑백 분포 검사
        black_pixels = sum(histogram[:30])
        white_pixels = sum(histogram[225:])
        total_pixels = sum(histogram)
        
        black_ratio = black_pixels / total_pixels
        white_ratio = white_pixels / total_pixels
        
        # 적절한 흑백 비율 (도장은 보통 20-40% 검정)
        if black_ratio < 0.05 or black_ratio > 0.8:
            score -= 15
        
        # 중간톤이 너무 많으면 감점 (이진화가 잘 안 된 경우)
        mid_pixels = sum(histogram[50:200])
        mid_ratio = mid_pixels / total_pixels
        if mid_ratio > 0.3:
            score -= 10
        
        return max(0, min(100, score))

    async def batch_process(
        self,
        input_paths: list[str],
        settings: ProcessingSettings = None,
    ) -> list[ProcessingResult]:
        """배치 처리"""
        results = []
        for path in input_paths:
            result = await self.process(path, settings)
            results.append(result)
        return results


class StampOptimizer:
    """
    도장 최적화 전문 처리기
    
    도장 제작에 특화된 이미지 처리를 수행합니다.
    """

    def __init__(self, processor: ImageProcessor = None):
        self.processor = processor or ImageProcessor()

    async def optimize_for_stamp(
        self,
        input_path: str,
        stamp_type: str = "general",  # general, name, logo, signature
        output_path: str = None,
    ) -> ProcessingResult:
        """
        도장 제작용 최적화
        
        Args:
            input_path: 입력 이미지
            stamp_type: 도장 유형
            output_path: 출력 경로
        """
        # 도장 유형별 설정
        settings_map = {
            "general": ProcessingSettings(
                mode=ProcessingMode.LOGO,
                threshold=140,
                adaptive_threshold=True,
                edge_enhancement=True,
            ),
            "name": ProcessingSettings(
                mode=ProcessingMode.TEXT,
                threshold=128,
                adaptive_threshold=True,
                edge_enhancement=True,
                line_thickness_adjust=1.1,
            ),
            "logo": ProcessingSettings(
                mode=ProcessingMode.LOGO,
                threshold=130,
                adaptive_threshold=True,
                edge_enhancement=True,
            ),
            "signature": ProcessingSettings(
                mode=ProcessingMode.HANDWRITING,
                threshold=150,
                adaptive_threshold=True,
                noise_reduction=True,
            ),
        }
        
        settings = settings_map.get(stamp_type, settings_map["general"])
        
        if output_path:
            output_filename = os.path.basename(output_path)
        else:
            output_filename = None
        
        return await self.processor.process(
            input_path=input_path,
            settings=settings,
            output_filename=output_filename,
        )

    async def remove_color_fill(
        self,
        input_path: str,
        output_path: str = None,
    ) -> ProcessingResult:
        """
        색상 채움 제거 (윤곽선만 추출)
        
        도장에서 색이 있는 영역을 비우고 윤곽선만 남깁니다.
        """
        result = ProcessingResult(
            success=False,
            input_path=input_path,
        )
        
        try:
            img = Image.open(input_path)
            result.original_size = img.size
            
            # RGB로 변환
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # 그레이스케일 변환
            gray = img.convert("L")
            
            # 엣지 검출 (윤곽선 추출)
            edges = gray.filter(ImageFilter.FIND_EDGES)
            
            # 반전 (흰 배경에 검은 선)
            edges = ImageOps.invert(edges)
            
            # 이진화
            edges = edges.point(lambda x: 255 if x > 200 else 0, "1")
            
            # 저장
            if output_path is None:
                base_name = Path(input_path).stem
                output_path = os.path.join(
                    self.processor.output_dir,
                    f"{base_name}_outline.png"
                )
            
            edges.save(output_path, "PNG")
            
            result.output_path = output_path
            result.processed_size = edges.size
            result.success = True
            
        except Exception as e:
            result.issues.append(f"윤곽선 추출 오류: {str(e)}")
            logger.error(f"Outline extraction error: {e}")
        
        return result

    async def adjust_line_weight(
        self,
        input_path: str,
        weight_factor: float = 1.0,  # 1.0 = 원본, >1 = 굵게, <1 = 얇게
        output_path: str = None,
    ) -> ProcessingResult:
        """
        선 굵기 조정
        
        도장의 선 굵기를 조정합니다.
        """
        result = ProcessingResult(
            success=False,
            input_path=input_path,
        )
        
        try:
            img = Image.open(input_path)
            result.original_size = img.size
            
            # 그레이스케일 변환
            if img.mode != "L":
                img = img.convert("L")
            
            # 선 굵기 조정
            if weight_factor > 1.0:
                # 팽창 (선 굵게)
                iterations = int((weight_factor - 1.0) * 3) + 1
                for _ in range(iterations):
                    img = img.filter(ImageFilter.MaxFilter(size=3))
            elif weight_factor < 1.0:
                # 침식 (선 얇게)
                iterations = int((1.0 - weight_factor) * 3) + 1
                for _ in range(iterations):
                    img = img.filter(ImageFilter.MinFilter(size=3))
            
            # 저장
            if output_path is None:
                base_name = Path(input_path).stem
                output_path = os.path.join(
                    self.processor.output_dir,
                    f"{base_name}_weight_{weight_factor:.1f}.png"
                )
            
            img.save(output_path, "PNG")
            
            result.output_path = output_path
            result.processed_size = img.size
            result.success = True
            
        except Exception as e:
            result.issues.append(f"선 굵기 조정 오류: {str(e)}")
            logger.error(f"Line weight adjustment error: {e}")
        
        return result


# 편의 함수
async def process_for_stamp(
    input_path: str,
    stamp_type: str = "general",
) -> ProcessingResult:
    """도장 제작용 이미지 처리 헬퍼 함수"""
    optimizer = StampOptimizer()
    return await optimizer.optimize_for_stamp(input_path, stamp_type)
