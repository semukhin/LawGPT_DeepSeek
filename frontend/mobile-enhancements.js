/**
 * Улучшения интерфейса для мобильных устройств
 */

// Проверка на мобильное устройство
function isMobile() {
    return window.innerWidth <= 768;
}

// Инициализация улучшений для мобильных устройств
function initMobileEnhancements() {
    // Инициализируем свайп для меню
    initSwipeGestures();
    
    // Инициализируем pull-to-refresh
    initPullToRefresh();
    
    // Оптимизация для виртуальной клавиатуры
    initKeyboardOptimization();
    
    // Ленивая загрузка истории сообщений
    initLazyMessageLoading();
    
    // Оптимизация изображений и медиа
    initMediaOptimization();
    
    // Добавляем индикатор свайпа
    addSwipeIndicator();

    // Добавляем обработку клика на весь элемент chat-item
    enhanceChatItemClickability();

    // Оптимизируем анимации для слабых устройств
    if (isLowPowerDevice()) {
        optimizeForLowPowerDevices();
    }
}

/**
 * Инициализация свайп-жестов для открытия/закрытия меню
 */
function initSwipeGestures() {
    const chatContainer = document.querySelector('.chat-container');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    let touchStartX = 0;
    let touchEndX = 0;
    
    // Настройка минимального расстояния свайпа
    const minSwipeDistance = 50;
    
    // Обработчик начала касания
    chatContainer.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    // Обработчик окончания касания
    chatContainer.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
    
    // Функция обработки свайпа
    function handleSwipe() {
        const swipeDistance = touchEndX - touchStartX;
        
        // Свайп вправо - открываем меню
        if (swipeDistance > minSwipeDistance && touchStartX < 50) {
            toggleMenu(true);
        }
    }
    
    // Свайп для закрытия меню
    overlay.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    overlay.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        const swipeDistance = touchStartX - touchEndX;
        
        // Свайп влево - закрываем меню
        if (swipeDistance > minSwipeDistance) {
            toggleMenu(false);
        }
    }, { passive: true });

    // Глобальная функция для переключения меню
    window.toggleMenu = function(open) {
        sidebar.classList.toggle('active', open);
        overlay.classList.toggle('active', open);
        document.body.style.overflow = open ? 'hidden' : '';
    };
}

/**
 * Инициализация pull-to-refresh для списка чатов
 */
function initPullToRefresh() {
    const chatList = document.getElementById('chat-list');
    let touchStartY = 0;
    let touchEndY = 0;
    let isRefreshing = false;
    
    // Минимальное расстояние для активации обновления
    const minPullDistance = 70;
    
    // Обработчик начала касания
    chatList.addEventListener('touchstart', (e) => {
        // Проверяем, что скролл в начале списка
        if (chatList.scrollTop === 0) {
            touchStartY = e.changedTouches[0].screenY;
            
            // Создаем индикатор, если его еще нет
            if (!document.querySelector('.pull-indicator')) {
                const indicator = document.createElement('div');
                indicator.className = 'pull-indicator';
                indicator.textContent = 'Потяните вниз для обновления';
                chatList.prepend(indicator);
            }
        }
    }, { passive: true });
    
    // Обработчик движения пальца
    chatList.addEventListener('touchmove', (e) => {
        if (touchStartY > 0 && !isRefreshing) {
            touchEndY = e.changedTouches[0].screenY;
            const pullDistance = touchEndY - touchStartY;
            
            if (pullDistance > 0) {
                // Предотвращаем стандартное поведение скролла
                e.preventDefault();
                
                const indicator = document.querySelector('.pull-indicator');
                if (indicator) {
                    if (pullDistance > minPullDistance) {
                        indicator.textContent = 'Отпустите для обновления';
                    } else {
                        indicator.textContent = 'Потяните вниз для обновления';
                    }
                }
            }
        }
    }, { passive: false });
    
    // Обработчик окончания касания
    chatList.addEventListener('touchend', (e) => {
        if (touchStartY > 0) {
            touchEndY = e.changedTouches[0].screenY;
            const pullDistance = touchEndY - touchStartY;
            
            // Если достаточное расстояние, запускаем обновление
            if (pullDistance > minPullDistance) {
                refreshChatList();
            } else {
                const indicator = document.querySelector('.pull-indicator');
                if (indicator) {
                    indicator.remove();
                }
            }
            
            // Сбрасываем значения
            touchStartY = 0;
            touchEndY = 0;
        }
    }, { passive: true });
    
    // Функция обновления списка чатов
    function refreshChatList() {
        isRefreshing = true;
        
        const indicator = document.querySelector('.pull-indicator');
        if (indicator) {
            indicator.textContent = 'Обновление...';
        }
        
        // Вызываем функцию загрузки чатов
        loadChatThreads()
            .then(() => {
                if (indicator) {
                    indicator.textContent = 'Обновлено!';
                    
                    // Удаляем индикатор через небольшую задержку
                    setTimeout(() => {
                        indicator.remove();
                        isRefreshing = false;
                    }, 1000);
                }
            })
            .catch((error) => {
                console.error('Ошибка при обновлении чатов:', error);
                if (indicator) {
                    indicator.textContent = 'Ошибка обновления';
                    
                    setTimeout(() => {
                        indicator.remove();
                        isRefreshing = false;
                    }, 1000);
                }
            });
    }
}

