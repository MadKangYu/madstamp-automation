#!/usr/bin/env python3
"""
Madstamp 원형 도장 생성기
========================

지원 글자 수: 1~5글자
- 1글자: 양면도장 (중앙 배치, 크게)
- 2글자: 가로 배치
- 3글자: 가로형 또는 세로형 선택 가능
- 4글자: 2x2 격자
- 5글자: 상단 2 + 하단 3

배치 규칙:
- 중심선 기준 좌우 대칭
- 글자 간격: 거의 붙을 듯
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math


class CircleStampGenerator:
    
    def __init__(self, size=1024):
        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        
        self.fonts = {
            'noto_serif': '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',
            'noto_sans': '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
        }
        
        self.stamp_color = (200, 30, 30)
        self.bg_color = (255, 255, 255, 0)
        
        self.output_dir = './output'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_font(self, font_name, font_size):
        font_path = self.fonts.get(font_name)
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                pass
        return ImageFont.load_default()
    
    def create_stamp(self, text, font_name='noto_serif', layout_3char='horizontal'):
        """
        도장 생성
        
        Args:
            text: 도장에 들어갈 텍스트 (1~5글자)
            font_name: 폰트 이름 ('noto_serif' 또는 'noto_sans')
            layout_3char: 3글자 배치 방식 ('horizontal'=가로, 'vertical'=세로)
        
        Returns:
            PIL Image 객체
        """
        img = Image.new('RGBA', (self.size, self.size), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # 외곽 원
        margin = int(self.size * 0.03)
        radius = (self.size // 2) - margin
        border_width = int(self.size * 0.035)
        
        draw.ellipse(
            [self.cx - radius, self.cy - radius,
             self.cx + radius, self.cy + radius],
            outline=self.stamp_color, width=border_width
        )
        
        inner_radius = radius - border_width // 2 - int(self.size * 0.02)
        
        chars = list(text)
        char_count = len(chars)
        
        if char_count == 1:
            self._draw_1char(draw, chars, inner_radius, font_name)
        elif char_count == 2:
            self._draw_2char(draw, chars, inner_radius, font_name)
        elif char_count == 3:
            if layout_3char == 'vertical':
                self._draw_3char_vertical(draw, chars, inner_radius, font_name)
            else:
                self._draw_3char_horizontal(draw, chars, inner_radius, font_name)
        elif char_count == 4:
            self._draw_4char(draw, chars, inner_radius, font_name)
        elif char_count == 5:
            self._draw_5char(draw, chars, inner_radius, font_name)
        
        return img
    
    def _draw_1char(self, draw, chars, radius, font_name):
        """
        1글자 배치 (양면도장) - 중앙 배치, 크게
        """
        # 글자 크기: 원 지름의 85% (더 크게)
        char_size = int(radius * 2 * 0.82)
        font_size = int(char_size * 0.95)
        font = self.get_font(font_name, font_size)
        
        char = chars[0]
        bbox = draw.textbbox((0, 0), char, font=font)
        bbox_cx = (bbox[0] + bbox[2]) / 2
        bbox_cy = (bbox[1] + bbox[3]) / 2
        
        draw_x = self.cx - bbox_cx
        draw_y = self.cy - bbox_cy
        
        draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
    
    def _draw_2char(self, draw, chars, radius, font_name):
        """
        2글자 배치 - 가로 배치
        """
        gap_ratio = 0.02
        available_width = radius * 2 * 0.85
        char_size = int(available_width / (2 + gap_ratio))
        gap = int(char_size * gap_ratio)
        
        font_size = int(char_size * 0.95)
        font = self.get_font(font_name, font_size)
        
        half_step = (char_size + gap) / 2
        
        positions = [
            (self.cx - half_step, self.cy),
            (self.cx + half_step, self.cy),
        ]
        
        for i, (target_x, target_y) in enumerate(positions):
            char = chars[i]
            bbox = draw.textbbox((0, 0), char, font=font)
            bbox_cx = (bbox[0] + bbox[2]) / 2
            bbox_cy = (bbox[1] + bbox[3]) / 2
            
            draw_x = target_x - bbox_cx
            draw_y = target_y - bbox_cy
            
            draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
    
    def _draw_3char_horizontal(self, draw, chars, radius, font_name):
        """
        3글자 가로형 배치 - 한 줄에 3글자
        """
        gap_ratio = 0.02
        available_width = radius * 2 * 0.92
        char_size = int(available_width / (3 + 2 * gap_ratio))
        gap = int(char_size * gap_ratio)
        
        font_size = int(char_size * 0.95)
        font = self.get_font(font_name, font_size)
        
        step = char_size + gap
        
        positions = [
            (self.cx - step, self.cy),
            (self.cx, self.cy),
            (self.cx + step, self.cy),
        ]
        
        for i, (target_x, target_y) in enumerate(positions):
            char = chars[i]
            bbox = draw.textbbox((0, 0), char, font=font)
            bbox_cx = (bbox[0] + bbox[2]) / 2
            bbox_cy = (bbox[1] + bbox[3]) / 2
            
            draw_x = target_x - bbox_cx
            draw_y = target_y - bbox_cy
            
            draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
    
    def _draw_3char_vertical(self, draw, chars, radius, font_name):
        """
        3글자 세로형 배치 - 세로로 3글자
        """
        gap_ratio = 0.02
        available_height = radius * 2 * 0.92
        char_size = int(available_height / (3 + 2 * gap_ratio))
        gap = int(char_size * gap_ratio)
        
        font_size = int(char_size * 0.95)
        font = self.get_font(font_name, font_size)
        
        step = char_size + gap
        
        positions = [
            (self.cx, self.cy - step),
            (self.cx, self.cy),
            (self.cx, self.cy + step),
        ]
        
        for i, (target_x, target_y) in enumerate(positions):
            char = chars[i]
            bbox = draw.textbbox((0, 0), char, font=font)
            bbox_cx = (bbox[0] + bbox[2]) / 2
            bbox_cy = (bbox[1] + bbox[3]) / 2
            
            draw_x = target_x - bbox_cx
            draw_y = target_y - bbox_cy
            
            draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
    
    def _draw_4char(self, draw, chars, radius, font_name):
        """
        4글자 배치 (2x2)
        """
        gap_ratio = 0.01
        max_side = radius * math.sqrt(2) * 0.88
        char_size = int(max_side / (2 + gap_ratio))
        gap = int(char_size * gap_ratio)
        
        font_size = int(char_size * 0.95)
        font = self.get_font(font_name, font_size)
        
        half_step = (char_size + gap) / 2
        
        top_y = self.cy - half_step
        bottom_y = self.cy + half_step
        
        positions = [
            (self.cx - half_step, top_y),
            (self.cx + half_step, top_y),
            (self.cx - half_step, bottom_y),
            (self.cx + half_step, bottom_y),
        ]
        
        for i, (target_x, target_y) in enumerate(positions):
            char = chars[i]
            bbox = draw.textbbox((0, 0), char, font=font)
            bbox_cx = (bbox[0] + bbox[2]) / 2
            bbox_cy = (bbox[1] + bbox[3]) / 2
            
            draw_x = target_x - bbox_cx
            draw_y = target_y - bbox_cy
            
            draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
    
    def _draw_5char(self, draw, chars, radius, font_name):
        """
        5글자 배치 (상단 2 + 하단 3)
        """
        r = radius
        
        row_offset = r * 0.26
        top_y = self.cy - row_offset
        bottom_y = self.cy + row_offset
        
        dy = row_offset
        half_width = math.sqrt(r * r - dy * dy) if dy < r else 0
        
        gap_ratio = 0.01
        available_width = half_width * 2 * 0.92
        
        char_size = int(available_width / (3 + 2 * gap_ratio))
        gap = int(char_size * gap_ratio)
        
        font_size = int(char_size * 0.95)
        font = self.get_font(font_name, font_size)
        
        step = char_size + gap
        
        bottom_positions = [
            (self.cx - step, bottom_y),
            (self.cx, bottom_y),
            (self.cx + step, bottom_y),
        ]
        
        half_step = (char_size + gap) / 2
        
        top_positions = [
            (self.cx - half_step, top_y),
            (self.cx + half_step, top_y),
        ]
        
        all_positions = top_positions + bottom_positions
        
        for i, (target_x, target_y) in enumerate(all_positions):
            char = chars[i]
            bbox = draw.textbbox((0, 0), char, font=font)
            bbox_cx = (bbox[0] + bbox[2]) / 2
            bbox_cy = (bbox[1] + bbox[3]) / 2
            
            draw_x = target_x - bbox_cx
            draw_y = target_y - bbox_cy
            
            draw.text((draw_x, draw_y), char, font=font, fill=self.stamp_color)
    
    def save(self, img, filename):
        path = os.path.join(self.output_dir, filename)
        img.save(path, 'PNG')
        print(f"저장됨: {path}")
        return path


def main():
    generator = CircleStampGenerator(size=1024)
    generator.output_dir = '/home/ubuntu/madstamp-automation/test_output'
    os.makedirs(generator.output_dir, exist_ok=True)
    
    test_cases = [
        ("강", "1글자 양면도장", {}),
        ("합격", "2글자", {}),
        ("대한민", "3글자 가로형", {'layout_3char': 'horizontal'}),
        ("대한민", "3글자 세로형", {'layout_3char': 'vertical'}),
        ("대한민국", "4글자", {}),
        ("매드스탬프", "5글자", {}),
    ]
    
    for text, desc, kwargs in test_cases:
        print(f"\n=== {desc}: {text} ({len(text)}글자) ===")
        img = generator.create_stamp(text, 'noto_serif', **kwargs)
        
        # 파일명 결정
        if '가로' in desc:
            filename = f"stamp_circle_{len(text)}char_horizontal.png"
        elif '세로' in desc:
            filename = f"stamp_circle_{len(text)}char_vertical.png"
        else:
            filename = f"stamp_circle_{len(text)}char.png"
        
        generator.save(img, filename)
    
    print("\n완료!")


if __name__ == '__main__':
    main()
