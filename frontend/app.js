/**
 * LawGPT - Основной файл приложения
 * Оптимизированная версия с улучшенной обработкой ошибок и мобильной адаптивностью
 * @version 2.0.1
 * @date 2025-03-27
 */

console.log('LawGPT Frontend загружен');

// Конфигурация приложения
const config = {
    apiUrl: '/api',
    apiTimeout: 60000,
    storageTokenKey: 'lawgpt_token',
    storageThreadKey: 'lawgpt_thread_id',
    storageTempTokenKey: 'lawgpt_temp_token',
    offlineModeKey: 'lawgpt_offline_mode',
    markdownEnabled: true,
    autoscrollEnabled: true,
    maxFileSize: 50 * 1024 * 1024,
    mobileBreakpoint: 768, // Точка перехода для мобильных устройств
    reconnectInterval: 5000, // Интервал попыток восстановления соединения в мс
    maxReconnectAttempts: 3, // Максимальное количество попыток восстановления
    defaultLanguage: 'ru-RU' // Язык по умолчанию для голосового ввода
};

// ============================================================
// Сетевое состояние и обработка ошибок
// ============================================================

/**
 * Состояние сети и обработка ошибок
 */
const networkState = {
    online: window.navigator.onLine,
    reconnectAttempts: 0,
    reconnectTimer: null,

    /**
     * Инициализирует отслеживание состояния сети
     */
    init() {
        window.addEventListener('online', () => this.setOnlineStatus(true));
        window.addEventListener('offline', () => this.setOnlineStatus(false));
        
        // Начальная проверка состояния сети
        this.checkConnection();
    },

    /**
     * Устанавливает статус онлайн/оффлайн
     * @param {boolean} isOnline - Статус подключения
     */
    setOnlineStatus(isOnline) {
        this.online = isOnline;
        
        // Обновляем UI для отображения статуса сети
        this.updateNetworkStatusUI();
        
        if (isOnline) {
            // Если мы вернулись в онлайн, синхронизируем данные
            this.handleReconnection();
        } else {
            // Если перешли в оффлайн, активируем оффлайн-режим
            this.activateOfflineMode();
        }
    },

    /**
     * Проверяет соединение с сервером
     * @returns {Promise<boolean>} - Промис с результатом проверки
     */
    async checkConnection() {
        try {
            const response = await fetch(`${config.apiUrl}/ping`, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache'
                }
            });
            
            const isOnline = response.ok;
            this.setOnlineStatus(isOnline);
            return isOnline;
        } catch (error) {
            console.warn('Не удалось проверить соединение:', error);
            this.setOnlineStatus(false);
            return false;
        }
    },

    /**
     * Обрабатывает восстановление соединения
     */
    handleReconnection() {
        // Сбрасываем счетчик попыток
        this.reconnectAttempts = 0;
        
        // Очищаем таймер, если он был установлен
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        // Показываем уведомление о восстановлении соединения
        this.showNetworkStatus('Соединение восстановлено', 'online');
        
        // Скрываем статус через 3 секунды
        setTimeout(() => {
            this.hideNetworkStatus();
        }, 3000);
        
        // Проверяем наличие оффлайн-данных и синхронизируем их
        this.syncOfflineData();
    },

    /**
     * Пытается восстановить соединение
     */
    attemptReconnection() {
        if (this.reconnectAttempts >= config.maxReconnectAttempts) {
            this.showNetworkStatus('Не удалось восстановить соединение', 'offline');
            return;
        }
        
        this.reconnectAttempts++;
        this.showNetworkStatus('Попытка восстановления соединения...', 'reconnecting');
        
        this.checkConnection().then(isOnline => {
            if (!isOnline) {
                // Планируем следующую попытку
                this.reconnectTimer = setTimeout(() => {
                    this.attemptReconnection();
                }, config.reconnectInterval);
            }
        });
    },

    /**
     * Активирует режим оффлайн
     */
    activateOfflineMode() {
        // Сохраняем флаг оффлайн-режима
        localStorage.setItem(config.offlineModeKey, 'true');
        
        // Показываем уведомление о переходе в оффлайн
        this.showNetworkStatus('Отсутствует подключение к интернету', 'offline');
        
        // Запускаем попытки восстановления соединения
        this.attemptReconnection();
    },

    /**
     * Синхронизирует данные, сохраненные в оффлайн-режиме
     */
    syncOfflineData() {
        // Проверяем наличие оффлайн-режима
        const wasOffline = localStorage.getItem(config.offlineModeKey) === 'true';
        
        if (wasOffline) {
            // Удаляем флаг оффлайн-режима
            localStorage.removeItem(config.offlineModeKey);
            
            // Загружаем и синхронизируем оффлайн-данные
            // Например, можно загрузить сообщения из local/indexedDB
            console.log('Синхронизация оффлайн-данных');
            
            // В текущей реализации мы просто перезагружаем данные чата
            const threadId = localStorage.getItem(config.storageThreadKey);
            if (threadId) {
                loadChatMessages(threadId).catch(error => {
                    console.error('Ошибка при загрузке сообщений после восстановления соединения:', error);
                });
            }
        }
    },

    /**
     * Обновляет UI для отображения статуса сети
     */
    updateNetworkStatusUI() {
        // Обновляем классы на body
        document.body.classList.toggle('offline-mode', !this.online);
        
        // Обновляем доступность кнопок отправки
        const sendButtons = document.querySelectorAll('.send-btn');
        sendButtons.forEach(btn => {
            btn.disabled = !this.online || btn.dataset.emptyInput === 'true';
        });
    },

    /**
     * Показывает статус сети
     * @param {string} message - Сообщение для отображения
     * @param {string} status - Статус ('online', 'offline', 'reconnecting')
     */
    showNetworkStatus(message, status) {
        let statusEl = document.getElementById('network-status');
        
        if (!statusEl) {
            statusEl = document.createElement('div');
            statusEl.id = 'network-status';
            statusEl.className = 'network-status';
            document.body.appendChild(statusEl);
        }
        
        statusEl.textContent = message;
        statusEl.className = `network-status ${status} visible`;
    },

    /**
     * Скрывает статус сети
     */
    hideNetworkStatus() {
        const statusEl = document.getElementById('network-status');
        if (statusEl) {
            statusEl.classList.remove('visible');
        }
    }
};

// ============================================================
// Мобильные утилиты
// ============================================================

/**
 * Проверка на мобильное устройство
 * @returns {boolean} 
 */
function isMobile() {
    return window.innerWidth <= config.mobileBreakpoint;
}

/**
 * Проверка производительности устройства
 * @returns {boolean}
 */
function isLowPowerDevice() {
    return (
        (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4) ||
        /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
        (navigator.deviceMemory && navigator.deviceMemory < 2)
    );
}

/**
 * Оптимизация для маломощных устройств
 */
function optimizeForLowPowerDevices() {
    // Отключаем тяжелые анимации
    document.body.classList.add('reduce-motion');
    
    // Уменьшаем качество изображений
    document.body.classList.add('data-saver');
    
    // Ограничиваем количество загружаемых сообщений за раз
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        // Упрощаем обработку прокрутки с помощью throttle
        let lastScrollTime = 0;
        const originalScrollListener = messagesContainer.onscroll;
        messagesContainer.onscroll = (e) => {
            const now = Date.now();
            if (now - lastScrollTime > 200) {
                lastScrollTime = now;
                if (originalScrollListener) {
                    originalScrollListener(e);
                }
            }
        };
    }
    
    console.log('Оптимизация для маломощных устройств применена');
}

/**
 * Инициализация мобильного меню
 */
function initMobileMenu() {
    // Получаем необходимые элементы
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const header = document.querySelector('.header');
    
    // Проверяем наличие sidebar и overlay
    if (!sidebar || !overlay) {
        console.error('Не найдены sidebar или overlay для мобильного меню');
        return;
    }
    
    // Проверяем наличие кнопки меню
    let menuToggle = document.getElementById('menu-toggle');
    
    // Если кнопки нет, создаем её
    if (!menuToggle) {
        console.log('Создаем новую кнопку меню');
        menuToggle = document.createElement('button');
        menuToggle.id = 'menu-toggle';
        menuToggle.className = 'menu-toggle';
        menuToggle.setAttribute('aria-label', 'Открыть меню');
        menuToggle.innerHTML = `
            <span class="burger-line"></span>
            <span class="burger-line"></span>
            <span class="burger-line"></span>
        `;
        
        // Вставляем кнопку в начало header
        header.insertBefore(menuToggle, header.firstChild);
    }
    
    // Удаляем существующие обработчики событий, чтобы избежать дублирования
    const newMenuToggle = menuToggle.cloneNode(true);
    if (menuToggle.parentNode) {
        menuToggle.parentNode.replaceChild(newMenuToggle, menuToggle);
    }
    menuToggle = newMenuToggle;
    
    // Добавляем обработчик для кнопки меню
    menuToggle.addEventListener('click', function() {
        console.log('Клик по кнопке меню обработан');
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
        menuToggle.classList.toggle('active');
        
        // Если меню активно, изменяем атрибут aria-label
        if (sidebar.classList.contains('active')) {
            menuToggle.setAttribute('aria-label', 'Закрыть меню');
            document.body.style.overflow = 'hidden';
        } else {
            menuToggle.setAttribute('aria-label', 'Открыть меню');
            document.body.style.overflow = '';
        }
    });
    
    // Закрытие меню при клике на оверлей
    overlay.addEventListener('click', function() {
        console.log('Клик по оверлею');
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        menuToggle.classList.remove('active');
        menuToggle.setAttribute('aria-label', 'Открыть меню');
        document.body.style.overflow = '';
    });
    
    // Закрытие меню при выборе чата на мобильных устройствах
    document.addEventListener('click', function(e) {
        const chatItem = e.target.closest('.chat-item');
        if (chatItem && window.innerWidth <= 768) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
            menuToggle.classList.remove('active');
            menuToggle.setAttribute('aria-label', 'Открыть меню');
            document.body.style.overflow = '';
        }
    });
    
    console.log('Мобильное меню инициализировано успешно');
}

/**
 * Инициализация мобильных улучшений
 * Централизованный метод для настройки мобильного интерфейса
 */
/**
 * Инициализация мобильных улучшений
 * Централизованный метод для настройки мобильного интерфейса
 */
