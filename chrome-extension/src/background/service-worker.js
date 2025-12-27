/**
 * Madstamp - Background Service Worker
 * 
 * 확장 프로그램의 백그라운드 작업을 관리합니다.
 * - 주문 관리
 * - 탭 간 통신
 * - 알림 처리
 * - 다운로드 관리
 */

// ============================================
// 상수 및 설정
// ============================================
const LOVART_URL = 'https://www.lovart.ai';
const GMAIL_URL = 'https://mail.google.com';

// ============================================
// 초기화
// ============================================
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('Madstamp 확장 프로그램 설치됨:', details.reason);
  
  // 기본 설정 초기화
  await chrome.storage.local.set({
    orders: [],
    gmailMonitoring: true,
    monitoringEmail: 'goopick@goopick.net',
    settings: {
      autoDownload: true,
      resolution: '4k',
      defaultTemplate: 'traditional_korean'
    }
  });
  
  // 설치 완료 알림
  if (details.reason === 'install') {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: '../assets/icons/icon128.png',
      title: 'Madstamp 설치 완료',
      message: '도장 이미지 자동화 확장 프로그램이 설치되었습니다.'
    });
  }
});

// ============================================
// 메시지 핸들러
// ============================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then(response => sendResponse(response))
    .catch(error => sendResponse({ success: false, error: error.message }));
  
  return true; // 비동기 응답을 위해 true 반환
});

async function handleMessage(message, sender) {
  switch (message.action) {
    // 주문 관리
    case 'createOrder':
      return await createOrder(message.orderData);
    
    case 'updateOrder':
      return await updateOrder(message.orderId, message.updates);
    
    case 'getOrders':
      return await getOrders();
    
    case 'deleteOrder':
      return await deleteOrder(message.orderId);
    
    // Lovart AI 관련
    case 'openLovart':
      return await openLovartTab();
    
    case 'generationComplete':
      return await handleGenerationComplete(message);
    
    case 'generationError':
      return await handleGenerationError(message);
    
    // Gmail 관련
    case 'setGmailMonitoring':
      return await setGmailMonitoring(message.enabled);
    
    case 'stampRequestDetected':
      return await handleStampRequestDetected(message);
    
    // 다운로드
    case 'downloadImage':
      return await downloadImage(message.url, message.filename);
    
    // 설정
    case 'getSettings':
      return await getSettings();
    
    case 'updateSettings':
      return await updateSettings(message.settings);
    
    default:
      throw new Error(`Unknown action: ${message.action}`);
  }
}