/**
 * Оптимизация для виртуальной клавиатуры
 */
function initKeyboardOptimization() {
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('messages-container');
    
    // Фокус на input
    messageInput.addEventListener('focus', () => {
        if (isMobile()) {
            // Даем небольшую задержку для открытия клавиатуры
            setTimeout(() => {
                // Прокручиваем к нижней части чата
                scrollToBottom();
                
                // Прокручиваем страницу, чтобы убедиться, что поле ввода видно
                messageInput.scrollIntoView({ behavior: 'smooth' });
            }, 300);
        }
    });
    
    // Обработка изменения размера окна (например, при появлении клавиатуры)
    let windowHeight = window.innerHeight;
    
    window.addEventListener('resize', () => {
        // Если высота окна значительно изменилась, вероятно, появилась клавиатура
        if (isMobile() && Math.abs(window.innerHeight - windowHeight) > 150) {
            setTimeout(() => {
                scrollToBottom();
                messageInput.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        }
        
        // Обновляем текущую высоту
        windowHeight = window.innerHeight;
    });
}

/**
 * Реализация ленивой загрузки сообщений
 */
function initLazyMessageLoading() {
    const messagesContainer = document.getElementById('messages-container');
    
    // Состояние для ленивой загрузки
    let lazyLoadState = {
        isLoading: false,
        hasMoreMessages: true,
        currentPage: 1,
        messagesPerPage: 20,
        threadId: null
    };
    
    // Обработчик прокрутки контейнера сообщений
    messagesContainer.addEventListener('scroll', () => {
        // Если прокрутили близко к верху и есть еще сообщения для загрузки
        if (messagesContainer.scrollTop < 100 && !lazyLoadState.isLoading && lazyLoadState.hasMoreMessages) {
            loadMoreMessages();
        }
    });
    
    // Модифицируем существующую функцию загрузки сообщений
    const originalLoadChatMessages = window.loadChatMessages;
    
    window.loadChatMessages = async function(threadId) {
        // Сбрасываем состояние
        lazyLoadState.isLoading = false;
        lazyLoadState.hasMoreMessages = true;
        lazyLoadState.currentPage = 1;
        lazyLoadState.threadId = threadId;
        
        // Вызываем оригинальную функцию
        return originalLoadChatMessages(threadId);
    };
    
    // Функция загрузки дополнительных сообщений
    async function loadMoreMessages() {
        if (!lazyLoadState.threadId) return;
        
        lazyLoadState.isLoading = true;
        
        // Добавляем индикатор загрузки
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'message-loading';
        loadingIndicator.innerHTML = '<div class="message-loading-spinner"></div>';
        messagesContainer.prepend(loadingIndicator);
        
        // Запоминаем текущую позицию прокрутки
        const scrollHeight = messagesContainer.scrollHeight;
        
        try {
            // Загружаем следующую страницу сообщений
            const params = `?page=${++lazyLoadState.currentPage}&limit=${lazyLoadState.messagesPerPage}`;
            const response = await apiRequest(`/messages/${lazyLoadState.threadId}${params}`, 'GET');
            
            if (response.messages && Array.isArray(response.messages)) {
                if (response.messages.length > 0) {
                    // Добавляем сообщения в начало (они идут в обратном порядке)
                    const oldestMessages = response.messages.reverse();
                    
                    // Создаем фрагмент для более эффективной вставки
                    const fragment = document.createDocumentFragment();
                    
                    oldestMessages.forEach(message => {
                        if (message.role === 'user') {
                            const messageElement = createUserMessageElement(message.content);
                            fragment.appendChild(messageElement);
                        } else if (message.role === 'assistant') {
                            const messageElement = createAssistantMessageElement(message.content);
                            fragment.appendChild(messageElement);
                        }
                    });
                    
                    // Удаляем индикатор загрузки
                    loadingIndicator.remove();
                    
                    // Вставляем сообщения в начало
                    messagesContainer.prepend(fragment);
                    
                    // Восстанавливаем позицию прокрутки
                    messagesContainer.scrollTop = messagesContainer.scrollHeight - scrollHeight;
                } else {
                    // Если сообщений больше нет
                    lazyLoadState.hasMoreMessages = false;
                    loadingIndicator.remove();
                }
            } else {
                lazyLoadState.hasMoreMessages = false;
                loadingIndicator.remove();
            }
        } catch (error) {
            console.error('Ошибка при загрузке дополнительных сообщений:', error);
            loadingIndicator.remove();
        }
        
        lazyLoadState.isLoading = false;
    }
    
    // Вспомогательные функции для создания элементов сообщений
    function createUserMessageElement(text) {
        const template = document.getElementById('message-template');
        const messageElement = template.content.cloneNode(true).querySelector('.message');
        
        messageElement.classList.add('message-user');
        
        const contentElement = messageElement.querySelector('.message-content');
        contentElement.textContent = text;
        
        const timeElement = messageElement.querySelector('.message-time');
        timeElement.textContent = getCurrentTime();
        
        return messageElement;
    }
    
    function createAssistantMessageElement(text) {
        const template = document.getElementById('message-template');
        const messageElement = template.content.cloneNode(true).querySelector('.message');
        
        messageElement.classList.add('message-assistant');
        
        const contentElement = messageElement.querySelector('.message-content');
        
        // Если включена обработка Markdown и библиотека загружена
        if (config.markdownEnabled && window.markdown) {
            contentElement.innerHTML = window.markdown.parse(text);
        } else {
            contentElement.textContent = text;
        }
        
        const timeElement = messageElement.querySelector('.message-time');
        timeElement.textContent = getCurrentTime();
        
        return messageElement;
    }
}

/**
 * Оптимизация изображений и медиа-контента
 */
function initMediaOptimization() {
    // Отложенная загрузка изображений
    if ('loading' in HTMLImageElement.prototype) {
        // Используем нативную ленивую загрузку браузера
        document.querySelectorAll('img:not([loading])').forEach(img => {
            img.loading = 'lazy';
        });
    } else {
        // Для старых браузеров можно использовать IntersectionObserver
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        observer.unobserve(img);
                    }
                });
            });
            
            // Применяем ко всем изображениям с data-src
            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }
    
    // Устанавливаем меньшее качество canvas для экономии ресурсов
    document.querySelectorAll('canvas').forEach(canvas => {
        const context = canvas.getContext('2d');
        if (context && typeof context.imageSmoothingQuality === 'string') {
            context.imageSmoothingQuality = isMobile() ? 'low' : 'medium';
        }
    });
}