function initMobileEnhancements() {
    if (isMobile()) {
        console.log('🚀 Инициализация мобильных улучшений');
        
        // Функционал из initSwipeGestures
        const chatItems = document.querySelectorAll('.chat-item:not(.empty):not(.new-chat-item)');
        
        chatItems.forEach(item => {
            // Добавляем класс для свайпа
            item.classList.add('swipeable');
            
            // Создаем элементы действий
            const actionsEl = document.createElement('div');
            actionsEl.className = 'swipe-actions';
            
            // Действие удаления
            const deleteAction = document.createElement('div');
            deleteAction.className = 'swipe-action delete';
            deleteAction.innerHTML = '<i class="fas fa-trash"></i>';
            deleteAction.addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm('Удалить этот чат?')) {
                    // Код удаления чата
                    item.style.height = '0';
                    item.style.opacity = '0';
                    item.style.margin = '0';
                    item.style.padding = '0';
                    
                    setTimeout(() => {
                        item.remove();
                    }, 300);
                }
            });
            
            // Добавляем действия
            actionsEl.appendChild(deleteAction);
            item.appendChild(actionsEl);
            
            // Код обработки свайпа
            let startX, moveX, isDragging = false;
            
            item.addEventListener('touchstart', (e) => {
                startX = e.touches[0].clientX;
                isDragging = false;
                
                // Сбрасываем трансформацию других элементов
                chatItems.forEach(otherItem => {
                    if (otherItem !== item) {
                        otherItem.style.transform = 'translateX(0)';
                        const otherActions = otherItem.querySelector('.swipe-actions');
                        if (otherActions) {
                            otherActions.style.opacity = '0';
                        }
                    }
                });
            });
            
            item.addEventListener('touchmove', (e) => {
                if (!startX) return;
                
                moveX = e.touches[0].clientX;
                const diff = moveX - startX;
                
                // Если свайп влево
                if (diff < 0) {
                    isDragging = true;
                    item.style.transform = `translateX(${diff}px)`;
                    
                    // Показываем действия с прозрачностью
                    const normalizedOpacity = Math.min(Math.abs(diff) / 100, 1);
                    actionsEl.style.opacity = normalizedOpacity;
                }
            });
            
            item.addEventListener('touchend', () => {
                if (!isDragging) return;
                
                const diff = moveX - startX;
                
                // Если свайп достаточно большой
                if (diff < -80) {
                    // Открываем действия
                    item.style.transform = 'translateX(-80px)';
                    actionsEl.style.opacity = '1';
                } else {
                    // Возвращаем элемент в исходное положение
                    item.style.transform = 'translateX(0)';
                    actionsEl.style.opacity = '0';
                }
                
                startX = null;
                moveX = null;
                isDragging = false;
            });
        });
        
        // Функционал из initPullToRefresh
        const chatList = document.getElementById('chat-list');
        if (chatList) {
            // Создаем элемент индикатора
            const pullIndicator = document.createElement('div');
            pullIndicator.className = 'pull-indicator';
            pullIndicator.innerHTML = `
                <div class="pull-icon">
                    <i class="fas fa-arrow-down"></i>
                </div>
                <div class="pull-text">Потяните вниз для обновления</div>
            `;
            
            chatList.parentNode.insertBefore(pullIndicator, chatList);
            
            // Переменные для отслеживания жеста
            let startY, moveY;
            let isPulling = false;
            let isRefreshing = false;
            
            // Обработчик начала касания
            chatList.addEventListener('touchstart', (e) => {
                // Проверяем, находится ли скролл в начале
                if (chatList.scrollTop === 0) {
                    startY = e.touches[0].clientY;
                    isPulling = true;
                }
            });
            
            // Обработчик движения пальца
            chatList.addEventListener('touchmove', (e) => {
                if (!isPulling || isRefreshing) return;
                
                moveY = e.touches[0].clientY;
                const diff = moveY - startY;
                
                if (diff > 0) {
                    // Показываем индикатор с анимацией
                    pullIndicator.style.transform = `translateY(${Math.min(diff / 2, 60)}px)`;
                    pullIndicator.querySelector('.pull-icon').style.transform = `rotate(${diff / 3}deg)`;
                    
                    // Предотвращаем прокрутку, если тянем вниз
                    e.preventDefault();
                }
            });
            
            // Обработчик окончания касания
            chatList.addEventListener('touchend', () => {
                if (!isPulling || isRefreshing) return;
                
                const diff = moveY - startY;
                
                if (diff > 60) {
                    // Достаточно большое смещение - запускаем обновление
                    isRefreshing = true;
                    pullIndicator.style.transform = 'translateY(60px)';
                    pullIndicator.querySelector('.pull-text').textContent = 'Обновление...';
                    
                    // Обновляем список чатов
                    loadChatThreads().finally(() => {
                        // Возвращаем индикатор на место
                        setTimeout(() => {
                            pullIndicator.style.transform = 'translateY(0)';
                            pullIndicator.querySelector('.pull-text').textContent = 'Потяните вниз для обновления';
                            isRefreshing = false;
                        }, 1000);
                    });
                } else {
                    // Возвращаем индикатор на место
                    pullIndicator.style.transform = 'translateY(0)';
                }
                
                isPulling = false;
            });
        }
        
        // Функционал из initKeyboardOptimization
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            // Запрещаем масштабирование при фокусе на мобильных устройствах
            const viewportMeta = document.querySelector('meta[name="viewport"]');
            if (viewportMeta) {
                viewportMeta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0';
            } else {
                // Создаем метатег, если его нет
                const meta = document.createElement('meta');
                meta.name = 'viewport';
                meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0';
                document.head.appendChild(meta);
            }
            
            // Обработчик фокуса для автоскролла на мобильных
            messageInput.addEventListener('focus', () => {
                // Скроллим к полю ввода с задержкой
                setTimeout(() => {
                    window.scrollTo(0, document.body.scrollHeight);
                    scrollToBottom();
                }, 300);
            });
            
            // Фикс для iOS: предотвращаем зум на двойном тапе
            document.addEventListener('gesturestart', (e) => {
                e.preventDefault();
            });
        }
        
        // Функционал из initLazyMessageLoading
        const messagesContainer = document.getElementById('messages-container');
        if (messagesContainer) {
            // Состояние загрузки
            let isLoading = false;
            let hasMoreMessages = true;
            let loadedMessageCount = 0;
            let threadId = localStorage.getItem(config.storageThreadKey);
            
            // При прокрутке вверх загружаем больше сообщений
            messagesContainer.addEventListener('scroll', () => {
                // Если уже загружаем или нет больше сообщений, пропускаем
                if (isLoading || !hasMoreMessages) return;
                
                // Если прокрутили достаточно вверх, загружаем больше сообщений
                if (messagesContainer.scrollTop < 100) {
                    loadMoreMessages();
                }
            });
            
            // Функция загрузки дополнительных сообщений
            async function loadMoreMessages() {
                isLoading = true;
                
                // Показываем индикатор загрузки
                const loadingIndicator = document.createElement('div');
                loadingIndicator.className = 'message-loading';
                loadingIndicator.innerHTML = '<div class="message-loading-spinner"></div>';
                messagesContainer.prepend(loadingIndicator);
                
                // Запоминаем текущую высоту прокрутки
                const scrollHeight = messagesContainer.scrollHeight;
                
                try {
                    // Загружаем еще сообщения с пагинацией
                    const offset = loadedMessageCount;
                    const limit = 20; // Количество сообщений на страницу
                    
                    const response = await apiRequest(`/messages/${threadId}?offset=${offset}&limit=${limit}`, 'GET');
                    
                    if (response.messages && Array.isArray(response.messages)) {
                        // Если нет больше сообщений, отмечаем это
                        if (response.messages.length === 0) {
                            hasMoreMessages = false;
                        } else {
                            // Обрабатываем полученные сообщения
                            response.messages.forEach(message => {
                                // Добавляем сообщения в начало, а не в конец
                                const timestamp = message.created_at ? new Date(message.created_at) : new Date();
                                
                                const messageElement = document.createElement('div');
                                messageElement.className = `message message-${message.role}`;
                                
                                const contentElement = document.createElement('div');
                                contentElement.className = 'message-content';
                                
                                if (message.role === 'assistant' && config.markdownEnabled && window.markdown) {
                                    contentElement.innerHTML = window.markdown.parse(message.content);
                                } else {
                                    contentElement.textContent = message.content;
                                }
                                
                                const timeElement = document.createElement('div');
                                timeElement.className = 'message-time';
                                
                                const dateStr = timestamp.toLocaleDateString('ru-RU');
                                const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
                                
                                const dateSpan = document.createElement('span');
                                dateSpan.className = 'message-date';
                                dateSpan.textContent = dateStr;
                                
                                timeElement.appendChild(dateSpan);
                                timeElement.appendChild(document.createTextNode(timeStr));
                                
                                messageElement.dataset.timestamp = timestamp.getTime();
                                
                                messageElement.appendChild(contentElement);
                                messageElement.appendChild(timeElement);
                                
                                // Вставляем после индикатора загрузки
                                messagesContainer.insertBefore(messageElement, loadingIndicator.nextSibling);
                            });
                            
                            // Увеличиваем счетчик загруженных сообщений
                            loadedMessageCount += response.messages.length;
                        }
                    }
                } catch (error) {
                    console.error('Ошибка при загрузке дополнительных сообщений:', error);
                    showNotification('Не удалось загрузить больше сообщений', 'error');
                } finally {
                    // Удаляем индикатор загрузки
                    loadingIndicator.remove();
                    
                    // Восстанавливаем позицию прокрутки, чтобы не было скачка
                    messagesContainer.scrollTop = messagesContainer.scrollHeight - scrollHeight;
                    
                    isLoading = false;
                }
            }
        }
        
        // Добавляем класс на body для мобильных устройств
        document.body.classList.add('mobile-device');
        
        // Оптимизация для маломощных устройств
        if (isLowPowerDevice()) {
            console.log('⚡ Оптимизация для маломощных устройств');
            optimizeForLowPowerDevices();
        }
        
        // Помечаем инициализацию
        window.mobileEnhancementsInitialized = true;
    }
}

/**
 * Показывает основное приложение
 */
function showApp() {
    toggleAppVisibility(true);
}

/**
 * Показывает экраны аутентификации
 */
function showAuth() {
    toggleAppVisibility(false);
    showAuthScreen('login-screen');
}

/**
 * Показывает конкретный экран аутентификации
 * @param {string} screenId - ID экрана для показа
 */
function showAuthScreen(screenId) {
    const screens = [
        'login-screen',
        'register-screen',
        'verify-screen',
        'forgot-password-screen',
        'reset-password-screen'
    ];
    
    screens.forEach(id => {
        const screen = document.getElementById(id);
        if (screen) {
            if (id === screenId) {
                screen.style.display = 'block';
            } else {
                screen.style.display = 'none';
            }
        }
    });
}

/**
 * Показывает уведомление
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип уведомления ('success', 'error', 'info')
 */
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    if (!notification) {
        console.error('Элемент notification не найден');
        return;
    }
    
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    notification.setAttribute('role', 'alert');
    
    // Добавляем обработчик для закрытия уведомления
    notification.onclick = () => {
        notification.style.display = 'none';
    };
    
    // Автоматически скрываем уведомление через 3 секунды
    setTimeout(() => {
        if (notification.style.display === 'block') {
            notification.style.display = 'none';
        }
    }, 3000);
}

/**
 * Показывает индикатор загрузки
 */
function showLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

/**
 * Скрывает индикатор загрузки
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

// ============================================================
// Функции для работы с API
// ============================================================

/**
 * Отправляет запрос к API
 * @param {string} endpoint - Путь API без базового URL
 * @param {string} method - HTTP метод (GET, POST, PUT, DELETE)
 * @param {Object} data - Данные для отправки (для POST, PUT)
 * @param {string} token - JWT токен для авторизации (опционально)
 * @returns {Promise<Object>} - Promise с ответом от API
 */
async function apiRequest(endpoint, method, data = null, token = null) {
    // Если мы в оффлайн-режиме, обрабатываем это
    if (!networkState.online) {
        console.warn('Попытка отправить запрос в оффлайн-режиме:', endpoint);
        
        // Проверяем, можно ли обслужить запрос из кэша
        if (method === 'GET') {
            // TODO: Реализовать кэширование запросов
            
            // В данной реализации просто возвращаем ошибку
            throw new Error('Нет подключения к интернету');
        } else {
            // Для POST/PUT запросов можно сохранять их для последующей синхронизации
            // TODO: Реализовать очередь запросов
            
            throw new Error('Нет подключения к интернету');
        }
    }
    
    // Если токен не передан, пытаемся получить его из localStorage
    if (!token) {
        token = localStorage.getItem(config.storageTokenKey);
    }
    
    // Формируем заголовки запроса
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // Добавляем заголовок авторизации, если есть токен
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Опции для fetch
    const options = {
        method: method,
        headers: headers
    };
    
    // Добавляем тело запроса для методов, которые его поддерживают
    if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const controller = new AbortController();
        options.signal = controller.signal;
        
        // Устанавливаем таймаут для запроса
        const timeoutId = setTimeout(() => controller.abort(), config.apiTimeout);
        
        const response = await fetch(`${config.apiUrl}${endpoint}`, options);
        clearTimeout(timeoutId);
        
        // Обрабатываем ошибки HTTP
        if (!response.ok) {
            let errorText = `HTTP ошибка ${response.status}`;
            
            // Пытаемся получить детали ошибки из тела ответа
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorText = errorData.detail;
                }
            } catch (e) {
                // Игнорируем ошибки при разборе JSON
            }
            
            // Проверяем на ошибку авторизации
            if (response.status === 401) {
                // Токен недействителен или истек срок его действия
                localStorage.removeItem(config.storageTokenKey);
                showAuth();
                
                throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
            }
            
            throw new Error(errorText);
        }
        
        // Парсим ответ как JSON
        const responseData = await response.json();
        return responseData;
    } catch (error) {
        // Проверяем тип ошибки
        if (error.name === 'AbortError') {
            // Запрос был прерван по таймауту
            throw new Error('Превышено время ожидания запроса');
        } else if (error.message === 'Failed to fetch' || error.message.includes('NetworkError')) {
            // Сетевая ошибка
            networkState.setOnlineStatus(false);
            throw new Error('Ошибка сети. Проверьте подключение к интернету.');
        }
        
        console.error(`Ошибка API запроса к ${endpoint}:`, error);
        throw error;
    }
}

/**
 * Отправляет запрос с FormData (для загрузки файлов)
 * @param {string} endpoint - Путь API без базового URL
 * @param {FormData} formData - FormData для отправки
 * @returns {Promise<Object>} - Promise с ответом от API
 */
