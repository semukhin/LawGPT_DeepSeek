// Конфигурация приложения
const config = {
    apiUrl: 'http://127.0.0.1:8000',  // URL API (замените на реальный URL при деплое)
    tokenStorageKey: 'access_token',   // Ключ для хранения токена в localStorage
    tempTokenKey: 'temp_token',        // Ключ для временного токена при регистрации
};

// Инициализация состояния приложения
const state = {
    accessToken: localStorage.getItem(config.tokenStorageKey),
    currentThreadId: null,
    threads: [],
    messages: [],
    isLoading: false,
    selectedFile: null,
    user: null,
    isTyping: false
};

// DOM элементы для авторизации
const authContainer = document.getElementById('auth-container');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const verifyForm = document.getElementById('verify-form');
const forgotPasswordForm = document.getElementById('forgot-password-form');
const resetPasswordForm = document.getElementById('reset-password-form');
const loginFormElement = document.getElementById('login-form-element');
const registerFormElement = document.getElementById('register-form-element');
const verifyFormElement = document.getElementById('verify-form-element');
const forgotPasswordFormElement = document.getElementById('forgot-password-form-element');
const resetPasswordFormElement = document.getElementById('reset-password-form-element');
const showRegisterBtn = document.getElementById('show-register-btn');
const showLoginBtn = document.getElementById('show-login-btn');
const forgotPasswordLink = document.getElementById('forgot-password-link');
const backToLoginBtn = document.getElementById('back-to-login-btn');

// DOM элементы для основного приложения
const mainApp = document.getElementById('main-app');
const createThreadBtn = document.getElementById('create-thread-btn');
const threadsList = document.getElementById('threads-list');
const messagesContainer = document.getElementById('messages-container');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const fileButton = document.getElementById('file-button');
const fileInput = document.getElementById('file-input');
const uploadPreview = document.getElementById('upload-preview');
const fileName = document.getElementById('file-name');
const removeFile = document.getElementById('remove-file');
const currentThreadIdElement = document.getElementById('current-thread-id');
const loadingContainer = document.getElementById('loading-container');
const logoutBtn = document.getElementById('logout-btn');
const profileBtn = document.getElementById('profile-btn');

// Инициализация marked.js для форматирования Markdown
marked.setOptions({
    renderer: new marked.Renderer(),
    highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
    },
    langPrefix: 'hljs language-',
    pedantic: false,
    gfm: true,
    breaks: true,
    sanitize: false,
    smartypants: false,
    xhtml: false
});

// ================ УТИЛИТЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================

/**
 * Показывает индикатор загрузки
 */
function showLoading() {
    state.isLoading = true;
    loadingContainer.style.display = 'flex';
}

/**
 * Скрывает индикатор загрузки
 */
function hideLoading() {
    state.isLoading = false;
    loadingContainer.style.display = 'none';
}

/**
 * Показывает уведомление пользователю
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип уведомления ('success', 'error')
 */
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Удаляем уведомление через 3 секунды
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

/**
 * Форматирует дату в человекочитаемый формат
 * @param {string} dateString - ISO строка даты
 * @returns {string} - Отформатированная дата
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        // Сегодня
        return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
        // Вчера
        return 'Вчера';
    } else {
        // Другие даты
        return date.toLocaleDateString('ru-RU');
    }
}

/**
 * Получает короткое отображаемое имя для треда
 * @param {object} thread - Объект треда
 * @returns {string} - Отображаемое имя треда
 */
function getThreadDisplayName(thread) {
    if (thread.first_message) {
        // Если есть первое сообщение, используем его как название (первые 20 символов)
        const truncatedMessage = thread.first_message.length > 20 
            ? thread.first_message.slice(0, 20) + '...'
            : thread.first_message;
        return truncatedMessage;
    }
    
    // Если нет сообщений, показываем "Без названия"
    return 'Без названия';
}

/**
 * Создает DOM элемент для треда
 * @param {object} thread - Объект треда
 * @returns {HTMLElement} - DOM элемент треда
 */
function createThreadElement(thread) {
    const li = document.createElement('li');
    li.className = `chat-item ${thread.id === state.currentThreadId ? 'active' : ''}`;
    li.dataset.threadId = thread.id;
    
    const displayName = getThreadDisplayName(thread);
    const formattedDate = formatDate(thread.created_at);
    
    li.innerHTML = `
        <i class="fas fa-comments"></i>
        <div class="chat-info">
            <div class="chat-title">${displayName}</div>
            <div class="chat-date">${formattedDate}</div>
        </div>
    `;
    
    li.addEventListener('click', () => selectThread(thread.id));
    
    return li;
}