// ============================================
// 주문 관리 함수
// ============================================
async function createOrder(orderData) {
  const { orders = [] } = await chrome.storage.local.get(['orders']);
  
  const newOrder = {
    id: orderData.id || `MS${Date.now()}`,
    subject: orderData.subject || '',
    sender: orderData.sender || '',
    senderEmail: orderData.senderEmail || '',
    attachments: orderData.attachments || [],
    confidence: orderData.confidence || 0,
    keywords: orderData.keywords || [],
    status: 'pending',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
  
  orders.push(newOrder);
  await chrome.storage.local.set({ orders });
  
  // 알림 표시
  chrome.notifications.create({
    type: 'basic',
    iconUrl: '../assets/icons/icon128.png',
    title: '새 주문 생성',
    message: `${newOrder.subject || newOrder.id} 주문이 생성되었습니다.`
  });
  
  // Popup에 알림
  broadcastMessage({ action: 'orderCreated', order: newOrder });
  
  return { success: true, order: newOrder };
}

async function updateOrder(orderId, updates) {
  const { orders = [] } = await chrome.storage.local.get(['orders']);
  
  const index = orders.findIndex(o => o.id === orderId);
  if (index === -1) {
    throw new Error('주문을 찾을 수 없습니다.');
  }
  
  orders[index] = {
    ...orders[index],
    ...updates,
    updatedAt: new Date().toISOString()
  };
  
  await chrome.storage.local.set({ orders });
  
  // Popup에 알림
  broadcastMessage({ action: 'orderUpdated', order: orders[index] });
  
  return { success: true, order: orders[index] };
}

async function getOrders() {
  const { orders = [] } = await chrome.storage.local.get(['orders']);
  return { success: true, orders };
}

async function deleteOrder(orderId) {
  const { orders = [] } = await chrome.storage.local.get(['orders']);
  
  const filteredOrders = orders.filter(o => o.id !== orderId);
  await chrome.storage.local.set({ orders: filteredOrders });
  
  return { success: true };
}

// ============================================
// Lovart AI 관련 함수
// ============================================
async function openLovartTab() {
  // 이미 열린 Lovart 탭이 있는지 확인
  const tabs = await chrome.tabs.query({ url: `${LOVART_URL}/*` });
  
  if (tabs.length > 0) {
    // 기존 탭 활성화
    await chrome.tabs.update(tabs[0].id, { active: true });
    await chrome.windows.update(tabs[0].windowId, { focused: true });
    return { success: true, tabId: tabs[0].id };
  }
  
  // 새 탭 열기
  const tab = await chrome.tabs.create({ url: `${LOVART_URL}/ko/home` });
  return { success: true, tabId: tab.id };
}

async function handleGenerationComplete(message) {
  const { orderId, imageCount } = message;
  
  if (orderId) {
    await updateOrder(orderId, {
      status: 'completed',
      generatedImages: imageCount
    });
  }
  
  // 알림 표시
  chrome.notifications.create({
    type: 'basic',
    iconUrl: '../assets/icons/icon128.png',
    title: '이미지 생성 완료',
    message: `${imageCount}개의 이미지가 생성되었습니다.`
  });
  
  return { success: true };
}

async function handleGenerationError(message) {
  const { orderId, error } = message;
  
  if (orderId) {
    await updateOrder(orderId, {
      status: 'error',
      errorMessage: error
    });
  }
  
  // 알림 표시
  chrome.notifications.create({
    type: 'basic',
    iconUrl: '../assets/icons/icon128.png',
    title: '이미지 생성 실패',
    message: error || '알 수 없는 오류가 발생했습니다.'
  });
  
  return { success: true };
}

// ============================================
// Gmail 관련 함수
// ============================================
async function setGmailMonitoring(enabled) {
  await chrome.storage.local.set({ gmailMonitoring: enabled });
  return { success: true };
}

async function handleStampRequestDetected(message) {
  const { emailInfo } = message;
  
  // 자동으로 주문 생성
  const orderData = {
    id: `MS${Date.now()}`,
    subject: emailInfo.subject,
    sender: emailInfo.sender,
    senderEmail: emailInfo.senderEmail,
    attachments: emailInfo.attachments,
    confidence: emailInfo.confidence,
    keywords: emailInfo.matchedKeywords
  };
  
  await createOrder(orderData);
  
  return { success: true };
}

// ============================================
// 다운로드 함수
// ============================================
async function downloadImage(url, filename) {
  try {
    const downloadId = await chrome.downloads.download({
      url: url,
      filename: `Madstamp/${filename}`,
      saveAs: false
    });
    
    return { success: true, downloadId };
  } catch (error) {
    console.error('다운로드 실패:', error);
    return { success: false, error: error.message };
  }
}

// ============================================
// 설정 함수
// ============================================
async function getSettings() {
  const { settings = {} } = await chrome.storage.local.get(['settings']);
  return { success: true, settings };
}

async function updateSettings(newSettings) {
  const { settings = {} } = await chrome.storage.local.get(['settings']);
  
  const updatedSettings = { ...settings, ...newSettings };
  await chrome.storage.local.set({ settings: updatedSettings });
  
  return { success: true, settings: updatedSettings };
}

// ============================================
// 유틸리티 함수
// ============================================
function broadcastMessage(message) {
  // 모든 탭에 메시지 전송
  chrome.tabs.query({}, (tabs) => {
    tabs.forEach(tab => {
      chrome.tabs.sendMessage(tab.id, message).catch(() => {
        // 메시지 전송 실패는 무시 (Content Script가 없는 탭)
      });
    });
  });
  
  // Popup에도 전송 시도
  chrome.runtime.sendMessage(message).catch(() => {
    // Popup이 열려있지 않으면 무시
  });
}

// ============================================
// 컨텍스트 메뉴
// ============================================
chrome.runtime.onInstalled.addListener(() => {
  // 이미지 우클릭 메뉴
  chrome.contextMenus.create({
    id: 'madstamp-analyze-image',
    title: 'Madstamp: 이미지 분석',
    contexts: ['image']
  });
  
  // 선택 텍스트 메뉴
  chrome.contextMenus.create({
    id: 'madstamp-create-stamp',
    title: 'Madstamp: 도장 제작 요청',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  switch (info.menuItemId) {
    case 'madstamp-analyze-image':
      // 이미지 분석 요청
      chrome.tabs.sendMessage(tab.id, {
        action: 'analyzeImage',
        imageUrl: info.srcUrl
      });
      break;
    
    case 'madstamp-create-stamp':
      // 선택 텍스트로 도장 제작 요청
      chrome.tabs.sendMessage(tab.id, {
        action: 'createStampRequest',
        text: info.selectionText
      });
      break;
  }
});

// ============================================
// 알람 (주기적 작업)
// ============================================
chrome.alarms.create('checkNewEmails', {
  periodInMinutes: 5
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'checkNewEmails') {
    const { gmailMonitoring } = await chrome.storage.local.get(['gmailMonitoring']);
    
    if (gmailMonitoring) {
      // Gmail 탭이 열려있으면 이메일 확인 요청
      const tabs = await chrome.tabs.query({ url: `${GMAIL_URL}/*` });
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, { action: 'checkNewEmails' }).catch(() => {});
      });
    }
  }
});

// ============================================
// 탭 이벤트
// ============================================
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete') {
    // Lovart AI 탭이 로드되면 상태 업데이트
    if (tab.url && tab.url.includes('lovart.ai')) {
      broadcastMessage({ action: 'lovartStatusChanged', connected: true });
    }
  }
});

chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
  // Lovart AI 탭이 닫히면 상태 업데이트
  chrome.tabs.query({ url: `${LOVART_URL}/*` }, (tabs) => {
    if (tabs.length === 0) {
      broadcastMessage({ action: 'lovartStatusChanged', connected: false });
    }
  });
});

console.log('Madstamp Background Service Worker 시작됨');