async function apiRequestFormData(endpoint, formData) {
    // Если мы в оффлайн-режиме, обрабатываем это
    if (!networkState.online) {
        console.warn('Попытка отправить запрос FormData в оффлайн-режиме:', endpoint);
        throw new Error('Нет подключения к интернету');
    }
    
    const token = localStorage.getItem(config.storageTokenKey);
    
    // Формируем заголовки запроса (без Content-Type, он будет установлен автоматически для FormData)
    const headers = {};
    
    // Добавляем заголовок авторизации, если есть токен
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const controller = new AbortController();
        
        // Устанавливаем таймаут для запроса
        const timeoutId = setTimeout(() => controller.abort(), config.apiTimeout);
        
        const response = await fetch(`${config.apiUrl}${endpoint}`, {
            method: 'POST',
            headers: headers,
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // Обрабатываем ошибки HTTP
        if (!response.ok) {
            let errorText = `HTTP ошибка ${response.status}`;
            
            // Пытаемся получить детали ошибки из тела ответа
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorText = errorData.detail;
                }
            } catch (e) {
                // Игнорируем ошибки при разборе JSON
            }
            
            // Проверяем на ошибку авторизации
            if (response.status === 401) {
                // Токен недействителен или истек срок его действия
                localStorage.removeItem(config.storageTokenKey);
                showAuth();
                
                throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
            }
            
            throw new Error(errorText);
        }
        
        // Парсим ответ как JSON
        const data = await response.json();
        return data;
    } catch (error) {
        // Проверяем тип ошибки
        if (error.name === 'AbortError') {
            // Запрос был прерван по таймауту
            throw new Error('Превышено время ожидания запроса');
        } else if (error.message === 'Failed to fetch' || error.message.includes('NetworkError')) {
            // Сетевая ошибка
            networkState.setOnlineStatus(false);
            throw new Error('Ошибка сети. Проверьте подключение к интернету.');
        }
        
        console.error(`Ошибка API запроса FormData к ${endpoint}:`, error);
        throw error;
    }
}

// ============================================================
// Функции аутентификации
// ============================================================

/**
 * Обработчик входа пользователя
 * @param {Event} e - Событие отправки формы
 */
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    if (!email || !password) {
        showNotification('Пожалуйста, заполните все поля', 'error');
        return;
    }
    
    showLoading();
    
    try {
        // Соответствует схеме UserLogin в app/schemas.py
        const response = await apiRequest('/login', 'POST', {
            email: email,
            password: password
        });
        
        if (response.access_token) {
            localStorage.setItem(config.storageTokenKey, response.access_token);
            hideLoading();
            showApp();
            loadUserProfile();
            loadChatThreads();
            showNotification('Вход выполнен успешно', 'success');
        } else {
            hideLoading();
            showNotification('Ошибка при входе: неверный ответ сервера', 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification(`Ошибка при входе: ${error.message || 'проверьте данные'}`, 'error');
    }
}

/**
 * Обработчик регистрации пользователя
 * @param {Event} e - Событие отправки формы
 */
async function handleRegister(e) {
    e.preventDefault();
    
    const firstName = document.getElementById('register-firstname').value;
    const lastName = document.getElementById('register-lastname').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    
    if (!firstName || !lastName || !email || !password) {
        showNotification('Пожалуйста, заполните все поля', 'error');
        return;
    }
    
    // Простая валидация email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showNotification('Пожалуйста, введите корректный email', 'error');
        return;
    }
    
    // Простая валидация пароля
    if (password.length < 6) {
        showNotification('Пароль должен содержать не менее 6 символов', 'error');
        return;
    }
    
    showLoading();
    
    try {
        // Соответствует UserCreate схеме в app/schemas.py
        const response = await apiRequest('/register', 'POST', {
            email: email,
            password: password,
            first_name: firstName,
            last_name: lastName
        });
        
        if (response.temp_token || response.message) {
            // Сохраняем временный токен для верификации
            if (response.temp_token) {
                localStorage.setItem(config.storageTempTokenKey, response.temp_token);
            }
            // Сохраняем email для повторной отправки кода
            localStorage.setItem('temp_email', email);
            
            hideLoading();
            showAuthScreen('verify-screen');
            showNotification(response.message || 'Код подтверждения отправлен на ваш email', 'success');
        } else {
            hideLoading();
            showNotification('Ошибка при регистрации: неверный ответ сервера', 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification(`Ошибка при регистрации: ${error.message || 'проверьте данные'}`, 'error');
    }
}

/**
 * Обработчик верификации email
 * @param {Event} e - Событие отправки формы
 */
async function handleVerify(e) {
    e.preventDefault();
    
    const code = document.getElementById('verify-code').value;
    const token = localStorage.getItem(config.storageTempTokenKey);
    
    if (!code) {
        showNotification('Пожалуйста, введите код подтверждения', 'error');
        return;
    }
    
    // Проверяем формат кода (4 цифры)
    const codeRegex = /^\d{4}$/;
    if (!codeRegex.test(code)) {
        showNotification('Код должен состоять из 4 цифр', 'error');
        return;
    }
    
    if (!token) {
        showNotification('Ошибка: токен не найден', 'error');
        showAuthScreen('login-screen');
        return;
    }
    
    showLoading();
    
    try {
        // Соответствует схеме VerifyRequest в app/schemas.py
        const response = await apiRequest('/verify', 'POST', {
            code: parseInt(code)
        }, token);
        
        if (response.access_token) {
            localStorage.setItem(config.storageTokenKey, response.access_token);
            localStorage.removeItem(config.storageTempTokenKey);
            localStorage.removeItem('temp_email');
            hideLoading();
            showApp();
            loadUserProfile();
            loadChatThreads();
            showNotification('Аккаунт успешно подтвержден', 'success');
        } else {
            hideLoading();
            showNotification('Ошибка при верификации: неверный ответ сервера', 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification(`Ошибка при верификации: ${error.message || 'неверный код'}`, 'error');
    }
}

/**
 * Обработчик повторной отправки кода
 * @param {Event} e - Событие клика
 */
async function handleResendCode(e) {
    e.preventDefault();
    
    const email = localStorage.getItem('temp_email');
    
    if (!email) {
        showNotification('Ошибка: email не найден', 'error');
        showAuthScreen('login-screen');
        return;
    }
    
    showLoading();
    
    try {
        // Используем существующий метод register
        const response = await apiRequest('/register', 'POST', {
            email: email,
            password: "temporary", // Это будет заменено при верификации
            first_name: "Временное",
            last_name: "Имя"
        });
        
        if (response.temp_token) {
            localStorage.setItem(config.storageTempTokenKey, response.temp_token);
        }
        
        hideLoading();
        showNotification('Код подтверждения отправлен повторно', 'success');
    } catch (error) {
        hideLoading();
        showNotification(`Ошибка при повторной отправке кода: ${error.message}`, 'error');
    }
}

/**
 * Обработчик восстановления пароля
 * @param {Event} e - Событие отправки формы
 */
async function handleForgotPassword(e) {
    e.preventDefault();
    
    const email = document.getElementById('forgot-email').value;
    
    if (!email) {
        showNotification('Пожалуйста, введите email', 'error');
        return;
    }
    
    // Простая валидация email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showNotification('Пожалуйста, введите корректный email', 'error');
        return;
    }
    
    showLoading();
    
    try {
        // Соответствует схеме PasswordResetRequest в app/schemas.py
        const response = await apiRequest('/forgot-password', 'POST', {
            email: email
        });
        
        localStorage.setItem('reset_email', email);
        hideLoading();
        showAuthScreen('reset-password-screen');
        
        // Предзаполняем email в форме сброса пароля
        document.getElementById('reset-email').value = email;
        
        showNotification('Код для сброса пароля отправлен на ваш email', 'success');
    } catch (error) {
        hideLoading();
        showNotification(`Ошибка при восстановлении пароля: ${error.message}`, 'error');
    }
}

/**
 * Обработчик сброса пароля
 * @param {Event} e - Событие отправки формы
 */
async function handleResetPassword(e) {
    e.preventDefault();
    
    const email = document.getElementById('reset-email').value;
    const code = document.getElementById('reset-code').value;
    const newPassword = document.getElementById('reset-password').value;
    
    if (!email || !code || !newPassword) {
        showNotification('Пожалуйста, заполните все поля', 'error');
        return;
    }
    
    // Проверяем формат кода (4 цифры)
    const codeRegex = /^\d{4}$/;
    if (!codeRegex.test(code)) {
        showNotification('Код должен состоять из 4 цифр', 'error');
        return;
    }
    
    // Простая валидация пароля
    if (newPassword.length < 6) {
        showNotification('Пароль должен содержать не менее 6 символов', 'error');
        return;
    }
    
    showLoading();
    
    try {
        // Соответствует схеме PasswordResetConfirm в app/schemas.py
        const response = await apiRequest('/reset-password', 'POST', {
            email: email,
            code: parseInt(code),
            new_password: newPassword
        });
        
        hideLoading();
        showAuthScreen('login-screen');
        showNotification('Пароль успешно изменен. Теперь вы можете войти с новым паролем', 'success');
    } catch (error) {
        hideLoading();
        showNotification(`Ошибка при сбросе пароля: ${error.message}`, 'error');
    }
}

/**
 * Обработчик выхода пользователя
 */
async function handleLogout() {
    showLoading();
    
    try {
        await apiRequest('/logout', 'POST');
    } catch (error) {
        console.error('Ошибка при выходе:', error);
    } finally {
        // Очищаем все связанные хранилища
        localStorage.removeItem(config.storageTokenKey);
        localStorage.removeItem(config.storageThreadKey);
        localStorage.removeItem(config.offlineModeKey);
        
        // Очищаем кэш если есть
        try {
            if ('caches' in window) {
                const cacheKeys = await caches.keys();
                await Promise.all(
                    cacheKeys.map(key => caches.delete(key))
                );
            }
        } catch (error) {
            console.error('Ошибка при очистке кэша:', error);
        }
        
        hideLoading();
        showAuth();
        showNotification('Выход выполнен успешно', 'success');
    }
}

/**
 * Проверка валидности токена
 * @param {string} token - JWT токен для проверки
 * @returns {Promise<boolean>} - Promise с результатом проверки
 */
async function validateToken(token) {
    try {
        const response = await apiRequest('/profile', 'GET', null, token);
        return !!response; // Если получили успешный ответ, значит токен валиден
    } catch (error) {
        console.error('Ошибка при валидации токена:', error);
        return false;
    }
}

// Модальное окно профиля
function showProfileModal() {
    // Создаем модальное окно, если его еще нет
    let modal = document.getElementById('profile-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'profile-modal';
        modal.className = 'modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-labelledby', 'profile-title');
        
        document.body.appendChild(modal);
    }
    
    // Показываем индикатор загрузки внутри модального окна
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-modal" aria-label="Закрыть">&times;</span>
            <h2 id="profile-title">Профиль пользователя</h2>
            <div class="loading-spinner"></div>
        </div>
    `;
    
    // Показываем модальное окно
    modal.style.display = 'block';
    
    // Загружаем данные профиля
    apiRequest('/profile', 'GET')
        .then(data => {
            modal.innerHTML = `
                <div class="modal-content">
                    <span class="close-modal" aria-label="Закрыть">&times;</span>
                    <h2 id="profile-title">Профиль пользователя</h2>
                    <div class="profile-info">
                        <div class="profile-row">
                            <span class="profile-label">Имя:</span>
                            <span class="profile-value">${data.first_name} ${data.last_name}</span>
                        </div>
                        <div class="profile-row">
                            <span class="profile-label">Email:</span>
                            <span class="profile-value">${data.email}</span>
                        </div>
                    </div>
                </div>
            `;
            
            // Обработчик для закрытия
            const closeBtn = modal.querySelector('.close-modal');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    modal.style.display = 'none';
                });
            }
            
            // Закрытие по клику вне модального окна
            window.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
            
            // Закрытие по Escape
            window.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && modal.style.display === 'block') {
                    modal.style.display = 'none';
                }
            });
        })
        .catch(error => {
            modal.innerHTML = `
                <div class="modal-content">
                    <span class="close-modal" aria-label="Закрыть">&times;</span>
                    <h2 id="profile-title">Профиль пользователя</h2>
                    <div class="error-message">
                        Ошибка загрузки профиля: ${error.message}
                    </div>
                    <button class="form-button" id="retry-profile-btn">Повторить</button>
                </div>
            `;
            
            // Обработчик для закрытия
            modal.querySelector('.close-modal').addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            // Обработчик для повторной попытки
            const retryBtn = document.getElementById('retry-profile-btn');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    showProfileModal();
                });
            }
        });
}

// Модальное окно "О нас"
function showAboutModal() {
    // Создаем модальное окно, если его еще нет
    let modal = document.getElementById('about-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'about-modal';
        modal.className = 'modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-labelledby', 'about-title');
        
        document.body.appendChild(modal);
    }
    
    // Заполняем содержимое
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-modal" aria-label="Закрыть">&times;</span>
            <h2 id="about-title">О сервисе LawGPT</h2>
            <p>Приветствуем вас на странице сервиса юридического ассистента LawGPT!</p>
            <p>LawGPT — это интеллектуальный помощник, специализирующийся на российском законодательстве.</p>
            <p>Наш сервис помогает получать ответы на юридические вопросы, обращаясь к актуальной базе российского законодательства и судебной практики.</p>
            <p>В настоящее время сервис имеет RAG c почти полной базой российского законодательства.</p>
            <p>Пополняется база судебных решений и обзоров судебной практики.</p>
            <p>Приглашаем вас принять участие в развитии сервиса, предлагая свои идеи и предложения на почту <a href="mailto:info@lawgpt.ru">info@lawgpt.ru</a>.</p>
            <p>Спасибо за ваш интерес к LawGPT!</p>
            
            <div class="social-links">
                <h3>Наши социальные сети</h3>
                <div class="social-buttons">
                    <a href="https://vk.com/lawgptru" target="_blank" rel="noopener" class="social-link">
                        <i class="fab fa-vk"></i> ВКонтакте
                    </a>
                    <a href="https://t.me/Law_GPT" target="_blank" rel="noopener" class="social-link">
                        <i class="fab fa-telegram"></i> Telegram
                    </a>
                </div>
            </div>
        </div>
    `;
    
    // Обработчики для закрытия
    const closeBtn = modal.querySelector('.close-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    // Закрытие по клику вне модального окна
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Закрытие по Escape
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            modal.style.display = 'none';
        }
    });
    
    // Показываем модальное окно
    modal.style.display = 'block';
}

