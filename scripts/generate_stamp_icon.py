#!/usr/bin/env python3
"""
한국 전통 도장 스타일 아이콘 생성기
- 원형 테두리 안에 글자 자동 배치
- 테두리를 넘지 않도록 자동 크기 조절
- 가로/세로 중심축 기준 정렬
"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

class StampIconGenerator:
    def __init__(self, size=1024):
        """
        Args:
            size: 이미지 크기 (정사각형)
        """
        self.size = size
        self.center = size // 2
        
        # 색상 정의 (전통 도장 스타일)
        self.bg_color = (26, 26, 46)  # 다크 배경 #1A1A2E
        self.stamp_color = (196, 30, 58)  # 주홍색 #C41E3A
        self.accent_color = (220, 50, 70)  # 밝은 주홍색
        
        # 테두리 정의 (비율 기반)
        self.outer_border_ratio = 0.90  # 외곽 테두리 (전체의 90%)
        self.inner_border_ratio = 0.82  # 내부 테두리 (전체의 82%)
        self.safe_area_ratio = 0.72     # 안전 영역 (글자 배치 영역)
        
        # 폰트 경로 (시스템 폰트 사용)
        self.font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
        self.serif_font_path = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
        
    def create_base_image(self):
        """기본 이미지 생성 (다크 배경)"""
        img = Image.new('RGBA', (self.size, self.size), self.bg_color + (255,))
        return img
    
    def draw_circuit_pattern(self, draw):
        """디지털/테크 느낌의 회로 패턴 그리기"""
        # 배경에 미세한 회로 패턴 추가
        pattern_color = (35, 35, 60, 100)  # 반투명 패턴
        
        # 수직/수평 라인
        for i in range(0, self.size, 64):
            if i % 128 == 0:
                draw.line([(i, 0), (i, self.size)], fill=pattern_color, width=1)
                draw.line([(0, i), (self.size, i)], fill=pattern_color, width=1)
        
        # 코너에 회로 노드
        node_positions = [
            (50, 50), (self.size-50, 50), 
            (50, self.size-50), (self.size-50, self.size-50)
        ]
        for x, y in node_positions:
            draw.ellipse([x-4, y-4, x+4, y+4], fill=(60, 60, 100, 150))
    
    def draw_borders(self, draw):
        """원형 테두리 그리기 (외곽 + 내부)"""
        # 외곽 테두리
        outer_radius = int(self.size * self.outer_border_ratio / 2)
        outer_bbox = [
            self.center - outer_radius, self.center - outer_radius,
            self.center + outer_radius, self.center + outer_radius
        ]
        draw.ellipse(outer_bbox, outline=self.stamp_color, width=int(self.size * 0.025))
        
        # 내부 테두리
        inner_radius = int(self.size * self.inner_border_ratio / 2)
        inner_bbox = [
            self.center - inner_radius, self.center - inner_radius,
            self.center + inner_radius, self.center + inner_radius
        ]
        draw.ellipse(inner_bbox, outline=self.stamp_color, width=int(self.size * 0.015))
        
        return outer_radius, inner_radius
    
    def draw_center_lines(self, draw):
        """가로/세로 중심축 그리기 (보조선)"""
        line_color = self.stamp_color + (80,)  # 반투명
        safe_radius = int(self.size * self.safe_area_ratio / 2)
        
        # 가로 중심선
        draw.line([
            (self.center - safe_radius, self.center),
            (self.center + safe_radius, self.center)
        ], fill=line_color, width=2)
        
        # 세로 중심선
        draw.line([
            (self.center, self.center - safe_radius),
            (self.center, self.center + safe_radius)
        ], fill=line_color, width=2)
    
    def calculate_font_size(self, text, num_rows=2):
        """
        글자 수에 따라 최적의 폰트 크기 계산
        테두리를 넘지 않도록 자동 조절
        """
        safe_radius = int(self.size * self.safe_area_ratio / 2)
        safe_diameter = safe_radius * 2
        
        # 행당 글자 수
        chars_per_row = math.ceil(len(text) / num_rows)
        
        # 각 글자가 차지할 수 있는 최대 크기
        max_char_width = safe_diameter / chars_per_row * 0.85
        max_char_height = safe_diameter / num_rows * 0.85
        
        # 더 작은 값 선택 (정사각형 글자 기준)
        font_size = int(min(max_char_width, max_char_height))
        
        return font_size
    
    def arrange_text_in_circle(self, text, num_rows=2):
        """
        원형 안에 텍스트 배치 좌표 계산
        4글자: 2x2 배열
        5글자: 상단 2글자, 하단 3글자 또는 상단 3글자, 하단 2글자
        """
        safe_radius = int(self.size * self.safe_area_ratio / 2)
        
        positions = []
        n = len(text)
        
        if n == 4:
            # 2x2 배열
            font_size = self.calculate_font_size(text, 2)
            offset = font_size * 0.55
            
            positions = [
                (self.center - offset, self.center - offset),  # 좌상
                (self.center + offset, self.center - offset),  # 우상
                (self.center - offset, self.center + offset),  # 좌하
                (self.center + offset, self.center + offset),  # 우하
            ]
            
        elif n == 5:
            # 상단 2글자, 하단 3글자
            font_size = self.calculate_font_size(text, 2)
            v_offset = font_size * 0.55
            h_offset_top = font_size * 0.55
            h_offset_bottom = font_size * 0.75
            
            positions = [
                # 상단 2글자
                (self.center - h_offset_top, self.center - v_offset),
                (self.center + h_offset_top, self.center - v_offset),
                # 하단 3글자
                (self.center - h_offset_bottom, self.center + v_offset),
                (self.center, self.center + v_offset),
                (self.center + h_offset_bottom, self.center + v_offset),
            ]
            
        elif n == 3:
            # 삼각형 배열
            font_size = self.calculate_font_size(text, 2)
            v_offset = font_size * 0.5
            h_offset = font_size * 0.6
            
            positions = [
                (self.center, self.center - v_offset),  # 상단 중앙
                (self.center - h_offset, self.center + v_offset),  # 좌하
                (self.center + h_offset, self.center + v_offset),  # 우하
            ]
            
        elif n == 2:
            # 가로 배열
            font_size = self.calculate_font_size(text, 1)
            h_offset = font_size * 0.55
            
            positions = [
                (self.center - h_offset, self.center),
                (self.center + h_offset, self.center),
            ]
            
        else:
            # 기본: 중앙 배치
            font_size = self.calculate_font_size(text, 1)
            positions = [(self.center, self.center)]
        
        return positions, font_size
    
    def draw_text(self, draw, text, use_serif=True):
        """텍스트 그리기"""
        positions, font_size = self.arrange_text_in_circle(text)
        
        # 폰트 로드
        font_path = self.serif_font_path if use_serif else self.font_path
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            # 대체 폰트
            font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", font_size)
        
        # 각 글자 그리기
        for i, char in enumerate(text):
            if i < len(positions):
                x, y = positions[i]
                
                # 글자 크기 측정
                bbox = draw.textbbox((0, 0), char, font=font)
                char_width = bbox[2] - bbox[0]
                char_height = bbox[3] - bbox[1]
                
                # 중앙 정렬
                draw_x = x - char_width / 2
                draw_y = y - char_height / 2
                
                # 글자 그리기 (약간의 그림자 효과)
                shadow_offset = 3
                draw.text((draw_x + shadow_offset, draw_y + shadow_offset), char, 
                         font=font, fill=(100, 20, 30, 150))
                draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
    
    def add_stamp_texture(self, img):
        """도장 질감 효과 추가 (약간의 불규칙성)"""
        import random
        
        pixels = img.load()
        width, height = img.size
        
        # 랜덤 노이즈로 도장 느낌 추가
        for _ in range(int(width * height * 0.001)):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            
            # 중심에서의 거리 계산
            dist = math.sqrt((x - self.center)**2 + (y - self.center)**2)
            max_dist = self.size * self.outer_border_ratio / 2
            
            if dist < max_dist:
                r, g, b, a = pixels[x, y]
                if r > 100:  # 빨간색 영역에만 적용
                    # 약간의 밝기 변화
                    variation = random.randint(-20, 20)
                    new_r = max(0, min(255, r + variation))
                    new_g = max(0, min(255, g + variation // 2))
                    new_b = max(0, min(255, b + variation // 2))
                    pixels[x, y] = (new_r, new_g, new_b, a)
        
        return img
    
    def generate(self, text, output_path, add_texture=True, show_guides=False):
        """
        도장 아이콘 생성
        
        Args:
            text: 도장에 새길 텍스트 (2-5글자 권장)
            output_path: 저장 경로
            add_texture: 도장 질감 효과 추가 여부
            show_guides: 가이드라인 표시 여부
        """
        # 기본 이미지 생성
        img = self.create_base_image()
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # 회로 패턴 (배경)
        self.draw_circuit_pattern(draw)
        
        # 테두리 그리기
        self.draw_borders(draw)
        
        # 가이드라인 (디버그용)
        if show_guides:
            self.draw_center_lines(draw)
        
        # 텍스트 그리기
        self.draw_text(draw, text)
        
        # 질감 효과
        if add_texture:
            img = self.add_stamp_texture(img)
        
        # 저장
        img.save(output_path, 'PNG')
        print(f"Generated: {output_path}")
        
        return img


def main():
    generator = StampIconGenerator(size=1024)
    
    output_dir = "/home/ubuntu/madstamp-automation/chrome-extension/assets"
    os.makedirs(output_dir, exist_ok=True)
    
    # 다양한 텍스트로 아이콘 생성
    texts = [
        "매드",      # 2글자
        "스탬프",    # 3글자
        "매드스탬",  # 4글자
        "매드스탬프", # 5글자
    ]
    
    for text in texts:
        output_path = f"{output_dir}/icon-stamp-{len(text)}char.png"
        generator.generate(text, output_path, add_texture=True, show_guides=False)
    
    # 최종 아이콘 (4글자 버전을 메인으로)
    main_icon_path = f"{output_dir}/icon-stamp-main.png"
    generator.generate("매드스탬", main_icon_path, add_texture=True, show_guides=False)
    
    print("\n모든 아이콘 생성 완료!")


if __name__ == "__main__":
    main()
