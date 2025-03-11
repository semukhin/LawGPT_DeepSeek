/**
 * LawGPT - Основной файл приложения
 * Обеспечивает функциональность чата с юридическим ассистентом
 * и реализует аутентификацию пользователей
 */

// Конфигурация API
const config = {
    apiUrl: 'http://127.0.0.1:8000',  // Базовый URL API
    apiTimeout: 60000,                // Таймаут запросов (60 секунд)
    storageTokenKey: 'lawgpt_token',  // Ключ для хранения токена в localStorage
    storageThreadKey: 'lawgpt_thread_id', // Ключ для хранения ID текущего треда
    storageTempTokenKey: 'lawgpt_temp_token', // Ключ для временного токена верификации
    markdownEnabled: true,            // Включить обработку Markdown
    autoscrollEnabled: true,          // Автопрокрутка к последнему сообщению
    maxFileSize: 50 * 1024 * 1024,    // Максимальный размер файла (50 MB)
};

// ============================================================
// Инициализация и утилиты
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Инициализация приложения
    initApp();
    
    // Загрузка и инициализация библиотек для обработки Markdown
    if (config.markdownEnabled && window.marked) {
        window.markdown = marked;
        window.markdown.setOptions({
            breaks: true,
            gfm: true
        });
        
        if (window.hljs) {
            window.markdown.setOptions({
                highlight: function(code, lang) {
                    if (lang && window.hljs.getLanguage(lang)) {
                        return window.hljs.highlight(code, {language: lang}).value;
                    }
                    return window.hljs.highlightAuto(code).value;
                }
            });
        }
    }
    
    // Инициализация Mermaid для диаграмм
    if (window.mermaid) {
        mermaid.initialize({
            startOnLoad: false,
            theme: 'dark',
            securityLevel: 'loose'
        });
    }
});

/**
 * Инициализация приложения
 */
function initApp() {
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
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    
    // Обработчики для переключения между формами
    initAuthSwitchers();
}

/**
 * Инициализация обработчиков форм аутентификации
 */
function initAuthForms() {
    // Форма входа
    const loginForm = document.getElementById('login-form');
    loginForm.addEventListener('submit', handleLogin);
    
    // Форма регистрации
    const registerForm = document.getElementById('register-form');
    registerForm.addEventListener('submit', handleRegister);
    
    // Форма верификации
    const verifyForm = document.getElementById('verify-form');
    verifyForm.addEventListener('submit', handleVerify);
    
    // Форма восстановления пароля
    const forgotPasswordForm = document.getElementById('forgot-password-form');
    forgotPasswordForm.addEventListener('submit', handleForgotPassword);
    
    // Форма сброса пароля
    const resetPasswordForm = document.getElementById('reset-password-form');
    resetPasswordForm.addEventListener('submit', handleResetPassword);
    
    // Кнопка повторной отправки кода
    document.getElementById('resend-code').addEventListener('click', handleResendCode);
    
    // Кнопки возврата
    document.getElementById('back-to-login').addEventListener('click', () => showAuthScreen('login-screen'));
    document.getElementById('reset-back-to-login').addEventListener('click', () => showAuthScreen('login-screen'));
    document.getElementById('verify-to-login').addEventListener('click', () => showAuthScreen('login-screen'));
}

/**
 * Инициализация переключателей между формами аутентификации
 */
function initAuthSwitchers() {
    // Переход к регистрации
    document.getElementById('to-register').addEventListener('click', (e) => {
        e.preventDefault();
        showAuthScreen('register-screen');
    });
    
    // Переход к входу
    document.getElementById('to-login').addEventListener('click', (e) => {
        e.preventDefault();
        showAuthScreen('login-screen');
    });
    
    // Переход к восстановлению пароля
    document.getElementById('to-forgot-password').addEventListener('click', (e) => {
        e.preventDefault();
        showAuthScreen('forgot-password-screen');
    });
}

/**
 * Инициализация интерфейса чата
 */
