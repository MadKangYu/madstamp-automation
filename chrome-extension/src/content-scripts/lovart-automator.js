/**
 * Madstamp - Lovart AI 자동화 Content Script
 * 
 * Lovart AI 웹사이트에서 도장 이미지 생성을 자동화합니다.
 * - 프롬프트 자동 입력
 * - 참조 이미지 업로드
 * - 이미지 생성 대기 및 다운로드
 */

(function() {
  'use strict';

  // ============================================
  // 상수 정의
  // ============================================
  const MADSTAMP_PANEL_ID = 'madstamp-lovart-panel';
  const STORAGE_KEY = 'madstamp_lovart_settings';
  
  // 도장 스타일별 프롬프트 템플릿
  const PROMPT_TEMPLATES = {
    traditional_korean: {
      name: '한국 전통 도장 (낙관)',
      prompt: 'Traditional Korean seal stamp (Nakgwan), red ink impression, elegant calligraphy style, circular or square shape, high contrast black and white design suitable for rubber stamp production, clean lines, minimalist, professional quality'
    },
    modern_logo: {
      name: '현대적 로고 스타일',
      prompt: 'Modern logo stamp design, clean geometric shapes, professional business seal, high contrast black and white, vector-like quality, suitable for rubber stamp production, minimalist design'
    },
    handwriting_style: {
      name: '손글씨 스타일',
      prompt: 'Handwritten signature style stamp, elegant cursive script, personal seal design, high contrast black and white, suitable for rubber stamp production, artistic calligraphy'
    },
    company_seal: {
      name: '회사 직인',
      prompt: 'Official company seal stamp, formal corporate design, circular shape with company name, professional business stamp, high contrast black and white, clean typography, suitable for rubber stamp production'
    },
    custom: {
      name: '커스텀 프롬프트',
      prompt: ''
    }
  };

  // ============================================
  // 유틸리티 함수
  // ============================================
  
  /**
   * 요소가 나타날 때까지 대기
   */
  function waitForElement(selector, timeout = 10000) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      
      const checkElement = () => {
        const element = document.querySelector(selector);
        if (element) {
          resolve(element);
          return;
        }
        
        if (Date.now() - startTime > timeout) {
          reject(new Error(`Element not found: ${selector}`));
          return;
        }
        
        requestAnimationFrame(checkElement);
      };
      
      checkElement();
    });
  }

  /**
   * 지정된 시간만큼 대기
   */
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 텍스트를 클립보드에 복사
   */
  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.error('클립보드 복사 실패:', err);
      return false;
    }
  }

  /**
   * 알림 표시
   */
  function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `madstamp-notification madstamp-notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.classList.add('madstamp-notification-fade');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // ============================================
  // Lovart AI 자동화 클래스
  // ============================================
  class LovartAutomator {
    constructor() {
      this.isProcessing = false;
      this.currentOrder = null;
      this.settings = this.loadSettings();
    }

    /**
     * 설정 로드
     */
    loadSettings() {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : {
          autoDownload: true,
          resolution: '4k',
          defaultTemplate: 'traditional_korean'
        };
      } catch (e) {
        return {
          autoDownload: true,
          resolution: '4k',
          defaultTemplate: 'traditional_korean'
        };
      }
    }

    /**
     * 설정 저장
     */
    saveSettings(settings) {
      this.settings = { ...this.settings, ...settings };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.settings));
    }

    /**
     * 프롬프트 입력 필드 찾기
     */
    findPromptInput() {
      // Lovart AI의 프롬프트 입력 필드 선택자들
      const selectors = [
        'textarea[placeholder*="idea"]',
        'textarea[placeholder*="prompt"]',
        'input[placeholder*="idea"]',
        '.prompt-input textarea',
        '[data-testid="prompt-input"]',
        'textarea'
      ];

      for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element) return element;
      }

      return null;
    }

    /**
     * 생성 버튼 찾기
     */
    findGenerateButton() {
      const selectors = [
        'button[type="submit"]',
        'button:contains("Generate")',
        'button:contains("생성")',
        '.generate-button',
        '[data-testid="generate-button"]'
      ];

      // 텍스트로 버튼 찾기
      const buttons = document.querySelectorAll('button');
      for (const btn of buttons) {
        const text = btn.textContent.toLowerCase();
        if (text.includes('generate') || text.includes('생성') || text.includes('create')) {
          return btn;
        }
      }

      for (const selector of selectors) {
        try {
          const element = document.querySelector(selector);
          if (element) return element;
        } catch (e) {
          continue;
        }
      }

      return null;
    }

    /**
     * 프롬프트 입력
     */
    async inputPrompt(prompt) {
      const input = this.findPromptInput();
      if (!input) {
        throw new Error('프롬프트 입력 필드를 찾을 수 없습니다.');
      }

      // 기존 내용 지우기
      input.value = '';
      input.focus();

      // 프롬프트 입력 (자연스러운 타이핑 시뮬레이션)
      for (const char of prompt) {
        input.value += char;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(10); // 타이핑 딜레이
      }

      // 변경 이벤트 발생
      input.dispatchEvent(new Event('change', { bubbles: true }));
      
      return true;
    }

    /**
     * 이미지 생성 시작
     */
    async startGeneration() {
      const button = this.findGenerateButton();
      if (!button) {
        throw new Error('생성 버튼을 찾을 수 없습니다.');
      }

      button.click();
      showNotification('이미지 생성을 시작합니다...', 'info');
      
      return true;
    }

    /**
     * 이미지 생성 완료 대기
     */
    async waitForGeneration(timeout = 120000) {
      const startTime = Date.now();
      
      while (Date.now() - startTime < timeout) {
        // 생성된 이미지 찾기
        const generatedImages = document.querySelectorAll('img[src*="generated"], .generated-image, [data-generated="true"]');
        
        // 로딩 인디케이터 확인
        const isLoading = document.querySelector('.loading, .generating, [data-loading="true"]');
        
        if (generatedImages.length > 0 && !isLoading) {
          showNotification('이미지 생성이 완료되었습니다!', 'success');
          return Array.from(generatedImages);
        }

        await sleep(2000);
      }

      throw new Error('이미지 생성 시간 초과');
    }

    /**
     * 생성된 이미지 다운로드
     */
    async downloadGeneratedImage(imageElement) {
      if (!imageElement || !imageElement.src) {
        throw new Error('다운로드할 이미지를 찾을 수 없습니다.');
      }

      // 다운로드 요청을 Background Script로 전송
      chrome.runtime.sendMessage({
        action: 'downloadImage',
        url: imageElement.src,
        filename: `madstamp_${Date.now()}.png`
      });

      showNotification('이미지 다운로드를 시작합니다.', 'success');
    }

    /**
     * 전체 자동화 프로세스 실행
     */
    async runAutomation(orderData) {
      if (this.isProcessing) {
        showNotification('이미 처리 중인 작업이 있습니다.', 'warning');
        return;
      }

      this.isProcessing = true;
      this.currentOrder = orderData;

      try {
        // 1. 프롬프트 생성
        const template = PROMPT_TEMPLATES[orderData.template] || PROMPT_TEMPLATES.traditional_korean;
        let prompt = template.prompt;
        
        if (orderData.customPrompt) {
          prompt = orderData.customPrompt;
        }
        
        if (orderData.additionalDetails) {
          prompt += `, ${orderData.additionalDetails}`;
        }

        // 2. 프롬프트 입력
        showNotification('프롬프트를 입력합니다...', 'info');
        await this.inputPrompt(prompt);
        await sleep(500);

        // 3. 이미지 생성 시작
        await this.startGeneration();

        // 4. 생성 완료 대기
        const images = await this.waitForGeneration();

        // 5. 자동 다운로드 (설정에 따라)
        if (this.settings.autoDownload && images.length > 0) {
          await this.downloadGeneratedImage(images[0]);
        }

        // 6. 완료 메시지 전송
        chrome.runtime.sendMessage({
          action: 'generationComplete',
          orderId: orderData.orderId,
          imageCount: images.length
        });

        showNotification('자동화 프로세스가 완료되었습니다!', 'success');

      } catch (error) {
        console.error('자동화 오류:', error);
        showNotification(`오류: ${error.message}`, 'error');
        
        chrome.runtime.sendMessage({
          action: 'generationError',
          orderId: orderData?.orderId,
          error: error.message
        });

      } finally {
        this.isProcessing = false;
        this.currentOrder = null;
      }
    }
  }

  // ============================================
  // UI 패널 생성
  // ============================================
  function createControlPanel() {
    // 기존 패널이 있으면 제거
    const existingPanel = document.getElementById(MADSTAMP_PANEL_ID);
    if (existingPanel) {
      existingPanel.remove();
    }

    const panel = document.createElement('div');
    panel.id = MADSTAMP_PANEL_ID;
    panel.innerHTML = `
      <div class="madstamp-panel-header">
        <span class="madstamp-logo">🔴 Madstamp</span>
        <button class="madstamp-minimize-btn">−</button>
      </div>
      <div class="madstamp-panel-content">
        <div class="madstamp-section">
          <label>도장 스타일</label>
          <select id="madstamp-template">
            ${Object.entries(PROMPT_TEMPLATES).map(([key, val]) => 
              `<option value="${key}">${val.name}</option>`
            ).join('')}
          </select>
        </div>
        
        <div class="madstamp-section">
          <label>추가 설명 (선택)</label>
          <textarea id="madstamp-additional" placeholder="예: 회사명 'GOOPICK', 원형 도장"></textarea>
        </div>
        
        <div class="madstamp-section">
          <label>커스텀 프롬프트 (선택)</label>
          <textarea id="madstamp-custom-prompt" placeholder="직접 프롬프트를 입력하세요..."></textarea>
        </div>
        
        <div class="madstamp-actions">
          <button id="madstamp-copy-prompt" class="madstamp-btn madstamp-btn-secondary">
            📋 프롬프트 복사
          </button>
          <button id="madstamp-generate" class="madstamp-btn madstamp-btn-primary">
            🚀 자동 생성
          </button>
        </div>
        
        <div class="madstamp-status" id="madstamp-status">
          대기 중
        </div>
      </div>
    `;

    document.body.appendChild(panel);

    // 이벤트 리스너 등록
    setupPanelEvents(panel);
  }

  /**
   * 패널 이벤트 설정
   */
  function setupPanelEvents(panel) {
    const automator = new LovartAutomator();

    // 최소화 버튼
    panel.querySelector('.madstamp-minimize-btn').addEventListener('click', () => {
      panel.classList.toggle('madstamp-panel-minimized');
    });

    // 프롬프트 복사 버튼
    panel.querySelector('#madstamp-copy-prompt').addEventListener('click', async () => {
      const template = panel.querySelector('#madstamp-template').value;
      const additional = panel.querySelector('#madstamp-additional').value;
      const custom = panel.querySelector('#madstamp-custom-prompt').value;

      let prompt = custom || PROMPT_TEMPLATES[template].prompt;
      if (additional) {
        prompt += `, ${additional}`;
      }

      const success = await copyToClipboard(prompt);
      if (success) {
        showNotification('프롬프트가 클립보드에 복사되었습니다.', 'success');
      }
    });

    // 자동 생성 버튼
    panel.querySelector('#madstamp-generate').addEventListener('click', async () => {
      const template = panel.querySelector('#madstamp-template').value;
      const additional = panel.querySelector('#madstamp-additional').value;
      const custom = panel.querySelector('#madstamp-custom-prompt').value;

      const statusEl = panel.querySelector('#madstamp-status');
      statusEl.textContent = '처리 중...';
      statusEl.className = 'madstamp-status madstamp-status-processing';

      await automator.runAutomation({
        template: template,
        additionalDetails: additional,
        customPrompt: custom,
        orderId: `manual_${Date.now()}`
      });

      statusEl.textContent = '완료';
      statusEl.className = 'madstamp-status madstamp-status-complete';
    });
  }

  // ============================================
  // 메시지 리스너 (Background Script와 통신)
  // ============================================
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const automator = new LovartAutomator();

    switch (message.action) {
      case 'runAutomation':
        automator.runAutomation(message.orderData)
          .then(() => sendResponse({ success: true }))
          .catch(err => sendResponse({ success: false, error: err.message }));
        return true; // 비동기 응답

      case 'getStatus':
        sendResponse({
          isProcessing: automator.isProcessing,
          currentOrder: automator.currentOrder
        });
        break;

      case 'updateSettings':
        automator.saveSettings(message.settings);
        sendResponse({ success: true });
        break;

      default:
        sendResponse({ error: 'Unknown action' });
    }
  });

  // ============================================
  // 초기화
  // ============================================
  function initialize() {
    // Lovart AI 페이지가 완전히 로드된 후 패널 생성
    if (document.readyState === 'complete') {
      createControlPanel();
    } else {
      window.addEventListener('load', createControlPanel);
    }

    console.log('Madstamp Lovart Automator 초기화 완료');
  }

  // 실행
  initialize();

})();