/**
 * Функция для добавления ссылки на Telegram в футер
 */
function ensureTelegramLink() {
    try {
        const footerSocialLinks = document.querySelector('.footer .social-links');
        
        if (!footerSocialLinks) {
            console.error('Не найден контейнер для социальных ссылок в футере');
            return;
        }
        
        const telegramLink = footerSocialLinks.querySelector('a[href*="t.me"], a[href*="telegram"]');
        
        if (!telegramLink) {
            const newTelegramLink = document.createElement('a');
            newTelegramLink.href = 'https://t.me/Law_GPT';
            newTelegramLink.target = '_blank';
            newTelegramLink.rel = 'noopener noreferrer';
            newTelegramLink.className = 'social-link';
            newTelegramLink.innerHTML = '<i class="fab fa-telegram"></i> Telegram';
            
            footerSocialLinks.appendChild(newTelegramLink);
            console.log('Ссылка на Telegram добавлена в футер');
        }
    } catch (error) {
        console.error('Ошибка при добавлении ссылки Telegram:', error);
    }
}

/**
 * Функция инициализации социальных ссылок для всех страниц
 */
function initSocialLinks() {
    // Проверяем футер на наличие ссылок
    ensureTelegramLink();
    
    // Функция для добавления или обновления иконок социальных сетей
    function updateSocialIcons() {
        // Проверяем, загружена ли библиотека Font Awesome
        if (typeof FontAwesome === 'undefined' && document.querySelector('[class*="fa-"]') === null) {
            // Если Font Awesome не загружен, добавляем его
            const fontAwesomeLink = document.createElement('link');
            fontAwesomeLink.rel = 'stylesheet';
            fontAwesomeLink.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
            document.head.appendChild(fontAwesomeLink);
            console.log('Font Awesome добавлен для иконок социальных сетей');
        }
        
        // Находим все социальные ссылки
        const socialLinks = document.querySelectorAll('.social-link');
        socialLinks.forEach(link => {
            // Проверяем, есть ли у ссылки иконка
            if (!link.querySelector('i[class*="fa-"]')) {
                // Если иконки нет, определяем, какую добавить
                if (link.href && link.href.includes('vk.com')) {
                    link.innerHTML = '<i class="fab fa-vk"></i> ' + link.textContent;
                } else if (link.href && (link.href.includes('t.me') || link.href.includes('telegram'))) {
                    link.innerHTML = '<i class="fab fa-telegram"></i> ' + link.textContent;
                } else if (link.href && link.href.includes('whatsapp')) {
                    link.innerHTML = '<i class="fab fa-whatsapp"></i> ' + link.textContent;
                }
            }
        });
    }
    
    // Вызываем функцию обновления иконок
    updateSocialIcons();
}

// ============================================================
// Инициализация и утилиты
// ============================================================

/**
 * Оптимизирует стили футера для более компактного отображения
 */
function fixFooterStyles() {
    const footer = document.querySelector('.footer');
    if (footer) {
        // Применяем улучшенные стили для футера
        footer.style.padding = '0.25rem';
        footer.style.paddingBottom = 'calc(0.25rem + env(safe-area-inset-bottom))';
        footer.style.minHeight = 'auto';
        footer.style.marginTop = 'auto';
        
        // Уменьшаем отступы между элементами
        const footerDivs = footer.querySelectorAll('div');
        footerDivs.forEach(div => {
            div.style.margin = '0.05rem 0';
        });
    }
}

/**
 * Инициализация приложения
 */
function initApp() {
    console.log('Инициализация приложения');
    
    // Инициализация сетевого состояния
    networkState.init();
    
    // Проверка авторизации
    const token = localStorage.getItem(config.storageTokenKey);
    
    if (token) {
        // Если есть токен, проверяем его валидность
        validateToken(token)
            .then(isValid => {
                if (isValid) {
                    showApp();
                    loadUserProfile();
                    loadChatThreads();
                    
                    // Добавим проверку на пустой список чатов и автоматически создадим первый чат
                    setTimeout(() => {
                        const chatList = document.getElementById('chat-list');
                        if (chatList && chatList.children.length === 0) {
                            console.log('Создаем первый чат для нового пользователя');
                            createNewChat();
                        } else if (chatList && chatList.querySelector('.chat-item.empty')) {
                            console.log('Создаем первый чат для нового пользователя (нет активных чатов)');
                            createNewChat();
                        }
                    }, 1000); // Небольшая задержка, чтобы chatList успел загрузиться
                } else {
                    showAuth();
                }
            })
            .catch(error => {
                console.error('Ошибка при проверке токена:', error);
                showAuth();
            });
    } else {
        // Если токена нет, показываем экран авторизации
        showAuth();
    }
    
    // Инициализация обработчиков событий
    initEventListeners();
    
    // Инициализация мобильного меню
    initMobileMenu();
    
    // Оптимизация стилей футера
    fixFooterStyles();
}

/**
 * Инициализация всех обработчиков событий
 */
function initEventListeners() {
    // Обработчики форм аутентификации
    initAuthForms();
    
    // Обработчики интерфейса чата
    initChatInterface();
    
    // Обработчик для кнопки выхода
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Обработчики для переключения между формами
    initAuthSwitchers();
}

/**
 * Инициализация обработчиков форм аутентификации
 */
function initAuthForms() {
    // Форма входа
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Форма регистрации
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // Форма верификации
    const verifyForm = document.getElementById('verify-form');
    if (verifyForm) {
        verifyForm.addEventListener('submit', handleVerify);
    }
    
    // Форма восстановления пароля
    const forgotPasswordForm = document.getElementById('forgot-password-form');
    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', handleForgotPassword);
    }
    
    // Форма сброса пароля
    const resetPasswordForm = document.getElementById('reset-password-form');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', handleResetPassword);
    }
    
    // Кнопка повторной отправки кода
    const resendCodeBtn = document.getElementById('resend-code');
    if (resendCodeBtn) {
        resendCodeBtn.addEventListener('click', handleResendCode);
    }
    
    // Кнопки возврата
    const backToLoginBtn = document.getElementById('back-to-login');
    if (backToLoginBtn) {
        backToLoginBtn.addEventListener('click', () => showAuthScreen('login-screen'));
    }
    
    const resetBackToLoginBtn = document.getElementById('reset-back-to-login');
    if (resetBackToLoginBtn) {
        resetBackToLoginBtn.addEventListener('click', () => showAuthScreen('login-screen'));
    }
    
    const verifyToLoginBtn = document.getElementById('verify-to-login');
    if (verifyToLoginBtn) {
        verifyToLoginBtn.addEventListener('click', () => showAuthScreen('login-screen'));
    }
}

/**
 * Инициализация переключателей между формами аутентификации
 */
function initAuthSwitchers() {
    // Переход к регистрации
    const toRegisterBtn = document.getElementById('to-register');
    if (toRegisterBtn) {
        toRegisterBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showAuthScreen('register-screen');
        });
    }
    
    // Переход к входу
    const toLoginBtn = document.getElementById('to-login');
    if (toLoginBtn) {
        toLoginBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showAuthScreen('login-screen');
        });
    }
    
    // Переход к восстановлению пароля
    const toForgotPasswordBtn = document.getElementById('to-forgot-password');
    if (toForgotPasswordBtn) {
        toForgotPasswordBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showAuthScreen('forgot-password-screen');
        });
    }
}

/**
 * Инициализация интерфейса чата
 */
function initChatInterface() {
    // Кнопка нового чата
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewChat);
    }
    
    // Логотип как ссылка на главную
    const logo = document.querySelector('.logo');
    if (logo) {
        logo.addEventListener('click', function(e) {
            e.preventDefault(); // Предотвращаем обычное действие ссылки
            
            // Код для перехода на главную
            const savedThreadId = localStorage.getItem(config.storageThreadKey);
            if (savedThreadId) {
                selectChatThread(savedThreadId);
            } else {
                createNewChat();
            }
        });
    }
    
    // Поле ввода сообщения
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('input', () => {
            // Автоматическое изменение высоты поля ввода
            messageInput.style.height = 'auto';
            messageInput.style.height = (messageInput.scrollHeight) + 'px';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
            
            // Активация/деактивация кнопки отправки
            const sendBtn = document.getElementById('send-btn');
            if (sendBtn) {
                const isEmpty = messageInput.value.trim() === '';
                sendBtn.disabled = isEmpty || !networkState.online;
                sendBtn.dataset.emptyInput = isEmpty ? 'true' : 'false';
            }
        });
        
        // Отправка сообщения по Enter
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (messageInput.value.trim() && networkState.online) {
                    const sendBtn = document.getElementById('send-btn');
                    if (sendBtn) {
                        sendBtn.click();
                    }
                }
            }
        });
    }
    
    // Отправка сообщения
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    // Загрузка файла
    const fileUpload = document.getElementById('file-upload');
    if (fileUpload) {
        fileUpload.addEventListener('change', handleFileUpload);
    }
    
    // Удаление файла
    const removeFileBtn = document.getElementById('remove-file-btn');
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', removeUploadedFile);
    }
    
    // Обработчики для модальных окон
    const navProfileBtn = document.getElementById('nav-profile');
    if (navProfileBtn) {
        navProfileBtn.addEventListener('click', showProfileModal);
    }
    
    const navAboutBtn = document.getElementById('nav-about');
    if (navAboutBtn) {
        navAboutBtn.addEventListener('click', showAboutModal);
    }

    // Добавляем кнопки голосового ввода
    addVoiceInputButtons();
}

/**
 * Возвращает текущее время в формате ЧЧ:ММ
 * @returns {string} - Строка с форматированным временем
 */
function getCurrentTime() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
}

// ============================================================
// Функции интерфейса чата
// ============================================================

/**
 * Создает новый чат
 */
