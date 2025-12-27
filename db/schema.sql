-- =============================================================================
-- Madstamp Automation - Supabase 데이터베이스 스키마
-- =============================================================================
-- 이 파일을 Supabase SQL Editor에서 실행하여 테이블을 생성합니다.
-- 버전: 1.0.0
-- 최종 수정: 2024-12-27

-- -----------------------------------------------------------------------------
-- 확장 기능 활성화
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. customers: 고객 정보
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100),
    phone VARCHAR(20),
    company VARCHAR(200),
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE customers IS '고객 정보 테이블';
COMMENT ON COLUMN customers.email IS '고객 이메일 주소 (고유)';
COMMENT ON COLUMN customers.name IS '고객 이름';
COMMENT ON COLUMN customers.phone IS '고객 연락처';
COMMENT ON COLUMN customers.company IS '고객 회사명';

-- -----------------------------------------------------------------------------
-- 2. orders: 주문 요청
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    email_message_id VARCHAR(255),
    email_thread_id VARCHAR(255),
    subject VARCHAR(500),
    body TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    -- 상태값:
    -- pending: 대기 중
    -- analyzing: 분석 중
    -- producible: 제작 가능
    -- needs_clarification: 확인 필요
    -- not_producible: 제작 불가
    -- generating: 이미지 생성 중
    -- converting: 벡터 변환 중
    -- completed: 완료
    -- failed: 실패
    -- cancelled: 취소
    priority INTEGER DEFAULT 0,
    admin_notes TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

COMMENT ON TABLE orders IS '도장 제작 주문 요청 테이블';
COMMENT ON COLUMN orders.status IS '주문 상태 (pending, analyzing, producible, needs_clarification, not_producible, generating, converting, completed, failed, cancelled)';
COMMENT ON COLUMN orders.email_message_id IS 'Gmail 메시지 ID';
COMMENT ON COLUMN orders.email_thread_id IS 'Gmail 스레드 ID';

-- -----------------------------------------------------------------------------
-- 3. attachments: 첨부 이미지
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    original_filename VARCHAR(255),
    storage_path VARCHAR(500),
    storage_url VARCHAR(1000),
    file_size INTEGER,
    mime_type VARCHAR(100),
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE attachments IS '주문에 첨부된 이미지 파일';
COMMENT ON COLUMN attachments.storage_path IS 'Supabase Storage 경로';
COMMENT ON COLUMN attachments.storage_url IS '공개 접근 URL';

-- -----------------------------------------------------------------------------
-- 4. image_analyses: 이미지 분석 결과
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attachment_id UUID NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL,
    -- 분석 유형:
    -- vision: AI 비전 분석 (OpenRouter Grok-4.1-fast)
    -- ocr: 텍스트 추출 (OCR.space)
    -- font_detection: 폰트 감지
    result JSONB,
    confidence DECIMAL(5,4),
    is_producible BOOLEAN,
    producibility_reason TEXT,
    detected_text TEXT,
    detected_font_style VARCHAR(100),
    recommended_font VARCHAR(100),
    image_quality VARCHAR(50),
    -- 이미지 품질: excellent, good, fair, poor
    suggestions TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE image_analyses IS '이미지 분석 결과 저장';
COMMENT ON COLUMN image_analyses.analysis_type IS '분석 유형 (vision, ocr, font_detection)';
COMMENT ON COLUMN image_analyses.is_producible IS '제작 가능 여부';
COMMENT ON COLUMN image_analyses.producibility_reason IS '제작 가능/불가 판단 이유';

-- -----------------------------------------------------------------------------
-- 5. generated_images: 생성된 이미지
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generated_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    lovart_project_id VARCHAR(255),
    lovart_project_url VARCHAR(500),
    original_image_path VARCHAR(500),
    original_image_url VARCHAR(1000),
    vector_svg_path VARCHAR(500),
    vector_svg_url VARCHAR(1000),
    vector_eps_path VARCHAR(500),
    vector_eps_url VARCHAR(1000),
    resolution VARCHAR(20) DEFAULT '4K',
    -- 해상도: 4K, HD, SD
    status VARCHAR(50) DEFAULT 'pending',
    -- 상태: pending, generating, downloaded, converting, completed, failed
    generation_time_seconds INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

