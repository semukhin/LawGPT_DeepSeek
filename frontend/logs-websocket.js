/**
 * logs-websocket.js - Обработка логов через WebSocket
 * v1.0.0 - 2025-03-17
 */

// Объект для управления отображением логов
const logsManager = (function() {
    const logsContainer = document.getElementById('logs-container');
    const processingLogs = document.getElementById('processing-logs');
    
    // Состояние
    let ws = null;
    let reconnectAttempts = 0;
    let reconnectTimeout = null;
    const maxReconnectAttempts = 5;
    
    // Подключение к WebSocket
    function connect() {
        // Используем протокол в зависимости от текущего
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log(`Подключение к WebSocket: ${wsUrl}`);
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('WebSocket подключен');
            reconnectAttempts = 0;
            
            // Отправляем пинг каждые 30 секунд для поддержания соединения
            setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000);
        };
        
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                
                if (data.type === 'log') {
                    // Показываем панель логов, если она скрыта
                    if (processingLogs && processingLogs.classList.contains('hidden')) {
                        processingLogs.classList.remove('hidden');
                    }
                    
                    // Добавляем лог в контейнер
                    const logItem = document.createElement('p');
                    logItem.innerHTML = `${data.content}`;
                    
                    logsContainer.appendChild(logItem);
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                    
                    // Если лог содержит сообщение о завершении, начинаем таймер на скрытие
                    if (data.content.includes('Анализ завершен') || 
                        data.content.includes('Обработка завершена') ||
                        data.content.includes('Готово')) {
                        setTimeout(() => {
                            hideLogsPanel();
                        }, 2000);
                    }
                }
            } catch (error) {
                console.error('Ошибка обработки сообщения WebSocket:', error);
            }
        };
        
        ws.onclose = function() {
            console.log('WebSocket соединение закрыто');
            
            // Попробуем переподключиться с экспоненциальной задержкой
            if (reconnectAttempts < maxReconnectAttempts) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                reconnectAttempts++;
                
                console.log(`Попытка переподключения через ${delay}мс (${reconnectAttempts}/${maxReconnectAttempts})`);
                
                reconnectTimeout = setTimeout(() => {
                    connect();
                }, delay);
            }
        };
        
        ws.onerror = function(error) {
            console.error('Ошибка WebSocket:', error);
        };
    }
    
    // Показать панель логов
    function showLogsPanel() {
        if (processingLogs) {
            // Очищаем предыдущие логи
            if (logsContainer) {
                logsContainer.innerHTML = '';
            }
            processingLogs.classList.remove('hidden');
        }
    }
    
    // Скрыть панель логов
    function hideLogsPanel() {
        if (processingLogs) {
            processingLogs.classList.add('hidden');
            
            // Очищаем логи после скрытия
            setTimeout(() => {
                if (logsContainer) {
                    logsContainer.innerHTML = '';
                }
            }, 500);
        }
    }
    
    // Инициализация системы логирования
    function init() {
        // Запускаем соединение
        connect();
        
        // Очищаем таймер при закрытии страницы
        window.addEventListener('beforeunload', () => {
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
            }
            if (ws) {
                ws.close();
            }
        });
        
        // Находим форму чата для добавления обработчика
        const chatForm = document.getElementById('chat-form');
        const sendBtn = document.getElementById('send-btn');
        
        // Если есть кнопка отправки, но нет формы - используем кнопку
        if (sendBtn && !chatForm) {
            sendBtn.addEventListener('click', handleMessageSending);
        }
        
        // Проверяем, является ли форма нашим случаем отправки сообщения
        if (chatForm) {
            chatForm.addEventListener('submit', handleMessageSending);
        }
        
        console.log('Система логирования через WebSocket инициализирована');
    }
    
    // Обработчик отправки сообщения
    function handleMessageSending(e) {
        // Предотвращаем действие формы, только если это событие submit
        if (e.type === 'submit') {
            e.preventDefault();
        }
        
        // Показываем логи при отправке сообщения
        showLogsPanel();
        
        // Продолжаем обычную обработку (не блокируем стандартный код приложения)
        // Отправка сообщения должна быть реализована в основном коде приложения
    }
    
    // Публичный API
    return {
        init: init,
        showLogs: showLogsPanel,
        hideLogs: hideLogsPanel
    };
})();

// Инициализация менеджера логов при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, что элементы логов существуют
    if (document.getElementById('processing-logs') && document.getElementById('logs-container')) {
        // Инициализируем систему логирования
        logsManager.init();
        console.log('Менеджер логов готов к работе');
    } else {
        console.error('Не найдены элементы для системы логирования!');
    }
});

// Модификация функции отправки сообщений
// Добавляем обработчик для привязки к существующей функции sendMessage (если она есть)
if (typeof window.sendMessage === 'function') {
    const originalSendMessage = window.sendMessage;
    window.sendMessage = function() {
        // Показываем логи перед отправкой
        if (logsManager && typeof logsManager.showLogs === 'function') {
            logsManager.showLogs();
        }
        
        // Вызываем оригинальную функцию
        return originalSendMessage.apply(this, arguments);
    };
    console.log('Функция sendMessage перехвачена для показа логов');
}