async function createNewChat() {
    // Проверяем соединение
    if (!networkState.online) {
        showNotification('Нет подключения к интернету. Невозможно создать новый чат.', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await apiRequest('/create_thread', 'POST');
        
        if (response.thread_id) {
            const threadId = response.thread_id;
            localStorage.setItem(config.storageThreadKey, threadId);
            
            // Обновляем список чатов
            await loadChatThreads();
            
            // Открываем новый чат
            selectChatThread(threadId);
            
            // Очищаем контейнер с сообщениями
            const messagesContainer = document.getElementById('messages-container');
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
            }
            
            // Показываем приветственное сообщение от ассистента
            addAssistantMessage('Здравствуйте! Я юридический ассистент LawGPT. Чем я могу вам помочь?');
            
            showNotification('Новый чат создан', 'success');
        } else {
            showNotification('Ошибка при создании чата', 'error');
        }
    } catch (error) {
        showNotification(`Ошибка при создании чата: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Загружает список чатов пользователя
 */
async function loadChatThreads() {
    try {
        const response = await apiRequest('/chat/threads', 'GET');
        
        if (response.threads && Array.isArray(response.threads)) {
            renderChatThreads(response.threads);
            
            // Если есть сохраненный ID треда, выбираем его
            const savedThreadId = localStorage.getItem(config.storageThreadKey);
            if (savedThreadId) {
                selectChatThread(savedThreadId);
            } else if (response.threads.length > 0) {
                // Иначе выбираем первый чат из списка
                selectChatThread(response.threads[0].id);
            }
        }
    } catch (error) {
        console.error('Ошибка при загрузке списка чатов:', error);
        showNotification('Не удалось загрузить историю чатов', 'error');
        
        // Проверяем, не проблема ли с сетью
        if (error.message.includes('сети') || error.message.includes('подключен')) {
            networkState.setOnlineStatus(false);
        }
    }
}

/**
 * Отображает список чатов в боковой панели
 * @param {Array} threads - Массив объектов с данными чатов
 */
function renderChatThreads(threads) {
    const chatList = document.getElementById('chat-list');
    if (!chatList) {
        console.error('Элемент списка чатов не найден');
        return;
    }
    
    chatList.innerHTML = '';
    
    if (threads.length === 0) {
        const emptyItem = document.createElement('li');
        emptyItem.className = 'chat-item empty';
        emptyItem.textContent = 'У вас пока нет активных чатов.';
        chatList.appendChild(emptyItem);
        
        // Для мобильной версии сделаем кнопку нового чата более заметной
        if (isMobile()) {
            // Добавляем кнопку создания чата прямо в список
            const newChatItem = document.createElement('li');
            newChatItem.className = 'chat-item new-chat-item';
            newChatItem.innerHTML = '<i class="fas fa-plus"></i> Создать новый чат';
            newChatItem.addEventListener('click', createNewChat);
            chatList.appendChild(newChatItem);
            
            // Для мобильной версии также сделаем кнопку в шапке более заметной
            const menuToggle = document.getElementById('menu-toggle');
            if (menuToggle) {
                // Добавим анимацию, чтобы обратить внимание пользователя
                menuToggle.classList.add('pulse-animation');
                
                // Уберем анимацию через некоторое время
                setTimeout(() => {
                    menuToggle.classList.remove('pulse-animation');
                }, 5000);
            }
        }
        
        return;
    }
    
    // Сортируем чаты по дате создания (новые сверху)
    threads.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    threads.forEach(thread => {
        const chatItem = document.createElement('li');
        chatItem.className = 'chat-item';
        chatItem.dataset.threadId = thread.id;
        
        // Форматируем дату
        const date = new Date(thread.created_at);
        const formattedDate = `${date.toLocaleDateString('ru-RU')} ${date.toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'})}`;
        
        // Устанавливаем заголовок или используем стандартный текст
        const title = thread.first_message || 'Новый чат';
        
        // Добавляем контент чата
        chatItem.innerHTML = `
            <div class="chat-info">
                <div class="chat-title">${title}</div>
                <div class="chat-date">${formattedDate}</div>
            </div>
        `;
        
        // Обработчик клика
        chatItem.addEventListener('click', () => {
            selectChatThread(thread.id);
        });
        
        chatList.appendChild(chatItem);
    });
    
    // Инициализируем свайп-жесты после добавления элементов
    if (isMobile()) {
        initSwipeGestures();
    }
}

/**
 * Выбирает чат из списка и загружает его сообщения
 * @param {string} threadId - ID треда чата
 */
async function selectChatThread(threadId) {
    // Сохраняем ID треда в localStorage
    localStorage.setItem(config.storageThreadKey, threadId);
    
    // Обновляем UI - подсвечиваем выбранный чат
    const chatItems = document.querySelectorAll('.chat-item');
    chatItems.forEach(item => {
        if (item.dataset.threadId === threadId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Обновляем заголовок чата
    const currentChatId = document.getElementById('current-chat-id');
    if (currentChatId) {
        currentChatId.textContent = threadId;
    }
    
    // Очищаем контейнер сообщений и показываем индикатор загрузки
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="message-loading">
                <div class="message-loading-spinner"></div>
            </div>
        `;
    }
    
    // Загружаем сообщения данного чата
    try {
        await loadChatMessages(threadId);
    } catch (error) {
        // Если ошибка при загрузке сообщений, показываем сообщение об ошибке
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="empty-state-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <h3>Ошибка загрузки сообщений</h3>
                    <p>${error.message}</p>
                    <button id="retry-load-messages" class="form-button">Повторить</button>
                </div>
            `;
            
            // Добавляем обработчик для повторной попытки
            const retryBtn = document.getElementById('retry-load-messages');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    selectChatThread(threadId);
                });
            }
        }
    }
}

/**
 * Загружает сообщения выбранного чата
 * @param {string} threadId - ID треда чата
 * @returns {Promise<void>}
 */