COMMENT ON TABLE generated_images IS 'Lovart AI로 생성된 이미지';
COMMENT ON COLUMN generated_images.prompt IS 'Lovart AI에 전달한 프롬프트';
COMMENT ON COLUMN generated_images.resolution IS '이미지 해상도 (4K, HD, SD)';

-- -----------------------------------------------------------------------------
-- 6. email_logs: 이메일 발송 이력
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    email_type VARCHAR(50) NOT NULL,
    -- 이메일 유형:
    -- confirmation: 접수 확인
    -- clarification: 추가 정보 요청
    -- progress: 진행 상황 알림
    -- delivery: 결과물 전달
    -- error: 오류 알림
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    body TEXT,
    attachments JSONB,
    gmail_message_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    -- 상태: pending, sent, failed
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE email_logs IS '이메일 발송 이력';
COMMENT ON COLUMN email_logs.email_type IS '이메일 유형 (confirmation, clarification, progress, delivery, error)';

-- -----------------------------------------------------------------------------
-- 7. fonts: 사용 가능한 폰트 라이브러리
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fonts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    family VARCHAR(100),
    style VARCHAR(50),
    -- 스타일: serif, sans-serif, handwriting, display, monospace
    weight VARCHAR(50),
    -- 굵기: thin, light, regular, medium, bold, black
    license_type VARCHAR(50) NOT NULL,
    -- 라이선스: OFL, Apache, MIT, Free
    license_url VARCHAR(500),
    download_url VARCHAR(500),
    cdn_url VARCHAR(500),
    preview_url VARCHAR(500),
    korean_support BOOLEAN DEFAULT false,
    is_recommended BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE fonts IS '저작권 무료 폰트 라이브러리';
COMMENT ON COLUMN fonts.license_type IS '라이선스 유형 (OFL, Apache, MIT, Free)';
COMMENT ON COLUMN fonts.korean_support IS '한글 지원 여부';

-- -----------------------------------------------------------------------------
-- 8. settings: 시스템 설정
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100)
);

COMMENT ON TABLE settings IS '시스템 설정 키-값 저장소';

-- -----------------------------------------------------------------------------
-- 9. activity_logs: 시스템 활동 로그
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,
    -- 엔티티 유형: order, customer, image, email
    entity_id UUID,
    action VARCHAR(50) NOT NULL,
    -- 액션: created, updated, deleted, analyzed, generated, sent
    details JSONB,
    performed_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE activity_logs IS '시스템 활동 로그';

-- -----------------------------------------------------------------------------
-- 인덱스 생성
-- -----------------------------------------------------------------------------
-- customers
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_created ON customers(created_at DESC);

-- orders
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_email_message ON orders(email_message_id);

-- attachments
CREATE INDEX IF NOT EXISTS idx_attachments_order ON attachments(order_id);

-- image_analyses
CREATE INDEX IF NOT EXISTS idx_analyses_attachment ON image_analyses(attachment_id);
CREATE INDEX IF NOT EXISTS idx_analyses_type ON image_analyses(analysis_type);
CREATE INDEX IF NOT EXISTS idx_analyses_producible ON image_analyses(is_producible);

-- generated_images
CREATE INDEX IF NOT EXISTS idx_generated_order ON generated_images(order_id);
CREATE INDEX IF NOT EXISTS idx_generated_status ON generated_images(status);

-- email_logs
CREATE INDEX IF NOT EXISTS idx_email_logs_order ON email_logs(order_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);

-- fonts
CREATE INDEX IF NOT EXISTS idx_fonts_style ON fonts(style);
CREATE INDEX IF NOT EXISTS idx_fonts_korean ON fonts(korean_support);
CREATE INDEX IF NOT EXISTS idx_fonts_recommended ON fonts(is_recommended);