function initChatInterface() {
    // Кнопка нового чата
    document.getElementById('new-chat-btn').addEventListener('click', createNewChat);
    
    // Поле ввода сообщения
    const messageInput = document.getElementById('message-input');
    messageInput.addEventListener('input', () => {
        // Автоматическое изменение высоты поля ввода
        messageInput.style.height = 'auto';
        messageInput.style.height = (messageInput.scrollHeight) + 'px';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
        
        // Активация/деактивация кнопки отправки
        const sendBtn = document.getElementById('send-btn');
        sendBtn.disabled = messageInput.value.trim() === '';
    });
    
    // Отправка сообщения
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (messageInput.value.trim()) {
                const sendBtn = document.getElementById('send-btn');
                sendBtn.click();
            }
        }
    });
    
    // Загрузка файла
    const fileUpload = document.getElementById('file-upload');
    fileUpload.addEventListener('change', handleFileUpload);
    
    // Удаление файла
    document.getElementById('remove-file-btn').addEventListener('click', removeUploadedFile);
    
    // Обработчики для модальных окон
    document.getElementById('nav-profile').addEventListener('click', showProfileModal);
    document.getElementById('nav-about').addEventListener('click', showAboutModal);
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
            messagesContainer.innerHTML = '';
            
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
    }
}

/**
 * Отображает список чатов в боковой панели
 * @param {Array} threads - Массив объектов с данными чатов
 */
function renderChatThreads(threads) {
    const chatList = document.getElementById('chat-list');
    chatList.innerHTML = '';
    
    if (threads.length === 0) {
        const emptyItem = document.createElement('li');
        emptyItem.className = 'chat-item empty';
        emptyItem.textContent = 'У вас пока нет активных чатов.';
        chatList.appendChild(emptyItem);
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
        
        // Добавляем контент чата
        chatItem.innerHTML = `
            <div class="chat-info">
                <div class="chat-title">${thread.first_message || 'Новый чат'}</div>
                <div class="chat-date">${formattedDate}</div>
            </div>
        `;
        
        // Обработчик клика
        chatItem.addEventListener('click', () => {
            selectChatThread(thread.id);
        });
        
        chatList.appendChild(chatItem);
    });
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
    document.getElementById('current-chat-id').textContent = threadId;
    
    // Очищаем контейнер сообщений
    const messagesContainer = document.getElementById('messages-container');
    messagesContainer.innerHTML = '';
    
    // Загружаем сообщения данного чата
    await loadChatMessages(threadId);
}

/**
 * Загружает сообщения выбранного чата
 * @param {string} threadId - ID треда чата
 */
async function loadChatMessages(threadId) {
    try {
        console.log(`Загрузка сообщений для треда ${threadId}`); // Для отладки
        const response = await apiRequest(`/messages/${threadId}`, 'GET');
        
        if (response.messages && Array.isArray(response.messages)) {
            renderChatMessages(response.messages);
        }
    } catch (error) {
        console.error('Ошибка при загрузке сообщений:', error);
        showNotification('Не удалось загрузить сообщения чата', 'error');
    }
}

/**
 * Отображает сообщения чата
 * @param {Array} messages - Массив объектов с сообщениями
 */
function renderChatMessages(messages) {
    const messagesContainer = document.getElementById('messages-container');
    messagesContainer.innerHTML = '';
    
    if (messages.length === 0) {
        // Если сообщений нет, показываем приветственное сообщение
        addAssistantMessage('Здравствуйте! Я юридический ассистент LawGPT. Чем я могу вам помочь?');
        return;
    }
    
    // Добавляем все сообщения
    messages.forEach(message => {
        if (message.role === 'user') {
            addUserMessage(message.content);
        } else if (message.role === 'assistant') {
            addAssistantMessage(message.content);
        }
    });
    
    // Прокручиваем к последнему сообщению
    scrollToBottom();
}

 /**
 * Отправляет сообщение пользователя
 */