async function loadChatMessages(threadId) {
    try {
        console.log(`Загрузка сообщений для треда ${threadId}`);
        
        // Если сеть недоступна, пытаемся загрузить из кэша
        if (!networkState.online) {
            const cachedMessages = await loadCachedMessages(threadId);
            if (cachedMessages && cachedMessages.length > 0) {
                renderChatMessages(cachedMessages);
                showNotification('Загружены сообщения из локального хранилища (оффлайн режим)', 'info');
                return;
            }
            throw new Error('Нет подключения к интернету');
        }
        
        const response = await apiRequest(`/messages/${threadId}`, 'GET');
        
        if (response.messages && Array.isArray(response.messages)) {
            // Проверяем наличие временных меток и форматируем их, если необходимо
            const formattedMessages = response.messages.map(message => {
                // Если у сообщения нет временной метки, добавляем текущую дату
                if (!message.created_at) {
                    console.warn(`Сообщение без временной метки: ${message.id || 'без ID'}`);
                    message.created_at = new Date().toISOString();
                }
                
                // Убедимся, что строка даты/времени корректно форматируется
                try {
                    const testDate = new Date(message.created_at);
                    if (isNaN(testDate.getTime())) {
                        console.warn(`Некорректная дата в сообщении: ${message.created_at}`);
                        message.created_at = new Date().toISOString();
                    }
                } catch (e) {
                    console.error(`Ошибка при обработке даты: ${e.message}`);
                    message.created_at = new Date().toISOString();
                }
                
                return message;
            });
            
            // Кэшируем сообщения для оффлайн-доступа
            cacheMessages(threadId, formattedMessages);
            
            // Передаем обработанные сообщения функции рендеринга
            renderChatMessages(formattedMessages);
        } else {
            console.warn('Сервер вернул пустой список сообщений или некорректный формат данных');
            renderChatMessages([]);
        }
    } catch (error) {
        console.error('Ошибка при загрузке сообщений:', error);
        
        // Проверяем, связана ли ошибка с сетью
        if (error.message.includes('сети') || error.message.includes('подключен')) {
            networkState.setOnlineStatus(false);
            
            // Пытаемся загрузить из кэша
            try {
                const cachedMessages = await loadCachedMessages(threadId);
                if (cachedMessages && cachedMessages.length > 0) {
                    renderChatMessages(cachedMessages);
                    showNotification('Загружены сообщения из локального хранилища', 'info');
                    return;
                }
            } catch (cacheError) {
                console.error('Ошибка при загрузке из кэша:', cacheError);
            }
        }
        
        showNotification(`Не удалось загрузить сообщения чата: ${error.message}`, 'error');
        
        // Показываем пустое состояние с возможностью повторить
        const messagesContainer = document.getElementById('messages-container');
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-circle"></i>
                    <h3>Ошибка загрузки сообщений</h3>
                    <p>${error.message}</p>
                    <button id="retry-load-messages" class="empty-action-btn">Повторить загрузку</button>
                </div>
            `;
            
            // Добавляем обработчик для повторной попытки
            const retryBtn = document.getElementById('retry-load-messages');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    const messagesContainer = document.getElementById('messages-container');
                    if (messagesContainer) {
                        messagesContainer.innerHTML = `
                            <div class="message-loading">
                                <div class="message-loading-spinner"></div>
                            </div>
                        `;
                    }
                    loadChatMessages(threadId);
                });
            }
        }
    }
}

/**
 * Кэширует сообщения треда в локальное хранилище
 * @param {string} threadId - ID треда
 * @param {Array} messages - Массив сообщений
 */
function cacheMessages(threadId, messages) {
    try {
        // Ограничиваем количество сообщений для кэширования
        const messagesToCache = messages.slice(0, 50); // Кэшируем до 50 последних сообщений
        localStorage.setItem(`cached_messages_${threadId}`, JSON.stringify(messagesToCache));
        console.log(`Кэшировано ${messagesToCache.length} сообщений для треда ${threadId}`);
    } catch (error) {
        console.error('Ошибка при кэшировании сообщений:', error);
    }
}

/**
 * Загружает сообщения из кэша
 * @param {string} threadId - ID треда
 * @returns {Promise<Array>} - Промис с массивом сообщений
 */
async function loadCachedMessages(threadId) {
    return new Promise((resolve, reject) => {
        try {
            const cachedMessagesStr = localStorage.getItem(`cached_messages_${threadId}`);
            if (cachedMessagesStr) {
                const cachedMessages = JSON.parse(cachedMessagesStr);
                console.log(`Загружено ${cachedMessages.length} сообщений из кэша для треда ${threadId}`);
                resolve(cachedMessages);
            } else {
                reject(new Error('Сообщения не найдены в кэше'));
            }
        } catch (error) {
            reject(error);
        }
    });
}

/**
 * Отображает сообщения чата с использованием временных меток
 * @param {Array} messages - Массив объектов с сообщениями
 */
function renderChatMessages(messages) {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Контейнер сообщений не найден');
        return;
    }
    
    messagesContainer.innerHTML = '';
    
    if (!messages || messages.length === 0) {
        // Если сообщений нет, показываем приветственное сообщение
        addAssistantMessage('Здравствуйте! Я юридический ассистент LawGPT. Чем я могу вам помочь?');
        return;
    }
    
    // Группируем сообщения по дате для отображения разделителей
    const groupedMessages = groupMessagesByDate(messages);
    
    // Добавляем разделители дат и сообщения
    Object.entries(groupedMessages).forEach(([dateKey, messagesGroup]) => {
        // Добавляем разделитель с датой
        addDateSeparator(dateKey);
        
        // Добавляем все сообщения даты с сохранением временных меток
        messagesGroup.forEach(message => {
            // Преобразуем строку с датой в объект Date
            const timestamp = message.created_at ? new Date(message.created_at) : new Date();
            
            if (message.role === 'user') {
                addUserMessage(message.content, timestamp);
            } else if (message.role === 'assistant') {
                addAssistantMessage(message.content, timestamp);
            }
        });
    });
    
    // Прокручиваем к последнему сообщению
    scrollToBottom();
    
    // Инициализируем интерактивные элементы
    initMessageActions();
}

/**
 * Группирует сообщения по дате для показа разделителей
 * @param {Array} messages - Массив сообщений
 * @returns {Object} - Объект с сгруппированными сообщениями
 */
function groupMessagesByDate(messages) {
    const grouped = {};
    
    messages.forEach(message => {
        const timestamp = message.created_at ? new Date(message.created_at) : new Date();
        const dateKey = timestamp.toLocaleDateString('ru-RU');
        
        if (!grouped[dateKey]) {
            grouped[dateKey] = [];
        }
        
        grouped[dateKey].push(message);
    });
    
    return grouped;
}

/**
 * Добавляет разделитель даты в контейнер сообщений
 * @param {string} dateStr - Строка даты для отображения
 */
function addDateSeparator(dateStr) {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) return;
    
    const today = new Date().toLocaleDateString('ru-RU');
    const yesterday = new Date(Date.now() - 86400000).toLocaleDateString('ru-RU');
    
    let displayText;
    if (dateStr === today) {
        displayText = 'Сегодня';
    } else if (dateStr === yesterday) {
        displayText = 'Вчера';
    } else {
        displayText = dateStr;
    }
    
    const separator = document.createElement('div');
    separator.className = 'date-separator';
    separator.innerHTML = `<span>${displayText}</span>`;
    
    messagesContainer.appendChild(separator);
}

/**
 * Добавляет сообщение пользователя в чат
 * @param {string} text - Текст сообщения
 * @param {Date} timestamp - Временная метка сообщения (опционально)
 */
function addUserMessage(text, timestamp = null) {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Контейнер сообщений не найден');
        return;
    }
    
    // Если временная метка не передана, создаем текущую
    if (!timestamp) {
        timestamp = new Date();
    }
    
    const template = document.getElementById('message-template');
    // Если шаблон не найден, создаем элемент вручную
    if (!template) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message message-user';
        messageElement.setAttribute('role', 'listitem');
        
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        contentElement.textContent = text;
        
        const timeElement = document.createElement('div');
        timeElement.className = 'message-time';
        
        // Используем переданную или созданную временную метку
        const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
        timeElement.textContent = timeStr;
        
        // Сохраняем временную метку в атрибуте data-timestamp
        messageElement.dataset.timestamp = timestamp.getTime();
        messageElement.dataset.role = 'user';
        
        // Собираем элемент сообщения
        messageElement.appendChild(contentElement);
        messageElement.appendChild(timeElement);
        
        // Добавляем кнопки действий для сообщения
        const actionsElement = document.createElement('div');
        actionsElement.className = 'message-actions';
        actionsElement.innerHTML = `
            <button class="message-action copy-action" aria-label="Копировать сообщение">
                <i class="fas fa-copy"></i>
            </button>
        `;
        messageElement.appendChild(actionsElement);
        
        // Добавляем в контейнер сообщений
        messagesContainer.appendChild(messageElement);
        scrollToBottom();
        return;
    }
    
    // Если шаблон найден, используем его
    const messageElement = template.content.cloneNode(true).querySelector('.message');
    
    messageElement.classList.add('message-user');
    messageElement.setAttribute('role', 'listitem');
    
    const contentElement = messageElement.querySelector('.message-content');
    contentElement.textContent = text;
    
    const timeElement = messageElement.querySelector('.message-time');
    
    // Используем переданную или созданную временную метку
    const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
    timeElement.textContent = timeStr;
    
    // Сохраняем временную метку в атрибуте data-timestamp
    messageElement.dataset.timestamp = timestamp.getTime();
    messageElement.dataset.role = 'user';
    
    // Добавляем кнопки действий для сообщения
    const actionsElement = document.createElement('div');
    actionsElement.className = 'message-actions';
    actionsElement.innerHTML = `
        <button class="message-action copy-action" aria-label="Копировать сообщение">
            <i class="fas fa-copy"></i>
        </button>
    `;
    messageElement.appendChild(actionsElement);
    
    messagesContainer.appendChild(messageElement);
    scrollToBottom();
}

/**
 * Добавляет сообщение ассистента в чат
 * @param {string} text - Текст сообщения
 * @param {Date} timestamp - Временная метка сообщения (опционально)
 */
function addAssistantMessage(text, timestamp = null) {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Контейнер сообщений не найден');
        return;
    }
    
    // Если временная метка не передана, создаем текущую
    if (!timestamp) {
        timestamp = new Date();
    }
    
    const template = document.getElementById('message-template');
    
    // Если шаблон не найден, создаем элемент вручную
    if (!template) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message message-assistant';
        messageElement.setAttribute('role', 'listitem');
        
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        
        // Если включена обработка Markdown и библиотека загружена
        if (config.markdownEnabled && window.markdown) {
            try {
                contentElement.innerHTML = window.markdown.parse(text);
            } catch (error) {
                console.error('Ошибка при обработке Markdown:', error);
                contentElement.textContent = text;
            }
        } else {
            contentElement.textContent = text;
        }
        
        const timeElement = document.createElement('div');
        timeElement.className = 'message-time';
        
        // Используем переданную или созданную временную метку
        const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
        timeElement.textContent = timeStr;
        
        // Сохраняем временную метку в атрибуте data-timestamp
        messageElement.dataset.timestamp = timestamp.getTime();
        messageElement.dataset.role = 'assistant';
        
        // Собираем элемент сообщения
        messageElement.appendChild(contentElement);
        messageElement.appendChild(timeElement);
        
        // Добавляем кнопки действий для сообщения
        const actionsElement = document.createElement('div');
        actionsElement.className = 'message-actions';
        actionsElement.innerHTML = `
            <button class="message-action copy-action" aria-label="Копировать сообщение">
                <i class="fas fa-copy"></i>
            </button>
            <button class="message-action speak-action" aria-label="Озвучить сообщение">
                <i class="fas fa-volume-up"></i>
            </button>
        `;
        messageElement.appendChild(actionsElement);
        
        // Добавляем в контейнер сообщений
        messagesContainer.appendChild(messageElement);
        
        // Инициализируем специальные компоненты в сообщении
        if (window.MarkdownProcessor) {
            MarkdownProcessor.processMessage(messageElement);
        }
        
        // Добавляем интерактивные элементы в код
        enhanceCodeBlocks(messageElement);
        
        scrollToBottom();
        return;
    }
    
    // Если шаблон найден, используем его
    const messageElement = template.content.cloneNode(true).querySelector('.message');
    
    messageElement.classList.add('message-assistant');
    messageElement.setAttribute('role', 'listitem');
    
    const contentElement = messageElement.querySelector('.message-content');
    
    // Если включена обработка Markdown и библиотека загружена
    if (config.markdownEnabled && window.markdown) {
        try {
            contentElement.innerHTML = window.markdown.parse(text);
        } catch (error) {
            console.error('Ошибка при обработке Markdown:', error);
            contentElement.textContent = text;
        }
    } else {
        contentElement.textContent = text;
    }
    
    const timeElement = messageElement.querySelector('.message-time');
    
    // Используем переданную или созданную временную метку
    const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
    timeElement.textContent = timeStr;
    
    // Сохраняем временную метку в атрибуте data-timestamp
    messageElement.dataset.timestamp = timestamp.getTime();
    messageElement.dataset.role = 'assistant';
    
    // Добавляем кнопки действий для сообщения
    const actionsElement = document.createElement('div');
    actionsElement.className = 'message-actions';
    actionsElement.innerHTML = `
        <button class="message-action copy-action" aria-label="Копировать сообщение">
            <i class="fas fa-copy"></i>
        </button>
        <button class="message-action speak-action" aria-label="Озвучить сообщение">
            <i class="fas fa-volume-up"></i>
        </button>
    `;
    messageElement.appendChild(actionsElement);
    
    messagesContainer.appendChild(messageElement);
    
    // Инициализируем специальные компоненты в сообщении
    if (window.MarkdownProcessor) {
        MarkdownProcessor.processMessage(messageElement);
    }
    
    // Добавляем интерактивные элементы в код
    enhanceCodeBlocks(messageElement);
    
    scrollToBottom();
}

/**
 * Инициализирует обработчики событий для элементов сообщений
 */
function initMessageActions() {
    // Добавляем обработчики для кнопок копирования
    document.querySelectorAll('.copy-action').forEach(button => {
        button.addEventListener('click', handleCopyMessage);
    });
    
    // Добавляем обработчики для кнопок озвучивания
    document.querySelectorAll('.speak-action').forEach(button => {
        button.addEventListener('click', handleSpeakMessage);
    });
}

/**
 * Улучшает блоки кода - добавляет кнопки копирования и выделения языка
 * @param {HTMLElement} messageElement - Элемент сообщения
 */
function enhanceCodeBlocks(messageElement) {
    const codeBlocks = messageElement.querySelectorAll('pre code');
    
    codeBlocks.forEach(codeBlock => {
        const pre = codeBlock.parentNode;
        
        // Если блок уже обработан, пропускаем
        if (pre.classList.contains('enhanced')) return;
        
        // Определяем язык кода
        let language = '';
        if (codeBlock.className) {
            const match = codeBlock.className.match(/language-(\w+)/);
            if (match) {
                language = match[1];
            }
        }
        
        // Создаем панель инструментов
        const toolbar = document.createElement('div');
        toolbar.className = 'code-toolbar';
        
        // Добавляем метку языка, если определен
        if (language) {
            const langLabel = document.createElement('span');
            langLabel.className = 'code-language';
            langLabel.textContent = language;
            toolbar.appendChild(langLabel);
        }
        
        // Создаем кнопку копирования
        const copyButton = document.createElement('button');
        copyButton.className = 'code-copy-button';
        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
        copyButton.setAttribute('aria-label', 'Копировать код');
        copyButton.addEventListener('click', (e) => {
            e.stopPropagation();
            
            // Копируем текст
            const code = codeBlock.textContent;
            navigator.clipboard.writeText(code)
                .then(() => {
                    // Показываем индикатор успеха
                    copyButton.innerHTML = '<i class="fas fa-check"></i>';
                    
                    // Возвращаем исходную иконку через 2 секунды
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                    }, 2000);
                })
                .catch(err => {
                    console.error('Ошибка при копировании кода:', err);
                    copyButton.innerHTML = '<i class="fas fa-times"></i>';
                    
                    // Возвращаем исходную иконку через 2 секунды
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                    }, 2000);
                });
        });
        toolbar.appendChild(copyButton);
        
        // Создаем обертку для кода с панелью инструментов
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        
        // Перемещаем блок кода в обертку
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(toolbar);
        wrapper.appendChild(pre);
        
        // Отмечаем блок как обработанный
        pre.classList.add('enhanced');
    });
}

/**
 * Обработчик для копирования сообщения
 * @param {Event} e - Событие клика
 */
function handleCopyMessage(e) {
    const messageElement = e.currentTarget.closest('.message');
    if (!messageElement) return;
    
    const contentElement = messageElement.querySelector('.message-content');
    if (!contentElement) return;
    
    // Получаем текст или HTML в зависимости от типа сообщения
    let textToCopy;
    
    if (messageElement.classList.contains('message-assistant')) {
        // Для сообщений ассистента копируем форматированный текст
        // Создаем временный элемент для извлечения только текста из HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = contentElement.innerHTML;
        
        // Заменяем элементы <pre> и <code> их текстовым содержимым
        tempDiv.querySelectorAll('pre, code').forEach(element => {
            element.textContent = element.textContent;
        });
        
        textToCopy = tempDiv.textContent;
    } else {
        // Для сообщений пользователя просто копируем текст
        textToCopy = contentElement.textContent;
    }
    
    // Копируем в буфер обмена
    navigator.clipboard.writeText(textToCopy)
        .then(() => {
            // Показываем уведомление об успешном копировании
            showNotification('Сообщение скопировано в буфер обмена', 'success');
            
            // Анимируем кнопку копирования
            const copyButton = e.currentTarget;
            copyButton.classList.add('copied');
            
            // Через 2 секунды убираем класс
            setTimeout(() => {
                copyButton.classList.remove('copied');
            }, 2000);
        })
        .catch(err => {
            console.error('Ошибка при копировании текста:', err);
            showNotification('Не удалось скопировать сообщение', 'error');
        });
}

/**
 * Обработчик для озвучивания сообщения
 * @param {Event} e - Событие клика
 */
function handleSpeakMessage(e) {
    // Проверяем поддержку Web Speech API
    if (!('speechSynthesis' in window)) {
        showNotification('Ваш браузер не поддерживает озвучивание текста', 'error');
        return;
    }
    
    const messageElement = e.currentTarget.closest('.message');
    if (!messageElement) return;
    
    const contentElement = messageElement.querySelector('.message-content');
    if (!contentElement) return;
    
    // Получаем текстовое содержимое элемента
    // Создаем временный элемент для извлечения только текста из HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = contentElement.innerHTML;
    
    // Удаляем блоки кода, чтобы не зачитывать их
    tempDiv.querySelectorAll('pre, code').forEach(element => {
        element.remove();
    });
    
    const textToSpeak = tempDiv.textContent.trim();
    
    if (!textToSpeak) {
        showNotification('Нет текста для озвучивания', 'error');
        return;
    }
    
    // Создаем экземпляр SpeechSynthesisUtterance
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    
    // Устанавливаем язык в зависимости от содержимого (можно доработать определение языка)
    utterance.lang = 'ru-RU';
    
    // Озвучиваем текст
    window.speechSynthesis.speak(utterance);
    
    // Показываем уведомление
    showNotification('Озвучивание текста...', 'info');
    
    // Анимируем кнопку
    const speakButton = e.currentTarget;
    speakButton.classList.add('speaking');
    
    // По окончании озвучивания
    utterance.onend = () => {
        speakButton.classList.remove('speaking');
    };
    
    // В случае ошибки
    utterance.onerror = () => {
        speakButton.classList.remove('speaking');
        showNotification('Ошибка при озвучивании текста', 'error');
    };
}

/**
 * Показывает индикатор набора текста ассистентом
 */
function showTypingIndicator() {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Контейнер сообщений не найден');
        return;
    }
    
    // Сначала проверяем, существует ли уже индикатор
    let indicator = document.getElementById('typing-indicator-container');
    
    // Если индикатор уже существует, просто показываем его
    if (indicator) {
        indicator.style.display = 'flex';
        return;
    }
    
    // Создаем новый индикатор
    const container = document.createElement('div');
    container.className = 'message message-assistant';
    container.id = 'typing-indicator-container';
    container.setAttribute('aria-live', 'polite');
    
    // Создаем индикатор с анимированными точками
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <span class="sr-only">Ассистент печатает...</span>
    `;
    
    // Добавляем индикатор в контейнер
    container.appendChild(typingIndicator);
    
    // Добавляем элемент для статуса обработки
    const statusElement = document.createElement('div');
    statusElement.className = 'typing-status';
    statusElement.textContent = 'Обработка запроса...';
    container.appendChild(statusElement);
    
    // Добавляем контейнер в список сообщений
    messagesContainer.appendChild(container);
    
    // Прокручиваем к нижней части контейнера
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Скрывает индикатор набора текста
 */
function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator-container');
    if (indicator) {
        // Плавно скрываем и удаляем индикатор
        indicator.style.opacity = '0';
        indicator.style.transform = 'translateY(10px)';
        
        // Через 300мс удаляем полностью
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 300);
    }
}

/**
 * Обновляет текст в индикаторе набора текста
 * @param {string} message - Сообщение о статусе обработки
 */
function updateTypingIndicator(message) {
    const typingContainer = document.getElementById('typing-indicator-container');
    
    if (!typingContainer) {
        showTypingIndicator();
        setTimeout(() => updateTypingIndicator(message), 100);
        return;
    }
    
    // Обновляем текстовый элемент
    const statusText = typingContainer.querySelector('.typing-status');
    if (statusText) {
        statusText.textContent = message;
        
        // Обновляем элемент для скринридеров
        const srText = typingContainer.querySelector('.sr-only');
        if (srText) {
            srText.textContent = `Ассистент: ${message}`;
        }
    }
}

/**
 * Отправляет сообщение пользователя
 */