-- activity_logs
CREATE INDEX IF NOT EXISTS idx_activity_entity ON activity_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at DESC);

-- -----------------------------------------------------------------------------
-- 트리거: updated_at 자동 업데이트
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- 초기 데이터: 시스템 설정
-- -----------------------------------------------------------------------------
INSERT INTO settings (key, value, description) VALUES
    ('target_email', '"goopick@goopick.net"', '모니터링할 이메일 주소'),
    ('admin_email', '"richardowen7212@gmail.com"', '관리자 알림 이메일'),
    ('default_resolution', '"4K"', '기본 이미지 해상도'),
    ('auto_reply_enabled', 'true', '자동 응답 활성화 여부'),
    ('max_retries', '3', '최대 재시도 횟수'),
    ('company_info', '{"name": "Madstamp", "business_number": "880-86-02373", "phone": "+82 10 5911 2822", "email": "goopick@goopick.net"}', '회사 정보')
ON CONFLICT (key) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 초기 데이터: 추천 폰트
-- -----------------------------------------------------------------------------
INSERT INTO fonts (name, family, style, license_type, license_url, cdn_url, korean_support, is_recommended) VALUES
    ('Noto Sans Korean', 'Noto Sans KR', 'sans-serif', 'OFL', 'https://scripts.sil.org/OFL', 'https://fonts.googleapis.com/css2?family=Noto+Sans+KR', true, true),
    ('Noto Serif Korean', 'Noto Serif KR', 'serif', 'OFL', 'https://scripts.sil.org/OFL', 'https://fonts.googleapis.com/css2?family=Noto+Serif+KR', true, true),
    ('Pretendard', 'Pretendard', 'sans-serif', 'OFL', 'https://scripts.sil.org/OFL', 'https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css', true, true),
    ('나눔고딕', 'Nanum Gothic', 'sans-serif', 'OFL', 'https://scripts.sil.org/OFL', 'https://fonts.googleapis.com/css2?family=Nanum+Gothic', true, true),
    ('나눔명조', 'Nanum Myeongjo', 'serif', 'OFL', 'https://scripts.sil.org/OFL', 'https://fonts.googleapis.com/css2?family=Nanum+Myeongjo', true, true),
    ('나눔손글씨 펜', 'Nanum Pen Script', 'handwriting', 'OFL', 'https://scripts.sil.org/OFL', 'https://fonts.googleapis.com/css2?family=Nanum+Pen+Script', true, true),
    ('마루 부리', 'MaruBuri', 'serif', 'OFL', 'https://scripts.sil.org/OFL', NULL, true, true),
    ('IBM Plex Sans KR', 'IBM Plex Sans KR', 'sans-serif', 'OFL', 'https://scripts.sil.org/OFL', 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR', true, false)
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- Row Level Security (RLS) 설정
-- -----------------------------------------------------------------------------
-- 주의: 실제 운영 환경에서는 적절한 RLS 정책을 설정해야 합니다.
-- 아래는 서비스 역할 키를 사용하는 백엔드 전용 설정입니다.

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE fonts ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- 서비스 역할에 대한 전체 접근 허용
CREATE POLICY "Service role has full access to customers" ON customers FOR ALL USING (true);
CREATE POLICY "Service role has full access to orders" ON orders FOR ALL USING (true);
CREATE POLICY "Service role has full access to attachments" ON attachments FOR ALL USING (true);
CREATE POLICY "Service role has full access to image_analyses" ON image_analyses FOR ALL USING (true);
CREATE POLICY "Service role has full access to generated_images" ON generated_images FOR ALL USING (true);
CREATE POLICY "Service role has full access to email_logs" ON email_logs FOR ALL USING (true);
CREATE POLICY "Service role has full access to fonts" ON fonts FOR ALL USING (true);
CREATE POLICY "Service role has full access to settings" ON settings FOR ALL USING (true);
CREATE POLICY "Service role has full access to activity_logs" ON activity_logs FOR ALL USING (true);

-- =============================================================================
-- 스키마 생성 완료
-- =============================================================================