async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const fileUpload = document.getElementById('file-upload');
    const text = messageInput.value.trim();
    const file = fileUpload.files[0];
    
    // Если нет ни текста, ни файла - выходим
    if (!text && !file) {
        return;
    }
    
    // Получаем ID текущего треда
    const threadId = localStorage.getItem(config.storageThreadKey);
    if (!threadId) {
        showNotification('Ошибка: чат не выбран', 'error');
        return;
    }
    
    // Добавляем сообщение пользователя в чат
    addUserMessage(text);
    
    // Очищаем поле ввода
    messageInput.value = '';
    messageInput.style.height = 'auto';
    document.getElementById('send-btn').disabled = true;
    
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
    
    try {
        console.log(`Отправка сообщения в тред ${threadId}`); // Для отладки
        const response = await apiRequestFormData(`/chat/${threadId}`, formData);
        
        // Скрываем индикатор набора текста
        hideTypingIndicator();
        
        if (response.assistant_response) {
            // Добавляем ответ ассистента
            addAssistantMessage(response.assistant_response);
            
            // Если был загружен файл, показываем информацию о распознанном тексте
            if (response.recognized_text) {
                const infoMessage = document.createElement('div');
                infoMessage.className = 'message message-system';
                infoMessage.innerHTML = `
                    <div class="message-content">
                        <div class="file-info">
                            <i class="fas fa-file-alt"></i>
                            <span>Файл обработан: ${response.file_name}</span>
                        </div>
                    </div>
                `;
                document.getElementById('messages-container').appendChild(infoMessage);
            }
        } else {
            showNotification('Ошибка: не получен ответ от ассистента', 'error');
        }
    } catch (error) {
        hideTypingIndicator();
        showNotification(`Ошибка при отправке сообщения: ${error.message}`, 'error');
        console.error('Ошибка при отправке сообщения:', error);
    }
    
    // Прокручиваем к последнему сообщению
    scrollToBottom();
}

/**
 * Добавляет сообщение пользователя в чат
 * @param {string} text - Текст сообщения
 */
function addUserMessage(text) {
    const template = document.getElementById('message-template');
    const messageElement = template.content.cloneNode(true).querySelector('.message');
    
    messageElement.classList.add('message-user');
    
    const contentElement = messageElement.querySelector('.message-content');
    contentElement.textContent = text;
    
    const timeElement = messageElement.querySelector('.message-time');
    timeElement.textContent = getCurrentTime();
    
    document.getElementById('messages-container').appendChild(messageElement);
    scrollToBottom();
}

/**
 * Добавляет сообщение ассистента в чат
 * @param {string} text - Текст сообщения
 */
function addAssistantMessage(text) {
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
    
    document.getElementById('messages-container').appendChild(messageElement);
    
    // Инициализируем специальные компоненты в сообщении
    if (window.MarkdownProcessor) {
        MarkdownProcessor.processMessage(messageElement);
    }
    
    scrollToBottom();
}

/**
 * Показывает индикатор набора текста ассистентом
 */
function showTypingIndicator() {
    const template = document.getElementById('typing-indicator-template');
    const indicator = template.content.cloneNode(true);
    
    const container = document.createElement('div');
    container.className = 'message message-assistant';
    container.id = 'typing-indicator-container';
    container.appendChild(indicator);
    
    document.getElementById('messages-container').appendChild(container);
    scrollToBottom();
}

/**
 * Скрывает индикатор набора текста
 */
function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator-container');
    if (indicator) {
        indicator.remove();
    }
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
    const fileType = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!allowedTypes.includes(fileType)) {
        showNotification('Поддерживаются только файлы PDF и Word (.pdf, .doc, .docx)', 'error');
        e.target.value = '';
        return;
    }
    
    // Показываем предпросмотр файла
    const fileNameElement = document.getElementById('file-name');
    fileNameElement.textContent = file.name;
    
    document.getElementById('upload-preview').classList.remove('hidden');
    
    // Активируем кнопку отправки
    document.getElementById('send-btn').disabled = false;
}

/**
 * Удаляет загруженный файл
 */
function removeUploadedFile() {
    document.getElementById('file-upload').value = '';
    document.getElementById('upload-preview').classList.add('hidden');
    
    // Проверяем статус кнопки отправки
    const messageInput = document.getElementById('message-input');
    document.getElementById('send-btn').disabled = messageInput.value.trim() === '';
}

/**
 * Загружает профиль пользователя
 */
async function loadUserProfile() {
    try {
        const response = await apiRequest('/profile', 'GET');
        
        if (response) {
            const userName = `${response.first_name} ${response.last_name}`;
            document.getElementById('user-name').textContent = userName;
        }
    } catch (error) {
        console.error('Ошибка при загрузке профиля:', error);
    }
}

/**
 * Прокручивает контейнер сообщений к последнему сообщению
 */