async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const fileUpload = document.getElementById('file-upload');
    
    if (!messageInput || !fileUpload) {
        console.error('Элементы ввода сообщения не найдены');
        return;
    }
    
    const text = messageInput.value.trim();
    const file = fileUpload.files[0];
    
    // Если нет ни текста, ни файла - выходим
    if (!text && !file) {
        return;
    }
    
    // Проверяем соединение
    if (!networkState.online) {
        showNotification('Нет подключения к интернету. Сообщение будет отправлено, когда соединение восстановится.', 'warning');
        
        // Сохраняем сообщение в очередь для последующей отправки
        const pendingMessage = {
            text,
            file: file ? file.name : null,
            timestamp: new Date()
        };
        
        savePendingMessage(pendingMessage);
        
        // Показываем временно сообщение с индикатором ожидания
        addPendingMessage(text);
        
        // Очищаем поле ввода
        messageInput.value = '';
        messageInput.style.height = 'auto';
        return;
    }
    
    // Получаем ID текущего треда
    const threadId = localStorage.getItem(config.storageThreadKey);
    if (!threadId) {
        showNotification('Ошибка: чат не выбран', 'error');
        return;
    }
    
    // Фиксируем время отправки сообщения пользователя
    const userTimestamp = new Date();
    
    // Добавляем сообщение пользователя в чат с зафиксированным временем
    addUserMessage(text, userTimestamp);
    
    // Очищаем поле ввода
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.disabled = true;
    }
    
    // Показываем индикатор набора текста
    showTypingIndicator();
    
    // Создаем FormData для отправки текста и файла
    const formData = new FormData();
    if (text) {
        formData.append('query', text);
    }
    if (file) {
        formData.append('file', file);
        removeUploadedFile(); // Очищаем предпросмотр файла
    }
    
    // Определяем список статусов и времени их показа
    const processingSteps = [
        { message: "Обработка запроса...", delay: 500 },
        { message: "Поиск в законодательстве...", delay: 1000 },
        { message: "Поиск в судебной практике...", delay: 1000 },
        { message: "Анализ данных...", delay: 3000 },
        { message: "Формирование ответа...", delay: 5000 }
    ];
    
    // Запускаем отображение статусов
    const statusPromises = processingSteps.map((step, index) => {
        return new Promise(resolve => {
            setTimeout(() => {
                // Проверяем, что индикатор всё ещё отображается
                const indicator = document.getElementById('typing-indicator-container');
                if (indicator) {
                    updateTypingIndicator(step.message);
                }
                resolve();
            }, step.delay + (index > 0 ? processingSteps[index-1].delay : 0));
        });
    });
    
    try {
        console.log(`Отправка сообщения в тред ${threadId}`);
        
        // Делаем реальный запрос к серверу
        const response = await apiRequestFormData(`/chat/${threadId}`, formData);
        
        // Скрываем индикатор набора текста
        hideTypingIndicator();
        
        // Фиксируем время получения ответа ассистента
        const assistantTimestamp = new Date();
        
        if (response.assistant_response) {
            // Добавляем ответ ассистента с зафиксированным временем
            addAssistantMessage(response.assistant_response, assistantTimestamp);
            
            // Если был загружен файл, показываем информацию о распознанном тексте
            if (response.recognized_text && response.file_name) {
                const infoMessage = document.createElement('div');
                infoMessage.className = 'message message-system';
                infoMessage.innerHTML = `
                    <div class="message-content">
                        <div class="file-info">
                            <i class="fas fa-file-alt"></i>
                            <span>Файл обработан: ${response.file_name}</span>
                            <button class="file-details-btn">Подробнее</button>
                        </div>
                    </div>
                `;
                
                // Добавляем системному сообщению ту же временную метку
                infoMessage.dataset.timestamp = assistantTimestamp.getTime();
                
                // Добавляем кнопку для просмотра извлеченного текста
                const detailsBtn = infoMessage.querySelector('.file-details-btn');
                if (detailsBtn) {
                    detailsBtn.addEventListener('click', () => {
                        showExtractedTextModal(response.file_name, response.recognized_text);
                    });
                }
                
                document.getElementById('messages-container').appendChild(infoMessage);
            }
            
            // Сохраняем сообщение в историю для оффлайн-доступа
            saveMessageToHistory(threadId, {
                role: 'user',
                content: text,
                created_at: userTimestamp.toISOString()
            });
            
            saveMessageToHistory(threadId, {
                role: 'assistant',
                content: response.assistant_response,
                created_at: assistantTimestamp.toISOString()
            });
        } else {
            showNotification('Ошибка: не получен ответ от ассистента', 'error');
        }
    } catch (error) {
        hideTypingIndicator();
        showNotification(`Ошибка при отправке сообщения: ${error.message}`, 'error');
        console.error('Ошибка при отправке сообщения:', error);
        
        // Добавляем сообщение об ошибке вместо ответа ассистента
        const errorMessage = document.createElement('div');
        errorMessage.className = 'message message-error';
        errorMessage.innerHTML = `
            <div class="message-content">
                <i class="fas fa-exclamation-circle"></i>
                <span>Ошибка при отправке сообщения: ${error.message}</span>
                <button class="retry-btn">Повторить</button>
            </div>
        `;
        
        // Добавляем кнопку повтора
        const retryBtn = errorMessage.querySelector('.retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                // Удаляем сообщение об ошибке
                errorMessage.remove();
                
                // Восстанавливаем текст сообщения
                messageInput.value = text;
                
                // Включаем кнопку отправки
                if (sendBtn) {
                    sendBtn.disabled = false;
                }
            });
        }
        
        document.getElementById('messages-container').appendChild(errorMessage);
    }
    
    // Прокручиваем к последнему сообщению
    scrollToBottom();
}

/**
 * Сохраняет сообщение в историю для оффлайн-доступа
 * @param {string} threadId - ID треда
 * @param {Object} message - Объект сообщения
 */
function saveMessageToHistory(threadId, message) {
    try {
        // Получаем текущую историю чата
        const historyKey = `chat_history_${threadId}`;
        const historyStr = localStorage.getItem(historyKey);
        let history = historyStr ? JSON.parse(historyStr) : [];
        
        // Добавляем новое сообщение
        history.push(message);
        
        // Ограничиваем размер истории
        if (history.length > 100) {
            history = history.slice(-100);
        }
        
        // Сохраняем обновленную историю
        localStorage.setItem(historyKey, JSON.stringify(history));
    } catch (error) {
        console.error('Ошибка при сохранении сообщения в историю:', error);
    }
}

/**
 * Сохраняет сообщение, которое не удалось отправить
 * @param {Object} message - Объект сообщения
 */
function savePendingMessage(message) {
    try {
        const threadId = localStorage.getItem(config.storageThreadKey);
        if (!threadId) return;
        
        const pendingKey = `pending_messages_${threadId}`;
        const pendingStr = localStorage.getItem(pendingKey);
        const pendingMessages = pendingStr ? JSON.parse(pendingStr) : [];
        
        pendingMessages.push(message);
        localStorage.setItem(pendingKey, JSON.stringify(pendingMessages));
    } catch (error) {
        console.error('Ошибка при сохранении ожидающего сообщения:', error);
    }
}

/**
 * Добавляет ожидающее сообщение в чат
 * @param {string} text - Текст сообщения
 */
function addPendingMessage(text) {
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) return;
    
    const pendingMessage = document.createElement('div');
    pendingMessage.className = 'message message-user message-pending';
    pendingMessage.innerHTML = `
        <div class="message-content">${text}</div>
        <div class="message-time">
            <span class="pending-indicator">
                <i class="fas fa-clock"></i> Ожидает отправки...
            </span>
        </div>
    `;
    
    messagesContainer.appendChild(pendingMessage);
    scrollToBottom();
}

/**
 * Показывает модальное окно с извлеченным текстом файла
 * @param {string} fileName - Имя файла
 * @param {string} extractedText - Извлеченный текст
 */
