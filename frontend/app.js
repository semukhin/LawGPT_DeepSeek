/**
 * LawGPT - Основной файл приложения
 * Интегрированная версия с мобильными улучшениями
 * @version 2.0.0
 * @date 2024-03-14
 */

console.log('LawGPT Frontend загружен');

// Конфигурация приложения
const config = {
    apiUrl: '/api',
    apiTimeout: 60000,
    storageTokenKey: 'lawgpt_token',
    storageThreadKey: 'lawgpt_thread_id',
    storageTempTokenKey: 'lawgpt_temp_token',
    markdownEnabled: true,
    autoscrollEnabled: true,
    maxFileSize: 50 * 1024 * 1024,
    mobileBreakpoint: 768 // Точка перехода для мобильных устройств
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
 * Инициализация свайп-жестов для мобильных устройств
 */
function initSwipeGestures() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log('Инициализация свайп-жестов');
}

/**
 * Инициализация pull-to-refresh для обновления списка чатов
 */
function initPullToRefresh() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log('Инициализация pull-to-refresh');
}

/**
 * Оптимизация клавиатуры для мобильных устройств
 */
function initKeyboardOptimization() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log('Инициализация оптимизации клавиатуры');
}

/**
 * Инициализация ленивой загрузки сообщений
 */
function initLazyMessageLoading() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log('Инициализация ленивой загрузки сообщений');
}

/**
 * Оптимизация для маломощных устройств
 */