/**
 * Создает DOM элемент для сообщения
 * @param {object} message - Объект сообщения
 * @returns {HTMLElement} - DOM элемент сообщения
 */
function createMessageElement(message) {
    const div = document.createElement('div');
    div.className = `message message-${message.role}`;
    
    // Форматирование контента с помощью marked.js (Markdown)
    let formattedContent = message.content;
    if (message.role === 'assistant') {
        formattedContent = marked.parse(message.content);
    }
    
    const formattedTime = formatDate(message.created_at);
    
    div.innerHTML = `
        <div class="message-content">${formattedContent}</div>
        <div class="message-time">${formattedTime}</div>
    `;
    
    return div;
}

/**
 * Показывает индикатор "Ассистент печатает"
 */
function showTypingIndicator() {
    if (state.isTyping) return;
    
    state.isTyping = true;
    const div = document.createElement('div');
    div.className = 'message message-assistant typing-indicator';
    div.id = 'typing-indicator';
    div.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Скрывает индикатор "Ассистент печатает"
 */
function hideTypingIndicator() {
    state.isTyping = false;
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// ================ ФУНКЦИИ API ================

/**
 * Выполняет запрос к API
 * @param {string} url - Endpoint URL
 * @param {string} method - Метод запроса (GET, POST и т.д.)
 * @param {any} data - Данные для отправки
 * @param {boolean} isFormData - Флаг, использовать ли FormData
 * @returns {Promise<any>} - Результат запроса
 */
async function apiRequest(url, method, data = null, isFormData = false) {
    try {
        const headers = {};
        
        if (state.accessToken && !isFormData) {
            headers['Authorization'] = `Bearer ${state.accessToken}`;
        }
        
        if (!isFormData && method !== 'GET') {
            headers['Content-Type'] = 'application/json';
        }

        const options = {
            method,
            headers
        };

        if (data) {
            if (isFormData) {
                options.body = data;
                if (state.accessToken) {
                    options.headers['Authorization'] = `Bearer ${state.accessToken}`;
                }
            } else if (method !== 'GET') {
                options.body = JSON.stringify(data);
            }
        }

        const response = await fetch(`${config.apiUrl}/${url}`, options);
        
        // Проверка статуса ответа
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ошибка: ${response.status}`);
        }
        
        // Только для успешных ответов
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

/**
 * Регистрация нового пользователя
 * @param {string} email - Email пользователя
 * @param {string} password - Пароль пользователя
 * @param {string} firstName - Имя пользователя
 * @param {string} lastName - Фамилия пользователя
 */
async function register(email, password, firstName, lastName) {
    showLoading();
    try {
        const data = await apiRequest('register', 'POST', {
            email,
            password,
            first_name: firstName,
            last_name: lastName
        });
        
        // Сохраняем временный токен для верификации
        localStorage.setItem(config.tempTokenKey, data.temp_token);
        
        // Переходим к форме верификации
        showVerifyForm();
        showNotification('Код подтверждения отправлен на вашу почту');
    } catch (error) {
        console.error('Register error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * Верификация аккаунта пользователя
 * @param {number} code - Код подтверждения
 */
async function verify(code) {
    showLoading();
    try {
        const tempToken = localStorage.getItem(config.tempTokenKey);
        if (!tempToken) {
            throw new Error('Токен не найден, попробуйте зарегистрироваться заново');
        }
        
        // Используем временный токен для верификации
        const originalToken = state.accessToken;
        state.accessToken = tempToken;
        
        const data = await apiRequest('verify', 'POST', { code });
        
        // Обновляем токен после верификации
        state.accessToken = data.access_token;
        localStorage.setItem(config.tokenStorageKey, data.access_token);
        localStorage.removeItem(config.tempTokenKey);
        
        // Инициализируем приложение
        initApp();
        showNotification('Регистрация успешно завершена');
    } catch (error) {
        console.error('Verify error:', error);
        state.accessToken = localStorage.getItem(config.tokenStorageKey);
    } finally {
        hideLoading();
    }
}

/**
 * Вход пользователя в систему
 * @param {string} email - Email пользователя
 * @param {string} password - Пароль пользователя
 */
async function login(email, password) {
    showLoading();
    try {
        const data = await apiRequest('login', 'POST', { email, password });
        state.accessToken = data.access_token;
        localStorage.setItem(config.tokenStorageKey, data.access_token);
        
        // Инициализируем приложение
        initApp();
        showNotification('Вы успешно вошли в систему');
    } catch (error) {
        console.error('Login error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * Запрос на восстановление пароля
 * @param {string} email - Email пользователя
 */
async function forgotPassword(email) {
    showLoading();
    try {
        await apiRequest('forgot-password', 'POST', { email });
        showResetPasswordForm();
        
        // Предзаполняем email в форме сброса пароля
        document.getElementById('reset-email').value = email;
        showNotification('Код восстановления отправлен на вашу почту');
    } catch (error) {
        console.error('Forgot password error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * Сброс пароля пользователя
 * @param {string} email - Email пользователя
 * @param {number} code - Код подтверждения
 * @param {string} newPassword - Новый пароль
 */
async function resetPassword(email, code, newPassword) {
    showLoading();
    try {
        await apiRequest('reset-password', 'POST', {
            email,
            code,
            new_password: newPassword
        });
        showLoginForm();
        showNotification('Пароль успешно сброшен. Теперь вы можете войти с новым паролем.');
    } catch (error) {
        console.error('Reset password error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * Выход из системы
 */
async function logout() {
    showLoading();
    try {
        await apiRequest('logout', 'POST');
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Очищаем состояние приложения
        state.accessToken = null;
        localStorage.removeItem(config.tokenStorageKey);
        state.currentThreadId = null;
        state.threads = [];
        state.messages = [];
        state.selectedFile = null;
        
        // Показываем форму входа
        showLoginForm();
        authContainer.style.display = 'flex';
        mainApp.style.display = 'none';
        hideLoading();
        showNotification('Вы вышли из системы');
    }
}

/**
 * Получение списка тредов пользователя
 */
async function getThreads() {
    showLoading();
    try {
        const data = await apiRequest('chat/threads', 'GET');
        // Сохраняем полученные треды
        state.threads = data.threads;
        renderThreads();
    } catch (error) {
        console.error('Get threads error:', error);
        renderThreadsPlaceholder('Ошибка загрузки тредов');
    } finally {
        hideLoading();
    }
}

/**
 * Создание нового треда
 */
async function createThread() {
    showLoading();
    try {
        const data = await apiRequest('create_thread', 'POST');
        
        // Получаем обновленный список тредов
        await getThreads();
        
        // Выбираем новый тред
        selectThread(data.thread_id);
        showNotification('Новый чат создан');
    } catch (error) {
        console.error('Create thread error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * Получение сообщений для текущего треда
 * @param {string} threadId - ID треда
 */
async function getMessages(threadId) {
    if (!threadId) return;
    
    showLoading();
    try {
        const data = await apiRequest(`messages/${threadId}`, 'GET');
        
        // Сохраняем полученные сообщения
        state.messages = data.messages;
        renderMessages();
    } catch (error) {
        console.error('Get messages error:', error);
        renderMessagesPlaceholder('Ошибка загрузки сообщений');
    } finally {
        hideLoading();
    }
}

/**
 * Отправка сообщения в тред
 * @param {string} threadId - ID треда
 * @param {string} query - Текст сообщения
 * @param {File} file - Файл для отправки (опционально)
 */

async function sendMessage(threadId, query, file = null) {
    if ((!query.trim() && !file) || !threadId) {
        showNotification('Введите сообщение или выберите файл', 'error');
        return;
    }

    // Деактивируем кнопку отправки и очищаем поле ввода
    sendButton.disabled = true;
    chatInput.value = '';
    chatInput.style.height = 'auto';
    
    // Отображаем сообщение пользователя
    addMessage({
        role: 'user',
        content: query,
        created_at: new Date().toISOString()
    });
    
    // Если есть файл, показываем его в чате
    if (file) {
        addMessage({
            role: 'user',
            content: `Документ: ${file.name}`,
            created_at: new Date().toISOString()
        });
    }
    
    // Показываем индикатор набора текста ассистентом
    showTypingIndicator();
    
    try {
        let formData = new FormData();
        formData.append('query', query);
        
        if (file) {
            formData.append('file', file);
        }
        
        const data = await apiRequest(`chat/${threadId}`, 'POST', formData, true);
        
        // Скрываем индикатор набора текста
        hideTypingIndicator();
        
        // Если есть recognized_text, показываем его
        if (data.recognized_text) {
            showDocumentText(data.recognized_text);
        }
        
        // Добавляем ответ ассистента
        addMessage({
            role: 'assistant',
            content: data.assistant_response,
            created_at: new Date().toISOString()
        });
        
        // Очищаем выбранный файл
        clearFileSelection();
        
        // Прокручиваем к последнему сообщению
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        hideTypingIndicator();
        console.error('Send message error:', error);
        
        // Добавляем сообщение об ошибке
        addMessage({
            role: 'assistant',
            content: 'Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте еще раз.',
            created_at: new Date().toISOString()
        });
    } finally {
        sendButton.disabled = false;
    }
}
/**
 * Загрузка файла на сервер
 * @param {File} file - Файл для загрузки
 */
async function uploadFile(file) {
    showLoading();
    try {
        let formData = new FormData();
        formData.append('file', file);
        
        const data = await apiRequest('upload_file', 'POST', formData, true);
        showNotification('Файл успешно загружен');
        return data;
    } catch (error) {
        console.error('Upload file error:', error);
        throw error;
    } finally {
        hideLoading();
    }
}

/**
 * Получение данных профиля пользователя
 */
async function getProfile() {
    showLoading();
    try {
        state.user = await apiRequest('profile', 'GET');
    } catch (error) {
        console.error('Get profile error:', error);
    } finally {
        hideLoading();
    }
}

// ================ ФУНКЦИИ РЕНДЕРИНГА UI ================

/**
 * Отображение списка тредов
 */
function renderThreads() {
    threadsList.innerHTML = '';
    
    if (!state.threads || state.threads.length === 0) {
        renderThreadsPlaceholder('Нет чатов');
        return;
    }
    
    // Сортируем треды по дате (от новых к старым)
    const sortedThreads = [...state.threads].sort((a, b) => {
        return new Date(b.created_at) - new Date(a.created_at);
    });
    
    // Добавляем элементы тредов в список
    sortedThreads.forEach(thread => {
        const threadElement = createThreadElement(thread);
        threadsList.appendChild(threadElement);
    });
}

/**
 * Отображение плейсхолдера для списка тредов
 * @param {string} message - Текст плейсхолдера
 */
function renderThreadsPlaceholder(message) {
    threadsList.innerHTML = `
        <li class="chat-item" style="cursor: default;">
            <div class="chat-info">
                <div class="chat-title">${message}</div>
            </div>
        </li>
    `;
}

/**
 * Отображение сообщений текущего треда
 */
function renderMessages() {
    messagesContainer.innerHTML = '';
    
    if (!state.messages || state.messages.length === 0) {
        renderMessagesPlaceholder('Нет сообщений');
        return;
    }
    
    // Добавляем сообщения в контейнер
    state.messages.forEach(message => {
        const messageElement = createMessageElement(message);
        messagesContainer.appendChild(messageElement);
    });
    
    // Прокручиваем к последнему сообщению
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Отображение плейсхолдера для списка сообщений
 * @param {string} message - Текст плейсхолдера
 */
function renderMessagesPlaceholder(message) {
    messagesContainer.innerHTML = `
        <div class="message-placeholder" style="text-align: center; padding: 2rem;">
            ${message}
        </div>
    `;
}

/**
 * Добавление нового сообщения в чат
 * @param {object} message - Объект сообщения
 */
function addMessage(message) {
    // Добавляем сообщение в состояние
    state.messages.push(message);
    
    // Добавляем сообщение в DOM
    const messageElement = createMessageElement(message);
    messagesContainer.appendChild(messageElement);
    
    // Прокручиваем к последнему сообщению
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ================ ФУНКЦИИ ПРИЛОЖЕНИЯ ================

/**
 * Выбор треда
 * @param {string} threadId - ID треда
 */
function selectThread(threadId) {
    // Если тот же тред, ничего не делаем
    if (state.currentThreadId === threadId) return;
    
    // Обновляем активный тред в UI
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.threadId === threadId) {
            item.classList.add('active');
        }
    });
    
    // Обновляем состояние и загружаем сообщения
    state.currentThreadId = threadId;
    currentThreadIdElement.textContent = `ID: ${threadId}`;
    
    // Очищаем текущие сообщения и загружаем новые
    state.messages = [];
    getMessages(threadId);
}

/**
 * Обработка события выбора файла
 * @param {File} file - Выбранный файл
 */
function handleFileSelection(file) {
    if (file) {
        state.selectedFile = file;
        fileName.textContent = file.name;
        uploadPreview.classList.remove('hidden');
        
        // Активируем кнопку отправки
        updateSendButtonState();
    }
}

/**
 * Очистка выбранного файла
 */
function clearFileSelection() {
    state.selectedFile = null;
    fileName.textContent = '';
    uploadPreview.classList.add('hidden');
    fileInput.value = '';
    
    // Проверяем состояние кнопки отправки
    updateSendButtonState();
}

/**
 * Обновление состояния кнопки отправки
 */
function updateSendButtonState() {
    // Включаем кнопку, если есть текст или файл
    sendButton.disabled = !(chatInput.value.trim() || state.selectedFile);
}

/**
 * Автоматическое изменение высоты текстового поля в зависимости от содержимого
 */
function autoResizeTextarea() {
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight > 200 ? 200 : chatInput.scrollHeight) + 'px';
}

/**
 * Показ формы входа
 */
function showLoginForm() {
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
    verifyForm.style.display = 'none';
    forgotPasswordForm.style.display = 'none';
    resetPasswordForm.style.display = 'none';
}

/**
 * Показ формы регистрации
 */
function showRegisterForm() {
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
    verifyForm.style.display = 'none';
    forgotPasswordForm.style.display = 'none';
    resetPasswordForm.style.display = 'none';
}

/**
 * Показ формы верификации
 */
function showVerifyForm() {
    loginForm.style.display = 'none';
    registerForm.style.display = 'none';
    verifyForm.style.display = 'block';
    forgotPasswordForm.style.display = 'none';
    resetPasswordForm.style.display = 'none';
}

/**
 * Показ формы восстановления пароля (запрос)
 */
function showForgotPasswordForm() {
    loginForm.style.display = 'none';
    registerForm.style.display = 'none';
    verifyForm.style.display = 'none';
    forgotPasswordForm.style.display = 'block';
    resetPasswordForm.style.display = 'none';
}

/**
 * Показ формы сброса пароля
 */
function showResetPasswordForm() {
    loginForm.style.display = 'none';
    registerForm.style.display = 'none';
    verifyForm.style.display = 'none';
    forgotPasswordForm.style.display = 'none';
    resetPasswordForm.style.display = 'block';
}

/**
 * Инициализация приложения после успешной аутентификации
 */
function initApp() {
    // Загружаем данные пользователя
    getProfile();
    
    // Скрываем форму входа и показываем основное приложение
    authContainer.style.display = 'none';
    mainApp.style.display = 'block';
    
    // Загружаем список тредов
    getThreads();
}

// ================ ОБРАБОТЧИКИ СОБЫТИЙ ================

// Когда страница загружена
document.addEventListener('DOMContentLoaded', () => {
    // Инициализируем UI в зависимости от состояния авторизации
    if (state.accessToken) {
        initApp();
    } else {
        authContainer.style.display = 'flex';
        mainApp.style.display = 'none';
    }
    
    // === Обработчики форм авторизации ===
    
    // Форма входа
    loginFormElement.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        login(email, password);
    });
    
    // Форма регистрации
    registerFormElement.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const firstName = document.getElementById('register-first-name').value;
        const lastName = document.getElementById('register-last-name').value;
        register(email, password, firstName, lastName);
    });
    
    // Форма верификации
    verifyFormElement.addEventListener('submit', (e) => {
        e.preventDefault();
        const code = parseInt(document.getElementById('verification-code').value);
        verify(code);
    });
    
    // Форма запроса на восстановление пароля
    forgotPasswordFormElement.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('forgot-email').value;
        forgotPassword(email);
    });
    
    // Форма сброса пароля
    resetPasswordFormElement.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('reset-email').value;
        const code = parseInt(document.getElementById('reset-code').value);
        const newPassword = document.getElementById('reset-new-password').value;
        resetPassword(email, code, newPassword);
    });
    
    // Навигация между формами авторизации
    showRegisterBtn.addEventListener('click', showRegisterForm);
    showLoginBtn.addEventListener('click', showLoginForm);
    forgotPasswordLink.addEventListener('click', (e) => {
        e.preventDefault();
        showForgotPasswordForm();
    });
    if (backToLoginBtn) {
        backToLoginBtn.addEventListener('click', showLoginForm);
    }
    
    // === Обработчики событий чата ===
    
    // Создание нового треда
    createThreadBtn.addEventListener('click', async () => {
        // Создаем новый тред
        await createThread();
    });
    
    // Обр