function showExtractedTextModal(fileName, extractedText) {
    // Создаем модальное окно, если его еще нет
    let modal = document.getElementById('extracted-text-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'extracted-text-modal';
        modal.className = 'modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-labelledby', 'extracted-text-title');
        
        document.body.appendChild(modal);
    }
    
    // Добавляем содержимое
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-modal" aria-label="Закрыть">&times;</span>
            <h2 id="extracted-text-title">Содержимое файла: ${fileName}</h2>
            <div class="extracted-text-container">
                <pre>${extractedText}</pre>
            </div>
            <div class="modal-footer">
                <button class="copy-extracted-text">Копировать текст</button>
                <button class="close-modal-btn">Закрыть</button>
            </div>
        </div>
    `;
    
    // Обработчики для закрытия
    const closeBtn = modal.querySelector('.close-modal');
    const closeModalBtn = modal.querySelector('.close-modal-btn');
    
    const closeModal = () => {
        modal.style.display = 'none';
    };
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }
    
    // Обработчик для копирования
    const copyBtn = modal.querySelector('.copy-extracted-text');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(extractedText)
                .then(() => {
                    copyBtn.textContent = 'Скопировано!';
                    setTimeout(() => {
                        copyBtn.textContent = 'Копировать текст';
                    }, 2000);
                })
                .catch(err => {
                    console.error('Ошибка при копировании:', err);
                    copyBtn.textContent = 'Ошибка копирования';
                    setTimeout(() => {
                        copyBtn.textContent = 'Копировать текст';
                    }, 2000);
                });
        });
    }
    
    // Закрытие по клику вне модального окна
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // Закрытие по Escape
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            closeModal();
        }
    });
    
    // Показываем модальное окно
    modal.style.display = 'block';
}

/**
 * Обработчик загрузки файла
 * @param {Event} e - Событие изменения input file
 */
function handleFileUpload(e) {
    const file = e.target.files[0];
    
    if (!file) {
        return;
    }
    
    // Проверяем размер файла
    if (file.size > config.maxFileSize) {
        showNotification(`Размер файла превышает ${config.maxFileSize / (1024 * 1024)} МБ`, 'error');
        e.target.value = '';
        return;
    }
    
    // Проверяем тип файла
    const allowedTypes = ['.pdf', '.doc', '.docx'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!allowedTypes.some(type => fileExtension.endsWith(type))) {
        showNotification('Поддерживаются только файлы PDF и Word (.pdf, .doc, .docx)', 'error');
        e.target.value = '';
        return;
    }
    
    // Показываем предпросмотр файла
    const fileNameElement = document.getElementById('file-name');
    if (fileNameElement) {
        fileNameElement.textContent = file.name;
        
        // Добавляем размер файла
        const fileSize = file.size / 1024 < 1024 
            ? `${(file.size / 1024).toFixed(1)} КБ` 
            : `${(file.size / (1024 * 1024)).toFixed(1)} МБ`;
        
        fileNameElement.innerHTML = `${file.name} <span class="file-size">(${fileSize})</span>`;
    }
    
    const uploadPreview = document.getElementById('upload-preview');
    if (uploadPreview) {
        uploadPreview.classList.remove('hidden');
        
        // Определяем иконку в зависимости от типа файла
        let fileIcon = 'fa-file';
        if (fileExtension === '.pdf') {
            fileIcon = 'fa-file-pdf';
        } else if (fileExtension === '.doc' || fileExtension === '.docx') {
            fileIcon = 'fa-file-word';
        }
        
        // Добавляем иконку
        const iconElement = uploadPreview.querySelector('.file-icon') || document.createElement('i');
        iconElement.className = `fas ${fileIcon} file-icon`;
        
        if (!uploadPreview.contains(iconElement)) {
            uploadPreview.insertBefore(iconElement, uploadPreview.firstChild);
        }
    }
    
    // Активируем кнопку отправки
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.disabled = false;
    }
}

/**
 * Удаляет загруженный файл
 */
function removeUploadedFile() {
    const fileUpload = document.getElementById('file-upload');
    if (fileUpload) {
        fileUpload.value = '';
    }
    
    const uploadPreview = document.getElementById('upload-preview');
    if (uploadPreview) {
        uploadPreview.classList.add('hidden');
    }
    
    // Проверяем статус кнопки отправки
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    if (messageInput && sendBtn) {
        sendBtn.disabled = messageInput.value.trim() === '' || !networkState.online;
    }
}

/**
 * Загружает профиль пользователя
 */
async function loadUserProfile() {
    try {
        const response = await apiRequest('/profile', 'GET');
        
        if (response) {
            const userName = `${response.first_name} ${response.last_name}`;
            const userNameElement = document.getElementById('user-name');
            if (userNameElement) {
                userNameElement.textContent = userName;
                userNameElement.title = response.email;
            }
            
            // Сохраняем данные профиля в локальное хранилище для оффлайн-режима
            localStorage.setItem('user_profile', JSON.stringify(response));
        }
    } catch (error) {
        console.error('Ошибка при загрузке профиля:', error);
        
        // Пытаемся получить профиль из локального хранилища
        const cachedProfile = localStorage.getItem('user_profile');
        if (cachedProfile) {
            try {
                const profile = JSON.parse(cachedProfile);
                const userName = `${profile.first_name} ${profile.last_name}`;
                const userNameElement = document.getElementById('user-name');
                if (userNameElement) {
                    userNameElement.textContent = userName;
                    userNameElement.title = profile.email;
                }
            } catch (e) {
                console.error('Ошибка при загрузке профиля из кэша:', e);
            }
        }
    }
}

/**
 * Прокручивает контейнер сообщений к последнему сообщению
 */
function scrollToBottom() {
    if (!config.autoscrollEnabled) return;
    
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        // Используем плавную прокрутку
        messagesContainer.scrollTo({
            top: messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
}

/**
 * Переключает видимость между основным приложением и экранами аутентификации
 * @param {boolean} showAppScreen - true для показа основного приложения, false для экранов аутентификации
 */
function toggleAppVisibility(showAppScreen) {
    const authScreens = document.getElementById('auth-screens');
    const mainApp = document.getElementById('main-app');
    
    if (!authScreens || !mainApp) {
        console.error('Не найдены необходимые элементы для переключения видимости');
        return;
    }
    
    if (showAppScreen) {
        // Вертикальный переход с затуханием
        authScreens.style.opacity = '0';
        authScreens.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            authScreens.style.display = 'none';
            mainApp.style.display = 'flex';
            
            // Анимация появления
            mainApp.style.opacity = '0';
            mainApp.style.transform = 'translateY(-20px)';
            
            requestAnimationFrame(() => {
                mainApp.style.opacity = '1';
                mainApp.style.transform = 'translateY(0)';
            });
        }, 300);
    } else {
        // Вертикальный переход с затуханием
        mainApp.style.opacity = '0';
        mainApp.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            mainApp.style.display = 'none';
            authScreens.style.display = 'flex';
            
            // Анимация появления
            authScreens.style.opacity = '0';
            authScreens.style.transform = 'translateY(20px)';
            
            requestAnimationFrame(() => {
                authScreens.style.opacity = '1';
                authScreens.style.transform = 'translateY(0)';
            });
        }, 300);
    }
}

// ============================================================
// Функции для голосового ввода
// ============================================================

// Проверка поддержки браузером Web Speech API
function isSpeechRecognitionSupported() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
}

// Функция для начала записи голоса с использованием Web Speech API
function startVoiceRecording() {
    const messageInput = document.getElementById('message-input');
    const voiceRecordBtn = document.getElementById('voice-record-btn');
    const voiceStopBtn = document.getElementById('voice-stop-btn');
    
    if (!isSpeechRecognitionSupported()) {
        showNotification('Голосовой ввод не поддерживается в вашем браузере', 'error');
        return;
    }
    
    // Создаем объект распознавания речи
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    // Настройки распознавания
    recognition.lang = 'ru-RU'; // Русский язык по умолчанию
    recognition.interimResults = false; // Только финальный результат
    recognition.maxAlternatives = 1; // Один вариант распознавания
    
    // Обработчики событий
    recognition.onstart = () => {
        voiceRecordBtn.style.display = 'none';
        voiceStopBtn.style.display = 'inline-block';
        messageInput.placeholder = 'Говорите...';
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        messageInput.value = transcript;
        
        // Восстанавливаем кнопки
        voiceRecordBtn.style.display = 'inline-block';
        voiceStopBtn.style.display = 'none';
        messageInput.placeholder = 'Введите сообщение...';
        
        // Активируем кнопку отправки
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) {
            sendBtn.disabled = false;
        }
    };
    
    recognition.onerror = (event) => {
        console.error('Ошибка распознавания:', event.error);
        
        // Восстанавливаем кнопки
        voiceRecordBtn.style.display = 'inline-block';
        voiceStopBtn.style.display = 'none';
        messageInput.placeholder = 'Введите сообщение...';
        
        switch(event.error) {
            case 'no-speech':
                showNotification('Речь не распознана', 'error');
                break;
            case 'audio-capture':
                showNotification('Не удалось захватить аудио', 'error');
                break;
            case 'not-allowed':
                showNotification('Нет разрешения на использование микрофона', 'error');
                break;
            default:
                showNotification('Ошибка при распознавании речи', 'error');
        }
    };
    
    recognition.onend = () => {
        voiceRecordBtn.style.display = 'inline-block';
        voiceStopBtn.style.display = 'none';
        messageInput.placeholder = 'Введите сообщение...';
    };
    
    // Начинаем распознавание
    recognition.start();
}

// Получаем текущий выбранный язык распознавания
function getSelectedVoiceLanguage() {
    const languageSelect = document.getElementById('voice-language-select');
    return languageSelect ? languageSelect.value : 'ru-RU';
}

// Функция для альтернативного метода - серверное распознавание
async function startServerVoiceRecording() {
    const messageInput = document.getElementById('message-input');
    const voiceRecordBtn = document.getElementById('voice-record-btn');
    const voiceStopBtn = document.getElementById('voice-stop-btn');
    
    // Проверяем поддержку getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showNotification('Запись голоса не поддерживается в вашем браузере', 'error');
        return;
    }
    
    try {
        // Получаем доступ к микрофону
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        
        const audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            // Восстанавливаем кнопки
            voiceRecordBtn.style.display = 'inline-block';
            voiceStopBtn.style.display = 'none';
            messageInput.placeholder = 'Введите сообщение...';
            
            // Создаем Blob из записанных чанков
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            
            // Отправляем на сервер для распознавания
            const formData = new FormData();
            formData.append('file', audioBlob, 'voice_message.wav');
            
            // Получаем выбранный язык
            const selectedLanguage = getSelectedVoiceLanguage();
            formData.append('language', selectedLanguage);
            
            try {
                showLoading(); // Показываем индикатор загрузки
                const threadId = localStorage.getItem(config.storageThreadKey);
                const response = await apiRequestFormData(`/chat/${threadId}/voice-input`, formData);
                
                if (response.text) {
                    messageInput.value = response.text;
                    messageInput.focus();
                    
                    // Активируем кнопку отправки
                    const sendBtn = document.getElementById('send-btn');
                    if (sendBtn) {
                        sendBtn.disabled = false;
                    }
                    
                    showNotification('Голосовое сообщение распознано', 'success');
                }
            } catch (error) {
                showNotification(`Ошибка распознавания: ${error.message}`, 'error');
            } finally {
                hideLoading(); // Скрываем индикатор загрузки
            }
            
            // Закрываем медиапотоки
            stream.getTracks().forEach(track => track.stop());
        };
        
        // Начинаем запись
        mediaRecorder.start();
        
        // Обновляем UI
        voiceRecordBtn.style.display = 'none';
        voiceStopBtn.style.display = 'inline-block';
        messageInput.placeholder = 'Говорите...';
        
        // Останавливаем запись через 10 секунд или по нажатию стоп-кнопки
        const stopRecording = () => {
            if (mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            voiceStopBtn.removeEventListener('click', stopRecording);
        };
        
        voiceStopBtn.addEventListener('click', stopRecording);
        
        // Автоматическая остановка через 10 секунд
        setTimeout(() => {
            if (mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
        }, 10000);
    } catch (error) {
        console.error('Ошибка при записи голоса:', error);
        showNotification('Не удалось получить доступ к микрофону', 'error');
    }
}

// Добавляем кнопки голосового ввода в интерфейс
function addVoiceInputButtons() {
    const inputWrapper = document.querySelector('.input-wrapper');
    
    if (inputWrapper && !document.getElementById('voice-record-btn')) {
        // Создаем контейнер для голосовых элементов
        const voiceContainer = document.createElement('div');
        voiceContainer.className = 'voice-input-container';
        
        // Язык распознавания
        const languageSelect = document.createElement('select');
        languageSelect.id = 'voice-language-select';
        languageSelect.className = 'voice-language-select';
        
        // Список языков
        const languages = [
            { code: 'ru-RU', name: 'Русский' },
            { code: 'en-US', name: 'English' },
            { code: 'uk-UA', name: 'Українська' },
            { code: 'de-DE', name: 'Deutsch' },
            { code: 'fr-FR', name: 'Français' },
            { code: 'es-ES', name: 'Español' },
            { code: 'it-IT', name: 'Italiano' },
            { code: 'zh-CN', name: '中文' },
            { code: 'ja-JP', name: '日本語' }
        ];
        
        languages.forEach(lang => {
            const option = document.createElement('option');
            option.value = lang.code;
            option.textContent = lang.name;
            if (lang.code === 'ru-RU') option.selected = true;
            languageSelect.appendChild(option);
        });
        
        // Кнопка начала записи
        const voiceRecordBtn = document.createElement('button');
        voiceRecordBtn.id = 'voice-record-btn';
        voiceRecordBtn.className = 'action-btn voice-record-btn';
        voiceRecordBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceRecordBtn.title = 'Начать голосовой ввод';
        
        // Кнопка остановки записи (по умолчанию скрыта)
        const voiceStopBtn = document.createElement('button');
        voiceStopBtn.id = 'voice-stop-btn';
        voiceStopBtn.className = 'action-btn voice-stop-btn';
        voiceStopBtn.innerHTML = '<i class="fas fa-stop"></i>';
        voiceStopBtn.title = 'Остановить запись';
        voiceStopBtn.style.display = 'none';
        
        // Добавляем обработчики событий
        voiceRecordBtn.addEventListener('click', () => {
            // Если есть Web Speech API - используем его, иначе серверное распознавание
            if (isSpeechRecognitionSupported()) {
                startVoiceRecording();
            } else {
                startServerVoiceRecording();
            }
        });
        
        // Добавляем элементы в контейнер и в обертку ввода
        voiceContainer.appendChild(languageSelect);
        voiceContainer.appendChild(voiceRecordBtn);
        voiceContainer.appendChild(voiceStopBtn);
        
        inputWrapper.appendChild(voiceContainer);
    }
}

// Интеграция голосового ввода в инициализацию чата
function initChatInterface() {
    // Кнопка нового чата
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewChat);
    }
    
    // Логотип как ссылка на главную
    const logo = document.querySelector('.logo');
    if (logo) {
        logo.addEventListener('click', function(e) {
            e.preventDefault(); // Предотвращаем обычное действие ссылки
            
            // Код для перехода на главную
            const savedThreadId = localStorage.getItem(config.storageThreadKey);
            if (savedThreadId) {
                selectChatThread(savedThreadId);
            } else {
                createNewChat();
            }
        });
    }
    
    // Поле ввода сообщения
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('input', () => {
            // Автоматическое изменение высоты поля ввода
            messageInput.style.height = 'auto';
            messageInput.style.height = (messageInput.scrollHeight) + 'px';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
            
            // Активация/деактивация кнопки отправки
            const sendBtn = document.getElementById('send-btn');
            if (sendBtn) {
                sendBtn.disabled = messageInput.value.trim() === '';
            }
        });
        
        // Отправка сообщения по Enter
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (messageInput.value.trim()) {
                    const sendBtn = document.getElementById('send-btn');
                    if (sendBtn) {
                        sendBtn.click();
                    }
                }
            }
        });
    }
    
    // Отправка сообщения
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    // Загрузка файла
    const fileUpload = document.getElementById('file-upload');
    if (fileUpload) {
        fileUpload.addEventListener('change', handleFileUpload);
    }
    
    // Удаление файла
    const removeFileBtn = document.getElementById('remove-file-btn');
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', removeUploadedFile);
    }
    
    // Обработчики для модальных окон
    const navProfileBtn = document.getElementById('nav-profile');
    if (navProfileBtn) {
        navProfileBtn.addEventListener('click', showProfileModal);
    }
    
    const navAboutBtn = document.getElementById('nav-about');
    if (navAboutBtn) {
        navAboutBtn.addEventListener('click', showAboutModal);
    }

    // Добавляем кнопки голосового ввода
    addVoiceInputButtons();
}

// Статистика использования голосового ввода
const voiceInputStats = {
    recordingStartTime: null,
    recordingLanguage: null,
    
    startRecording: function() {
        this.recordingStartTime = Date.now();
        this.recordingLanguage = getSelectedVoiceLanguage();
        
        // Отправка события в аналитику
        try {
            if (window.analytics) {
                window.analytics.track('Voice Input Started', {
                    language: this.recordingLanguage
                });
            }
        } catch (error) {
            console.error('Ошибка при логировании события голосового ввода', error);
        }
    },
    
    stopRecording: function(success, recognizedText = null) {
        const recordingDuration = (Date.now() - this.recordingStartTime) / 1000;
        
        // Отправка события в аналитику
        try {
            if (window.analytics) {
                window.analytics.track('Voice Input Completed', {
                    language: this.recordingLanguage,
                    duration: recordingDuration,
                    success: success,
                    textLength: recognizedText ? recognizedText.length : 0
                });
            }
        } catch (error) {
            console.error('Ошибка при логировании события голосового ввода', error);
        }
        
        // Сброс статистики
        this.recordingStartTime = null;
        this.recordingLanguage = null;
    }
};

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initApp();
    initEventListeners();
});