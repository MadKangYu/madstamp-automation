#!/usr/bin/env python3
"""
Madstamp 도장 생성기 - 펜툴 방식 v11
===================================

v10에서 개선:
- 글자 간격 더 좁게 (거의 붙을 듯)
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

class PentoolStampGenerator:
    
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
        
        self.output_dir = '/home/ubuntu/madstamp-automation/chrome-extension/assets/stamps'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_font(self, font_name, font_size):
        font_path = self.fonts.get(font_name)
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                pass
        return ImageFont.load_default()
    
    def create_stamp(self, text, font_name='noto_serif'):
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
        
        if len(chars) == 5:
            self._draw_5char(draw, chars, inner_radius, font_name)
        elif len(chars) == 4:
            self._draw_4char(draw, chars, inner_radius, font_name)
        
        return img
    
    def _draw_5char(self, draw, chars, radius, font_name):
        """
        5글자 배치 (상단 2 + 하단 3)
        """
        r = radius
        
        # 상단/하단 y 위치
        row_offset = r * 0.26
        top_y = self.cy - row_offset
        bottom_y = self.cy + row_offset
        
        # 하단 y에서 원 안에 들어갈 수 있는 가로폭
        dy = row_offset
        half_width = math.sqrt(r * r - dy * dy) if dy < r else 0
        
        # 글자 크기 계산 - 간격 최소화
        gap_ratio = 0.01  # 거의 붙을 듯 (1%)
        available_width = half_width * 2 * 0.92
        
        # 하단 3글자 기준
        char_size = int(available_width / (3 + 2 * gap_ratio))
        gap = int(char_size * gap_ratio)
        
        font_size = int(char_size * 0.95)
        font = self.get_font(font_name, font_size)
        
        # 하단 3글자 배치
        step = char_size + gap
        
        bottom_positions = [
            (self.cx - step, bottom_y),
            (self.cx, bottom_y),
            (self.cx + step, bottom_y),
        ]
        
        # 상단 2글자 배치
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
    
    def _draw_4char(self, draw, chars, radius, font_name):
        """
        4글자 배치 (2x2)
        """
        r = radius
        
        gap_ratio = 0.01
        max_side = r * math.sqrt(2) * 0.88
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
    
    def save(self, img, filename):
        path = os.path.join(self.output_dir, filename)
        img.save(path, 'PNG')
        print(f"저장됨: {path}")
        return path


def main():
    generator = PentoolStampGenerator(size=1024)
    
    print("=== 매드스탬프 (5글자) - v11 ===")
    img = generator.create_stamp("매드스탬프", 'noto_serif')
    generator.save(img, "stamp_5char_v11.png")
    
    print("\n완료!")


if __name__ == '__main__':
    main()