function scrollToBottom() {
    if (!config.autoscrollEnabled) return;
    
    const messagesContainer = document.getElementById('messages-container');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ============================================================
// Функции для работы с интерфейсом
// ============================================================

/**
 * Переключает видимость между основным приложением и экранами аутентификации
 * @param {boolean} showAppScreen - true для показа основного приложения, false для экранов аутентификации
 */
function toggleAppVisibility(showAppScreen) {
    const authScreens = document.getElementById('auth-screens');
    const mainApp = document.getElementById('main-app');
    
    if (showAppScreen) {
        authScreens.style.display = 'none';
        mainApp.style.display = 'flex';
    } else {
        mainApp.style.display = 'none';
        authScreens.style.display = 'flex';
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
        if (id === screenId) {
            screen.style.display = 'block';
        } else {
            screen.style.display = 'none';
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
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    
    // Автоматически скрываем уведомление через 3 секунды
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

/**
 * Показывает индикатор загрузки
 */
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

/**
 * Скрывает индикатор загрузки
 */
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
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
        headers: headers,
        timeout: config.apiTimeout
    };
    
    // Добавляем тело запроса для методов, которые его поддерживают
    if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${config.apiUrl}${endpoint}`, options);
        
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
            
            throw new Error(errorText);
        }
        
        // Парсим ответ как JSON
        const data = await response.json();
        return data;
    } catch (error) {
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
    const token = localStorage.getItem(config.storageTokenKey);
    
    // Формируем заголовки запроса (без Content-Type, он будет установлен автоматически для FormData)
    const headers = {};
    
    // Добавляем заголовок авторизации, если есть токен
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(`${config.apiUrl}${endpoint}`, {
            method: 'POST',
            headers: headers,
            body: formData,
            timeout: config.apiTimeout
        });
        
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
            
            throw new Error(errorText);
        }
        
        // Парсим ответ как JSON
        const data = await response.json();
        return data;
    } catch (error) {
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
        // Используем существующий метод register вместо несуществующего resend-code
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
        localStorage.removeItem(config.storageTokenKey);
        localStorage.removeItem(config.storageThreadKey);
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
        
        document.body.appendChild(modal);
    }
    
    // Загружаем данные профиля
    apiRequest('/profile', 'GET')
        .then(data => {
            modal.innerHTML = `
                <div class="modal-content">
                    <span class="close-modal">&times;</span>
                    <h2>Профиль пользователя</h2>
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
            modal.querySelector('.close-modal').addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            // Показываем модальное окно
            modal.style.display = 'block';
        })
        .catch(error => {
            showNotification(`Ошибка загрузки профиля: ${error.message}`, 'error');
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
        
        document.body.appendChild(modal);
    }
    
    // Заполняем содержимое
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-modal">&times;</span>
            <h2>О сервисе LawGPT</h2>
            <p>Приветствуем вас на странице сервиса юридического ассистента LawGPT!</p>
            <p>LawGPT — это интеллектуальный помощник, специализирующийся на российском законодательстве и юридических вопросах.</p>
            <p>Наш сервис помогает быстро получать ответы на сложные юридические вопросы, обращаясь к актуальной базе российского законодательства.</p>
            
            <div class="social-links">
                <h3>VK | Telegram</h3>
                <a href="#" target="_blank" class="social-link"><i class="fab fa-vk"></i> ВКонтакте</a>
                <a href="#" target="_blank" class="social-link"><i class="fab fa-telegram"></i> Telegram</a>
            </div>
        </div>
    `;
    
    // Обработчик для закрытия
    modal.querySelector('.close-modal').addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    // Показываем модальное окно
    modal.style.display = 'block';
}

/**
 * Инициализация мобильного меню
 */
function initMobileMenu() {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    let isMenuOpen = false;

    // Функция открытия/закрытия меню
    function toggleMenu(open) {
        isMenuOpen = open;
        sidebar.classList.toggle('active', open);
        overlay.classList.toggle('active', open);
        document.body.style.overflow = open ? 'hidden' : '';
    }

    // Обработчик кнопки меню
    menuToggle.addEventListener('click', () => {
        toggleMenu(!isMenuOpen);
    });

    // Закрытие меню при клике на оверлей
    overlay.addEventListener('click', () => {
        toggleMenu(false);
    });

    // Закрытие меню при выборе чата
    document.addEventListener('click', (e) => {
        const chatItem = e.target.closest('.chat-item');
        if (chatItem && window.innerWidth <= 768) {
            toggleMenu(false);
        }
    });

    // Закрытие меню при изменении ориентации устройства
    window.addEventListener('orientationchange', () => {
        if (isMenuOpen) {
            toggleMenu(false);
        }
    });

    // Закрытие меню при ресайзе окна больше 768px
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && isMenuOpen) {
            toggleMenu(false);
        }
    });
}