function optimizeForLowPowerDevices() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log('Оптимизация для маломощных устройств');
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
        document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
    });
    
    // Закрытие меню при клике на оверлей
    overlay.addEventListener('click', function() {
        console.log('Клик по оверлею');
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        menuToggle.classList.remove('active');
        document.body.style.overflow = '';
    });
    
    // Закрытие меню при выборе чата на мобильных устройствах
    document.addEventListener('click', function(e) {
        const chatItem = e.target.closest('.chat-item');
        if (chatItem && window.innerWidth <= 768) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
            menuToggle.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
    
    console.log('Мобильное меню инициализировано успешно');
}

/**
 * Инициализация мобильных улучшений
 * Централизованный метод для настройки мобильного интерфейса
 */
function initMobileEnhancements() {
    if (isMobile()) {
        console.log('🚀 Инициализация мобильных улучшений');
        
        initSwipeGestures();
        initPullToRefresh();
        initKeyboardOptimization();
        initLazyMessageLoading();
        
        if (isLowPowerDevice()) {
            console.log('⚡ Оптимизация для маломощных устройств');
            optimizeForLowPowerDevices();
        }
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
            <p>LawGPT — это интеллектуальный помощник, специализирующийся на российском законодательстве.</p>
            <p>Наш сервис помогает получать ответы на  юридические вопросы, обращаясь к актуальной базе российского законодательства
            <p>и судебной практики.</p>
            <p>В настоящее вермя сервис имеет RAG c почти полной базой российского законодательства.</p>
            <p>Пополяется база судебных решений и обзоров судебной практики.</p>
            <p>Приглашаем вас принять участие в развитии сервиса, предлагая свои идеи и предложения 
            <p>на почту <a href="mailto:info@lawgpt.ru">info@lawgpt.ru</a>.</p>
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
    
    // Обработчик для закрытия
    modal.querySelector('.close-modal').addEventListener('click', () => {
        modal.style.display = 'none';
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
    const currentChatId = document.getElementById('current-chat-id');
    if (currentChatId) {
        currentChatId.textContent = threadId;
    }
    
    // Очищаем контейнер сообщений
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        messagesContainer.innerHTML = '';
    }
    
    // Загружаем сообщения данного чата
    await loadChatMessages(threadId);
}

/**
 * Загружает сообщения выбранного чата
 * @param {string} threadId - ID треда чата
 */
async function loadChatMessages(threadId) {
    try {
        console.log(`Загрузка сообщений для треда ${threadId}`);
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
            
            // Передаем обработанные сообщения функции рендеринга
            renderChatMessages(formattedMessages);
        }
    } catch (error) {
        console.error('Ошибка при загрузке сообщений:', error);
        showNotification('Не удалось загрузить сообщения чата', 'error');
    }
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
    
    if (messages.length === 0) {
        // Если сообщений нет, показываем приветственное сообщение
        addAssistantMessage('Здравствуйте! Я юридический ассистент LawGPT. Чем я могу вам помочь?');
        return;
    }
    
    // Добавляем все сообщения с сохранением временных меток
    messages.forEach(message => {
        // Преобразуем строку с датой в объект Date
        const timestamp = message.created_at ? new Date(message.created_at) : new Date();
        
        if (message.role === 'user') {
            addUserMessage(message.content, timestamp);
        } else if (message.role === 'assistant') {
            addAssistantMessage(message.content, timestamp);
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
    processingSteps.forEach(step => {
        setTimeout(() => {
            // Проверяем, что индикатор всё ещё отображается
            const indicator = document.getElementById('typing-indicator-container');
            if (indicator) {
                updateTypingIndicator(step.message);
            }
        }, step.delay);
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
                
                // Добавляем системному сообщению ту же временную метку
                infoMessage.dataset.timestamp = assistantTimestamp.getTime();
                
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
    
    // Создаем или обновляем текстовый элемент
    let statusText = typingContainer.querySelector('.typing-status');
    if (!statusText) {
        statusText = document.createElement('div');
        statusText.className = 'typing-status';
        statusText.style.marginLeft = '10px';
        statusText.style.fontSize = '12px';
        statusText.style.color = 'rgba(255, 255, 255, 0.7)';
        
        // Добавляем текст после индикатора с точками
        const indicator = typingContainer.querySelector('.typing-indicator');
        if (indicator) {
            typingContainer.appendChild(statusText);
        } 
    }
    
    // Обновляем текст
    statusText.textContent = message;
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
        
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        contentElement.textContent = text;
        
        const timeElement = document.createElement('div');
        timeElement.className = 'message-time';
        
        // Используем переданную или созданную временную метку
        const dateStr = timestamp.toLocaleDateString('ru-RU');
        const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
        
        // Создаем и добавляем элемент даты
        const dateSpan = document.createElement('span');
        dateSpan.className = 'message-date';
        dateSpan.textContent = dateStr;
        
        timeElement.appendChild(dateSpan);
        timeElement.appendChild(document.createTextNode(timeStr));
        
        // Сохраняем временную метку в атрибуте data-timestamp
        messageElement.dataset.timestamp = timestamp.getTime();
        
        // Собираем элемент сообщения
        messageElement.appendChild(contentElement);
        messageElement.appendChild(timeElement);
        
        // Добавляем в контейнер сообщений
        messagesContainer.appendChild(messageElement);
        scrollToBottom();
        return;
    }
    
    // Если шаблон найден, используем его
    const messageElement = template.content.cloneNode(true).querySelector('.message');
    
    messageElement.classList.add('message-user');
    
    const contentElement = messageElement.querySelector('.message-content');
    contentElement.textContent = text;
    
    const timeElement = messageElement.querySelector('.message-time');
    
    // Используем переданную или созданную временную метку
    const dateStr = timestamp.toLocaleDateString('ru-RU');
    const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
    
    // Создаем элемент для даты
    const dateSpan = document.createElement('span');
    dateSpan.className = 'message-date';
    dateSpan.textContent = dateStr;
    
    // Сохраняем временную метку в атрибуте data-timestamp
    messageElement.dataset.timestamp = timestamp.getTime();
    
    // Добавляем дату и время в элемент времени
    timeElement.appendChild(dateSpan);
    timeElement.appendChild(document.createTextNode(timeStr));
    
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
        
        const contentElement = document.createElement('div');
        contentElement.className = 'message-content';
        
        // Если включена обработка Markdown и библиотека загружена
        if (config.markdownEnabled && window.markdown) {
            contentElement.innerHTML = window.markdown.parse(text);
        } else {
            contentElement.textContent = text;
        }
        
        const timeElement = document.createElement('div');
        timeElement.className = 'message-time';
        
        // Используем переданную или созданную временную метку
        const dateStr = timestamp.toLocaleDateString('ru-RU');
        const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
        
        // Создаем и добавляем элемент даты
        const dateSpan = document.createElement('span');
        dateSpan.className = 'message-date';
        dateSpan.textContent = dateStr;
        
        // Сохраняем временную метку в атрибуте data-timestamp
        messageElement.dataset.timestamp = timestamp.getTime();
        
        timeElement.appendChild(dateSpan);
        timeElement.appendChild(document.createTextNode(timeStr));
        
        // Собираем элемент сообщения
        messageElement.appendChild(contentElement);
        messageElement.appendChild(timeElement);
        
        // Добавляем в контейнер сообщений
        messagesContainer.appendChild(messageElement);
        
        // Инициализируем специальные компоненты в сообщении
        if (window.MarkdownProcessor) {
            MarkdownProcessor.processMessage(messageElement);
        }
        
        scrollToBottom();
        return;
    }
    
    // Если шаблон найден, используем его
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
    
    // Используем переданную или созданную временную метку
    const dateStr = timestamp.toLocaleDateString('ru-RU');
    const timeStr = timestamp.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
    
    // Создаем элемент для даты
    const dateSpan = document.createElement('span');
    dateSpan.className = 'message-date';
    dateSpan.textContent = dateStr;
    
    // Сохраняем временную метку в атрибуте data-timestamp
    messageElement.dataset.timestamp = timestamp.getTime();
    
    // Добавляем дату и время в элемент времени
    timeElement.appendChild(dateSpan);
    timeElement.appendChild(document.createTextNode(timeStr));
    
    messagesContainer.appendChild(messageElement);
    
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
    
    // Создаем индикатор с анимированными точками
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    
    // Добавляем индикатор в контейнер
    container.appendChild(typingIndicator);
    
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
        // Удаляем индикатор из DOM
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
    if (fileNameElement) {
        fileNameElement.textContent = file.name;
    }
    
    const uploadPreview = document.getElementById('upload-preview');
    if (uploadPreview) {
        uploadPreview.classList.remove('hidden');
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
        sendBtn.disabled = messageInput.value.trim() === '';
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
            }
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
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
        authScreens.style.display = 'none';
        mainApp.style.display = 'flex';
    } else {
        mainApp.style.display = 'none';
        authScreens.style.display = 'flex';
    }
}

// Финальная инициализация
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM загружен, начинаем инициализацию приложения');
    
    // Первичная инициализация мобильных улучшений
    initMobileEnhancements();
    
    // Инициализация основного приложения
    initApp();
    
    // Инициализация социальных ссылок
    initSocialLinks();
    
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
    
    // Обработчик изменения размера окна для переинициализации мобильных улучшений
    window.addEventListener('resize', () => {
        if (isMobile() && !window.mobileEnhancementsInitialized) {
            initMobileMenu();
            window.mobileEnhancementsInitialized = true;
        }
    });
    
    // Инициализация Mermaid для диаграмм
    if (window.mermaid) {
        mermaid.initialize({
            startOnLoad: false,
            theme: 'dark',
            securityLevel: 'loose'
        });
    }
    
    // Проверяем наличие ссылки на Telegram в футере
    ensureTelegramLink();
    
    // Оптимизируем стили футера
    fixFooterStyles();
    
    console.log('Инициализация приложения завершена');
});