/**
 * Добавляет индикатор свайпа в мобильном режиме
 */
function addSwipeIndicator() {
    if (isMobile()) {
        const chatContainer = document.querySelector('.chat-container');
        
        // Проверяем, не создан ли уже индикатор
        if (!document.querySelector('.swipe-indicator')) {
            const indicator = document.createElement('div');
            indicator.className = 'swipe-indicator';
            chatContainer.appendChild(indicator);
            
            // Скрываем индикатор после нескольких показов
            let showCount = 0;
            
            // Показываем индикатор на короткое время при каждой загрузке сообщений
            const originalRenderMessages = window.renderChatMessages;
            
            window.renderChatMessages = function(messages) {
                // Вызываем оригинальную функцию
                originalRenderMessages(messages);
                
                // Показываем индикатор
                if (showCount < 3) {
                    indicator.style.opacity = '0.7';
                    
                    // Скрываем через 3 секунды
                    setTimeout(() => {
                        indicator.style.opacity = '0';
                    }, 3000);
                    
                    showCount++;
                }
            };
        }
    }
}

/**
 * Улучшает кликабельность элементов чата на сенсорных устройствах
 */
function enhanceChatItemClickability() {
    const chatList = document.getElementById('chat-list');
    
    // Делегирование события для текущих и будущих элементов
    chatList.addEventListener('click', (e) => {
        // Находим ближайший родительский элемент chat-item
        const chatItem = e.target.closest('.chat-item');
        
        // Если клик был по элементу внутри chat-item, но не по самому chat-item
        if (chatItem && e.target !== chatItem) {
            // Эмулируем клик по chat-item
            const threadId = chatItem.dataset.threadId;
            if (threadId) {
                selectChatThread(threadId);
            }
        }
    });
}

/**
 * Проверяет, является ли устройство маломощным
 */
function isLowPowerDevice() {
    // Проверка на количество логических процессоров
    if (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 4) {
        return true;
    }
    
    // Проверка на мобильное устройство
    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        // Дополнительная проверка на старые устройства
        if (
            /iPhone OS [1-9]_|iPad.*OS [1-9]_|Android [1-5]\./.test(navigator.userAgent) ||
            (navigator.deviceMemory && navigator.deviceMemory < 2)
        ) {
            return true;
        }
    }
    
    return false;
}

/**
 * Оптимизирует интерфейс для маломощных устройств
 */
function optimizeForLowPowerDevices() {
    // Отключаем анимации или делаем их проще
    document.body.classList.add('reduce-motion');
    
    // Добавляем стили для отключения тяжелых анимаций
    const style = document.createElement('style');
    style.textContent = `
        .reduce-motion * {
            transition-duration: 0ms !important;
            animation-duration: 0ms !important;
        }
        
        .reduce-motion .loading-spinner {
            animation: spin 1.5s linear infinite !important;
        }
    `;
    document.head.appendChild(style);
    
    // Ограничиваем количество загружаемых сообщений
    if (window.lazyLoadState) {
        window.lazyLoadState.messagesPerPage = 10;
    }
    
    // Отключаем некоторые тяжелые возможности
    if (window.config) {
        window.config.autoscrollEnabled = false; // Отключаем автоскролл для экономии ресурсов
    }
}

// Запускаем улучшения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Проверяем, загружено ли приложение на мобильном устройстве
    if (isMobile()) {
        initMobileEnhancements();
    }

    // Обрабатываем переключение на мобильную ориентацию
    window.addEventListener('resize', () => {
        if (isMobile() && !window.mobileEnhancementsInitialized) {
            initMobileEnhancements();
            window.mobileEnhancementsInitialized = true;
        }
    });
});