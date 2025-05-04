/**
 * LawGPT - Основной файл приложения
 * Интегрированная версия с мобильными улучшениями
 * @version 2.0.0
 * @date 2024-03-14
 */

console.log("LawGPT Frontend загружен");

// Конфигурация приложения
const config = {
    apiUrl: "/api",
    apiTimeout: 60000,
    storageTokenKey: "lawgpt_token",
    storageThreadKey: "lawgpt_thread_id",
    storageTempTokenKey: "lawgpt_temp_token",
    markdownEnabled: true,
    autoscrollEnabled: true,
    maxFileSize: 50 * 1024 * 1024,
    mobileBreakpoint: 768, // Точка перехода для мобильных устройств
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
        /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
            navigator.userAgent,
        ) ||
        (navigator.deviceMemory && navigator.deviceMemory < 2)
    );
}

/**
 * Инициализация свайп-жестов для мобильных устройств
 */
function initSwipeGestures() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log("Инициализация свайп-жестов");
}

/**
 * Инициализация pull-to-refresh для обновления списка threads
 */
function initPullToRefresh() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log("Инициализация pull-to-refresh для обновления списка threads");
}

/**
 * Оптимизация клавиатуры для мобильных устройств
 */
function initKeyboardOptimization() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log("Инициализация оптимизации клавиатуры");
}

/**
 * Инициализация ленивой загрузки сообщений
 */
function initLazyMessageLoading() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log("Инициализация ленивой загрузки сообщений");
}

/**
 * Оптимизация для маломощных устройств
 */
function optimizeForLowPowerDevices() {
    // Заглушка для метода - будет реализована в будущих версиях
    console.log("Оптимизация для маломощных устройств");
}

/**
 * Инициализация мобильного меню
 */
function initMobileMenu() {
    // Получаем необходимые элементы
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    const header = document.querySelector(".header");

    // Проверяем наличие sidebar и overlay
    if (!sidebar || !overlay) {
        console.error("Не найдены sidebar или overlay для мобильного меню");
        return;
    }

    // Проверяем наличие кнопки меню
    let menuToggle = document.getElementById("menu-toggle");

    // Если кнопки нет, создаем её
    if (!menuToggle) {
        console.log("Создаем новую кнопку меню");
        menuToggle = document.createElement("button");
        menuToggle.id = "menu-toggle";
        menuToggle.className = "menu-toggle";
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
    menuToggle.addEventListener("click", function () {
        console.log("Клик по кнопке меню обработан");
        sidebar.classList.toggle("active");
        overlay.classList.toggle("active");
        menuToggle.classList.toggle("active");
        document.body.style.overflow = sidebar.classList.contains("active")
            ? "hidden"
            : "";
    });

    // Закрытие меню при клике на оверлей
    overlay.addEventListener("click", function () {
        console.log("Клик по оверлею");
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
        menuToggle.classList.remove("active");
        document.body.style.overflow = "";
    });

    // Закрытие меню при выборе чата на мобильных устройствах
    document.addEventListener("click", function (e) {
        const chatItem = e.target.closest(".chat-item");
        if (chatItem && window.innerWidth <= 768) {
            sidebar.classList.remove("active");
            overlay.classList.remove("active");
            menuToggle.classList.remove("active");
            document.body.style.overflow = "";
        }
    });

    console.log("Мобильное меню инициализировано успешно");
}

/**
 * Инициализация мобильных улучшений
 * Централизованный метод для настройки мобильного интерфейса
 */
function initMobileEnhancements() {
    if (isMobile()) {
        console.log("🚀 Инициализация мобильных улучшений");

        initSwipeGestures();
        initPullToRefresh();
        initKeyboardOptimization();
        initLazyMessageLoading();

        if (isLowPowerDevice()) {
            console.log("⚡ Оптимизация для маломощных устройств");
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
    showAuthScreen("login-screen");
}

/**
 * Показывает конкретный экран аутентификации
 * @param {string} screenId - ID экрана для показа
 */
function showAuthScreen(screenId) {
    const screens = [
        "login-screen",
        "register-screen",
        "verify-screen",
        "forgot-password-screen",
        "reset-password-screen",
    ];

    screens.forEach((id) => {
        const screen = document.getElementById(id);
        if (screen) {
            if (id === screenId) {
                screen.style.display = "block";
            } else {
                screen.style.display = "none";
            }
        }
    });
}

/**
 * Показывает уведомление
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип уведомления ('success', 'error', 'info')
 */
function showNotification(message, type = "info") {
    // Просто вызываем createNotification без data-атрибутов и селекторов по тексту
    createNotification(message, type);
}

/**
 * Показывает всплывающее уведомление (toast)
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип уведомления ('success', 'error', 'info')
 */
function showToast(message, type = "info") {
    // Если уже есть контейнер для тостов, используем его, иначе создаем новый
    let toastContainer = document.querySelector(".toast-container");
    if (!toastContainer) {
        toastContainer = document.createElement("div");
        toastContainer.className = "toast-container";
        document.body.appendChild(toastContainer);

        // Добавляем стили для toast-контейнера, если их еще нет
        const style = document.createElement("style");
        style.textContent = `
            .toast-container {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 9999;
            }
            .toast {
                min-width: 250px;
                margin-bottom: 10px;
                padding: 15px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                animation: fadein 0.5s;
            }
            .toast.success {
                background-color: #4CAF50;
            }
            .toast.error {
                background-color: #f44336;
            }
            .toast.info {
                background-color: #2196F3;
            }
            @keyframes fadein {
                from { bottom: 0; opacity: 0; }
                to { bottom: 30px; opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }

    // Создаем toast-элемент
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    // Автоматически удаляем через 3 секунды
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.5s";
        setTimeout(() => toastContainer.removeChild(toast), 500);
    }, 3000);
}

/**
 * Показывает индикатор загрузки
 */
function showLoading() {
    document.getElementById("loading-overlay").style.display = "flex";
}

/**
 * Скрывает индикатор загрузки
 */
function hideLoading() {
    document.getElementById("loading-overlay").style.display = "none";
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
        "Content-Type": "application/json",
    };

    // Добавляем заголовок авторизации, если есть токен
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    // Опции для fetch
    const options = {
        method: method,
        headers: headers,
        timeout: config.apiTimeout,
    };

    // Добавляем тело запроса для методов, которые его поддерживают
    if (data && ["POST", "PUT", "PATCH"].includes(method)) {
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
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${config.apiUrl}${endpoint}`, {
            method: "POST",
            headers: headers,
            body: formData,
            timeout: config.apiTimeout,
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
    console.log("Обработка входа пользователя");
    e.preventDefault();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    console.log(`Авторизация с почтой: ${email}`);

    if (!email || !password) {
        showNotification("Пожалуйста, заполните все поля", "error");
        return;
    }

    showLoading();

    try {
        // Соответствует схеме UserLogin в app/schemas.py
        console.log("Отправка запроса на авторизацию");
        const response = await apiRequest("/login", "POST", {
            email: email,
            password: password,
        });

        console.log("Ответ получен:", response);

        if (response.access_token) {
            localStorage.setItem(config.storageTokenKey, response.access_token);
            hideLoading();
            showApp();
            loadUserProfile();
            loadChatThreads();
            showNotification("Вход выполнен успешно", "success");
        } else {
            hideLoading();
            showNotification(
                "Ошибка при входе: неверный ответ сервера",
                "error",
            );
        }
    } catch (error) {
        console.error("Ошибка при авторизации:", error);
        hideLoading();
        showNotification(
            `Ошибка при входе: ${error.message || "проверьте данные"}`,
            "error",
        );
    }
}

/**
 * Обработчик регистрации пользователя
 * @param {Event} e - Событие отправки формы
 */
async function handleRegister(e) {
    e.preventDefault();

    const firstName = document.getElementById("register-firstname").value;
    const lastName = document.getElementById("register-lastname").value;
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;

    if (!firstName || !lastName || !email || !password) {
        showNotification("Пожалуйста, заполните все поля", "error");
        return;
    }

    showLoading();

    try {
        // Соответствует UserCreate схеме в app/schemas.py
        const response = await apiRequest("/register", "POST", {
            email: email,
            password: password,
            first_name: firstName,
            last_name: lastName,
        });

        if (response.temp_token || response.message) {
            // Сохраняем временный токен для верификации
            if (response.temp_token) {
                localStorage.setItem(
                    config.storageTempTokenKey,
                    response.temp_token,
                );
            }
            // Сохраняем email для повторной отправки кода
            localStorage.setItem("temp_email", email);

            hideLoading();
            showAuthScreen("verify-screen");
            showNotification(
                response.message || "Код подтверждения отправлен на ваш email",
                "success",
            );
        } else {
            hideLoading();
            showNotification(
                "Ошибка при регистрации: неверный ответ сервера",
                "error",
            );
        }
    } catch (error) {
        hideLoading();
        showNotification(
            `Ошибка при регистрации: ${error.message || "проверьте данные"}`,
            "error",
        );
    }
}

/**
 * Обработчик верификации email
 * @param {Event} e - Событие отправки формы
 */
async function handleVerify(e) {
    e.preventDefault();

    const code = document.getElementById("verify-code").value;
    const token = localStorage.getItem(config.storageTempTokenKey);

    if (!code) {
        showNotification("Пожалуйста, введите код подтверждения", "error");
        return;
    }

    if (!token) {
        showNotification("Ошибка: токен не найден", "error");
        showAuthScreen("login-screen");
        return;
    }

    showLoading();

    try {
        // Соответствует схеме VerifyRequest в app/schemas.py
        const response = await apiRequest(
            "/verify",
            "POST",
            {
                code: parseInt(code),
            },
            token,
        );

        if (response.access_token) {
            localStorage.setItem(config.storageTokenKey, response.access_token);
            localStorage.removeItem(config.storageTempTokenKey);
            localStorage.removeItem("temp_email");
            hideLoading();
            showApp();
            loadUserProfile();
            loadChatThreads();
            showNotification("Аккаунт успешно подтвержден", "success");
        } else {
            hideLoading();
            showNotification(
                "Ошибка при верификации: неверный ответ сервера",
                "error",
            );
        }
    } catch (error) {
        hideLoading();
        // Проверяем, авторизован ли пользователь
        if (localStorage.getItem(config.storageTokenKey)) {
            // Уже авторизован — не показываем ошибку
            return;
        }
        showNotification(
            `Ошибка при верификации: ${error.message || "неверный код"}`,
            "error",
        );
    }
}

/**
 * Обработчик повторной отправки кода
 * @param {Event} e - Событие клика
 */
async function handleResendCode(e) {
    e.preventDefault();

    const email = localStorage.getItem("temp_email");

    if (!email) {
        showNotification("Ошибка: email не найден", "error");
        showAuthScreen("login-screen");
        return;
    }

    showLoading();

    try {
        // Используем существующий метод register вместо несуществующего resend-code
        const response = await apiRequest("/register", "POST", {
            email: email,
            password: "temporary", // Это будет заменено при верификации
            first_name: "Временное",
            last_name: "Имя",
        });

        if (response.temp_token) {
            localStorage.setItem(
                config.storageTempTokenKey,
                response.temp_token,
            );
        }

        hideLoading();
        showNotification("Код подтверждения отправлен повторно", "success");
    } catch (error) {
        hideLoading();
        showNotification(
            `Ошибка при повторной отправке кода: ${error.message}`,
            "error",
        );
    }
}

/**
 * Обработчик восстановления пароля
 * @param {Event} e - Событие отправки формы
 */
async function handleForgotPassword(e) {
    e.preventDefault();

    const email = document.getElementById("forgot-email").value;

    if (!email) {
        showNotification("Пожалуйста, введите email", "error");
        return;
    }

    showLoading();

    try {
        // Соответствует схеме PasswordResetRequest в app/schemas.py
        const response = await apiRequest("/forgot-password", "POST", {
            email: email,
        });

        localStorage.setItem("reset_email", email);
        hideLoading();
        showAuthScreen("reset-password-screen");

        // Предзаполняем email в форме сброса пароля
        document.getElementById("reset-email").value = email;

        showNotification(
            "Код для сброса пароля отправлен на ваш email",
            "success",
        );
    } catch (error) {
        hideLoading();
        showNotification(
            `Ошибка при восстановлении пароля: ${error.message}`,
            "error",
        );
    }
}

/**
 * Обработчик сброса пароля
 * @param {Event} e - Событие отправки формы
 */
async function handleResetPassword(e) {
    e.preventDefault();

    const email = document.getElementById("reset-email").value;
    const code = document.getElementById("reset-code").value;
    const newPassword = document.getElementById("reset-password").value;

    if (!email || !code || !newPassword) {
        showNotification("Пожалуйста, заполните все поля", "error");
        return;
    }

    showLoading();

    try {
        // Соответствует схеме PasswordResetConfirm в app/schemas.py
        const response = await apiRequest("/reset-password", "POST", {
            email: email,
            code: parseInt(code),
            new_password: newPassword,
        });

        hideLoading();
        showAuthScreen("login-screen");
        showNotification(
            "Пароль успешно изменен. Теперь вы можете войти с новым паролем",
            "success",
        );
    } catch (error) {
        hideLoading();
        showNotification(`Ошибка при сбросе пароля: ${error.message}`, "error");
    }
}

/**
 * Обработчик выхода пользователя
 */
async function handleLogout() {
    showLoading();

    try {
        await apiRequest("/logout", "POST");
    } catch (error) {
        console.error("Ошибка при выходе:", error);
    } finally {
        localStorage.removeItem(config.storageTokenKey);
        localStorage.removeItem(config.storageThreadKey);
        hideLoading();
        showAuth();
        showNotification("Выход выполнен успешно", "success");
    }
}

/**
 * Проверка валидности токена
 * @param {string} token - JWT токен для проверки
 * @returns {Promise<boolean>} - Promise с результатом проверки
 */
async function validateToken(token) {
    try {
        const response = await apiRequest("/profile", "GET", null, token);
        return !!response; // Если получили успешный ответ, значит токен валиден
    } catch (error) {
        console.error("Ошибка при валидации токена:", error);
        return false;
    }
}

// Модальное окно профиля
function showProfileModal() {
    // Создаем модальное окно, если его еще нет
    let modal = document.getElementById("profile-modal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "profile-modal";
        modal.className = "modal";

        document.body.appendChild(modal);
    }

    // Загружаем данные профиля
    apiRequest("/profile", "GET")
        .then((data) => {
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
            modal
                .querySelector(".close-modal")
                .addEventListener("click", () => {
                    modal.style.display = "none";
                });

            // Показываем модальное окно
            modal.style.display = "block";
        })
        .catch((error) => {
            showNotification(
                `Ошибка загрузки профиля: ${error.message}`,
                "error",
            );
        });
}

// Модальное окно "О нас"
function showAboutModal() {
    // Создаем модальное окно, если его еще нет
    let modal = document.getElementById("about-modal");
    if (!modal) {
        modal = document.createElement("div");
        modal.id = "about-modal";
        modal.className = "modal";

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
    modal.querySelector(".close-modal").addEventListener("click", () => {
        modal.style.display = "none";
    });

    // Показываем модальное окно
    modal.style.display = "block";
}

/**
 * Функция для добавления ссылки на Telegram в футер
 */
function ensureTelegramLink() {
    try {
        const footerSocialLinks = document.querySelector(
            ".footer .social-links",
        );

        if (!footerSocialLinks) {
            console.error("Не найден контейнер для социальных ссылок в футере");
            return;
        }

        const telegramLink = footerSocialLinks.querySelector(
            'a[href*="t.me"], a[href*="telegram"]',
        );

        if (!telegramLink) {
            const newTelegramLink = document.createElement("a");
            newTelegramLink.href = "https://t.me/Law_GPT";
            newTelegramLink.target = "_blank";
            newTelegramLink.rel = "noopener noreferrer";
            newTelegramLink.className = "social-link";
            newTelegramLink.innerHTML =
                '<i class="fab fa-telegram"></i> Telegram';

            footerSocialLinks.appendChild(newTelegramLink);
            console.log("Ссылка на Telegram добавлена в футер");
        }
    } catch (error) {
        console.error("Ошибка при добавлении ссылки Telegram:", error);
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
        const socialLinks = document.querySelectorAll(".footer a, .nav-links a");
        socialLinks.forEach(link => {
            if (link.innerText && !link.querySelector('i')) {
                if (link.href && (
                    link.href.includes("t.me") || 
                    link.href.includes("telegram"))
                ) {
                    link.innerHTML =
                        '<i class="fab fa-telegram"></i> ' + link.textContent;
                } else if (link.href && link.href.includes("whatsapp")) {
                    link.innerHTML =
                        '<i class="fab fa-whatsapp"></i> ' + link.textContent;
                }
            }
        });

        // Проверяем, загружена ли библиотека Font Awesome
        if (
            typeof FontAwesome === "undefined" &&
            document.querySelector('[class*="fa-"]') === null
        ) {
            // Если Font Awesome не загружен, добавляем его
            const fontAwesomeLink = document.createElement("link");
            fontAwesomeLink.rel = "stylesheet";
            fontAwesomeLink.href =
                "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css";
            document.head.appendChild(fontAwesomeLink);
            console.log("Font Awesome добавлен для иконок социальных сетей");
        }

        // Находим все социальные ссылки
        const socialLinks2 = document.querySelectorAll(".social-link");
        socialLinks2.forEach((link) => {
            // Проверяем, есть ли у ссылки иконка
            if (!link.querySelector('i[class*="fa-"]')) {
                // Если иконки нет, определяем, какую добавить
                if (link.href && link.href.includes("vk.com")) {
                    link.innerHTML =
                        '<i class="fab fa-vk"></i> ' + link.textContent;
                } else if (
                    link.href &&
                    (link.href.includes("t.me") ||
                        link.href.includes("telegram"))
                ) {
                    link.innerHTML =
                        '<i class="fab fa-telegram"></i> ' + link.textContent;
                } else if (link.href && link.href.includes("whatsapp")) {
                    link.innerHTML =
                        '<i class="fab fa-whatsapp"></i> ' + link.textContent;
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
    const footer = document.querySelector(".footer");
    if (footer) {
        // Применяем улучшенные стили для футера
        footer.style.padding = "0.25rem";
        footer.style.paddingBottom =
            "calc(0.25rem + env(safe-area-inset-bottom))";
        footer.style.minHeight = "auto";
        footer.style.marginTop = "auto";

        // Уменьшаем отступы между элементами
        const footerDivs = footer.querySelectorAll("div");
        footerDivs.forEach((div) => {
            div.style.margin = "0.05rem 0";
        });
    }
}

/**
 * Инициализация приложения
 */
function initApp() {
    console.log("Инициализация приложения");

    // Проверка авторизации
    const token = localStorage.getItem(config.storageTokenKey);

    if (token) {
        // Если есть токен, проверяем его валидность
        validateToken(token)
            .then((isValid) => {
                if (isValid) {
                    showApp();
                    loadUserProfile();
                    loadChatThreads();

                    // Добавим проверку на пустой список чатов и автоматически создадим первый чат
                    // Используем флаг, чтобы предотвратить двойное создание треда
                    const hasCreatedInitialChat = localStorage.getItem('hasCreatedInitialChat');

                    setTimeout(() => {
                        const chatList = document.getElementById("chat-list");
                        if (chatList && 
                            (chatList.children.length === 0 || 
                             chatList.querySelector(".chat-item.empty")) && 
                            !hasCreatedInitialChat) {

                            console.log("Создаем первый чат для нового пользователя");
                            localStorage.setItem('hasCreatedInitialChat', 'true');
                            createNewChat();
                        }
                    }, 1000);
                } else {
                    showAuth();
                }
            })
            .catch((error) => {
                console.error("Ошибка проверки токена:", error);
                showAuth();
            });
    } else {
        // Если токена нет, показываем экран авторизации
        showAuth();
    }

    // Инициализация обработчиков событий
    initEventListeners();

    //    // Инициализация мобильного меню
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
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", handleLogout);
    }

    // Обработчики для переключения между формами
    initAuthSwitchers();
}

/**
 * Инициализация обработчиков форм аутентификации
 */
function initAuthForms() {
    console.log("Инициализация форм аутентификации");

    try {
        // Форма входа
        const loginForm = document.getElementById("login-form");
        if (loginForm) {
            console.log("Найдена форма входа");
            loginForm.addEventListener("submit", function(e) {
                e.preventDefault();
                console.log("Форма входа отправлена");
                handleLogin(e);
            });
            console.log("Обработчик для формы входа успешно добавлен");
        } else {
            console.error("Форма входа не найдена");
        }

        // Форма регистрации
        const registerForm = document.getElementById("register-form");
        if (registerForm) {
            console.log("Найдена форма регистрации");
            registerForm.addEventListener("submit", function(e) {
                e.preventDefault();
                console.log("Форма регистрации отправлена");
                handleRegister(e);
            });
            console.log("Обработчик для формы регистрации успешно добавлен");
        } else {
            console.error("Форма регистрации не найдена");
        }

        // Форма верификации
        const verifyForm = document.getElementById("verify-form");
        if (verifyForm) {
            verifyForm.addEventListener("submit", function(e) {
                e.preventDefault();
                console.log("Форма верификации отправлена");
                handleVerify(e);
            });
            console.log("Обработчик для формы верификации успешно добавлен");
        } else {
            console.error("Форма верификации не найдена");
        }

        // Форма восстановления пароля
        const forgotPasswordForm = document.getElementById("forgot-password-form");
        if (forgotPasswordForm) {
            forgotPasswordForm.addEventListener("submit", function(e) {
                e.preventDefault();
                console.log("Форма восстановления пароля отправлена");
                handleForgotPassword(e);
            });
            console.log("Обработчик для формы восстановления пароля успешно добавлен");
        } else {
            console.error("Форма восстановления пароля не найдена");
        }

        // Форма сброса пароля
        const resetPasswordForm = document.getElementById("reset-password-form");
        if (resetPasswordForm) {
            resetPasswordForm.addEventListener("submit", function(e) {
                e.preventDefault();
                console.log("Форма сброса пароля отправлена");
                handleResetPassword(e);
            });
            console.log("Обработчик для формы сброса пароля успешно добавлен");
        } else {
            console.error("Форма сброса пароля не найдена");
        }

        // Кнопка повторной отправки кода
        const resendCodeBtn = document.getElementById("resend-code");
        if (resendCodeBtn) {
            resendCodeBtn.addEventListener("click", function(e) {
                e.preventDefault();
                console.log("Клик на кнопке повторной отправки кода");
                handleResendCode(e);
            });
            console.log("Обработчик для кнопки повторной отправки кода успешно добавлен");
        } else {
            console.error("Кнопка повторной отправки кода не найдена");
        }

        // Кнопки возврата
        const backToLoginBtn = document.getElementById("back-to-login");
        if (backToLoginBtn) {
            backToLoginBtn.addEventListener("click", function(e) {
                e.preventDefault();
                console.log("Клик на кнопке возврата к логину");
                showAuthScreen("login-screen");
            });
            console.log("Обработчик для кнопки возврата к логину успешно добавлен");
        } else {
            console.error("Кнопка возврата к логину не найдена");
        }

        const resetBackToLoginBtn = document.getElementById("reset-back-to-login");
        if (resetBackToLoginBtn) {
            resetBackToLoginBtn.addEventListener("click", function(e) {
                e.preventDefault();
                console.log("Клик на кнопке возврата к логину из сброса");
                showAuthScreen("login-screen");
            });
            console.log("Обработчик для кнопки возврата из сброса успешно добавлен");
        } else {
            console.error("Кнопка возврата из сброса не найдена");
        }

        const verifyToLoginBtn = document.getElementById("verify-to-login");
        if (verifyToLoginBtn) {
            verifyToLoginBtn.addEventListener("click", function(e) {
                e.preventDefault();
                console.log("Клик на кнопке возврата к логину из верификации");
                showAuthScreen("login-screen");
            });
            console.log("Обработчик для кнопки возврата из верификации успешно добавлен");
        } else {
            console.error("Кнопка возврата из верификации не найдена");
        }

        console.log("Все обработчики форм аутентификации успешно инициализированы");
    } catch (error) {
        console.error("Ошибка при инициализации форм аутентификации:", error);
    }
}

/**
 * Инициализация переключателей между формами аутентификации
 */
function initAuthSwitchers() {
    console.log("Инициализация переключателей форм");

    try {
        // Переход к регистрации
        const toRegisterBtn = document.getElementById("to-register");
        if (toRegisterBtn) {
            console.log("Найдена кнопка перехода к регистрации");

            // Удаляем существующие обработчики во избежание дублирования
            const newBtn = toRegisterBtn.cloneNode(true);
            toRegisterBtn.parentNode.replaceChild(newBtn, toRegisterBtn);

            // Добавляем новый обработчик
            newBtn.addEventListener("click", function(e) {
                console.log("Клик на кнопке перехода к регистрации");
                e.preventDefault();
                showAuthScreen("register-screen");
                return false;
            });

            // Дополнительный обработчик через onclick
            newBtn.onclick = function(e) {
                console.log("Клик на кнопке перехода к регистрации (onclick)");
                e.preventDefault();
                showAuthScreen("register-screen");
                return false;
            };

            console.log("Обработчик для кнопки перехода к регистрации успешно добавлен");
        } else {
            console.error("Кнопка перехода к регистрации не найдена");
        }

        // Переход к входу
        const toLoginBtn = document.getElementById("to-login");
        if (toLoginBtn) {
            console.log("Найдена кнопка перехода к входу");

            // Удаляем существующие обработчики во избежание дублирования
            const newBtn = toLoginBtn.cloneNode(true);
            toLoginBtn.parentNode.replaceChild(newBtn, toLoginBtn);

            // Добавляем новый обработчик
            newBtn.addEventListener("click", function(e) {
                console.log("Клик на кнопке перехода к входу");
                e.preventDefault();
                showAuthScreen("login-screen");
                return false;
            });

            // Дополнительный обработчик через onclick
            newBtn.onclick = function(e) {
                console.log("Клик на кнопке перехода к входу (onclick)");
                e.preventDefault();
                showAuthScreen("login-screen");
                return false;
            };

            console.log("Обработчик для кнопки перехода к входу успешно добавлен");
        } else {
            console.error("Кнопка перехода к входу не найдена");
        }

        // Переход к восстановлению пароля
        const toForgotPasswordBtn = document.getElementById("to-forgot-password");
        if (toForgotPasswordBtn) {
            console.log("Найдена кнопка восстановления пароля");

            // Удаляем существующие обработчики во избежание дублирования
            const newBtn = toForgotPasswordBtn.cloneNode(true);
            toForgotPasswordBtn.parentNode.replaceChild(newBtn, toForgotPasswordBtn);

            // Добавляем новый обработчик
            newBtn.addEventListener("click", function(e) {
                console.log("Клик на кнопке восстановления пароля");
                e.preventDefault();
                showAuthScreen("forgot-password-screen");
                return false;
            });

            // Дополнительный обработчик через onclick
            newBtn.onclick = function(e) {
                console.log("Клик на кнопке восстановления пароля (onclick)");
                e.preventDefault();
                showAuthScreen("forgot-password-screen");
                return false;
            };

            console.log("Обработчик для кнопки восстановления пароля успешно добавлен");
        } else {
            console.error("Кнопка восстановления пароля не найдена");
        }

        console.log("Все переключатели форм успешно инициализированы");
    } catch (error) {
        console.error("Ошибка при инициализации переключателей форм:", error);
    }
}

/**
 * Инициализация интерфейса чата
 */
function initChatInterface() {
    // Кнопка нового чата
    const newChatBtn = document.getElementById("new-chat-btn");
    if (newChatBtn) {
        newChatBtn.addEventListener("click", createNewChat);
    }

    // Логотип как ссылка на главную
    const logo = document.querySelector(".logo");
    if (logo) {
        logo.addEventListener("click", function (e) {
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
    const messageInput = document.getElementById("message-input");
    if (messageInput) {
        messageInput.addEventListener("input", () => {
            // Автоматическое изменение высоты поля ввода
            messageInput.style.height = "auto";
            messageInput.style.height = messageInput.scrollHeight + "px";
            messageInput.style.height =
                Math.min(messageInput.scrollHeight, 150) + "px";

            // Активация/деактивация кнопки отправки
            const sendBtn = document.getElementById("send-btn");
            if (sendBtn) {
                sendBtn.disabled = messageInput.value.trim() === "";
            }
        });

        // Отправка сообщения по Enter
        messageInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (messageInput.value.trim()) {
                    const sendBtn = document.getElementById("send-btn");
                    if (sendBtn) {
                        sendBtn.click();
                    }
                }
            }
        });
    }

    // Отправка сообщения
    const sendBtn = document.getElementById("send-btn");
    if (sendBtn) {
        sendBtn.addEventListener("click", sendMessage);
    }

    // Загрузка файла
    const fileUpload = document.getElementById("file-upload");
    if (fileUpload) {
        fileUpload.addEventListener("change", handleFileUpload);
    }

    // Удаление файла
    const removeFileBtn = document.getElementById("remove-file-btn");
    if (removeFileBtn) {
        removeFileBtn.addEventListener("click", removeUploadedFile);
    }

    // Обработчики для модальных окон
    const navProfileBtn = document.getElementById("nav-profile");
    if (navProfileBtn) {
        navProfileBtn.addEventListener("click", showProfileModal);
    }

    const navAboutBtn = document.getElementById("nav-about");
    if (navAboutBtn) {
        navAboutBtn.addEventListener("click", showAboutModal);
    }
}

/**
 * Форматирует временную метку в нужный формат
 * @param {Date} date - Объект даты для форматирования
 * @returns {string} Отформатированное время
 */
function formatTimestamp(date) {
    // Проверяем, является ли date объектом Date
    if (!(date instanceof Date)) {
        date = new Date(date);
    }

    // Проверяем валидность даты
    if (isNaN(date.getTime())) {
        console.warn('Некорректная дата:', date);
        return formatTimestamp(new Date()); // Возвращаем текущее время
    }

    // Проверяем на слишком старую дату (до 2020 года) или Unix epoch (1970)
    if (date.getFullYear() < 2020) {
        console.warn('Обнаружена слишком старая дата, используем текущее время:', date);
        return formatTimestamp(new Date());
    }

    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${day}.${month}.${year} ${hours}:${minutes}`;
}

/**
 * Возвращает текущее время в отформатированном виде
 * @returns {string} Отформатированное время
 */
function getCurrentTime() {
    return formatTimestamp(new Date());
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
        const response = await apiRequest("/create_thread", "POST");
        console.log('Ответ от сервера при создании чата:', response);

        if (response.thread_id) {
            const threadId = response.thread_id;
            console.log('Получен новый threadId:', threadId);
            
            localStorage.setItem(config.storageThreadKey, threadId);
            console.log('Сохранен threadId в localStorage:', threadId);

            // Обновляем список чатов
            await loadChatThreads();

            // Открываем новый чат
            selectChatThread(threadId);

            // Очищаем контейнер с сообщениями
            const messagesContainer =
                document.getElementById("messages-container");
            if (messagesContainer) {
                messagesContainer.innerHTML = "";
            }

            // Показываем приветственное сообщение от ассистента
            addAssistantMessage(
                "Здравствуйте! Я юридический ассистент LawGPT. Чем я могу вам помочь?",
            );

            showNotification("Новый чат создан", "success");
        } else {
            showNotification("Ошибка при создании чата", "error");
        }
    } catch (error) {
        showNotification(`Ошибка при создании чата: ${error.message}`, "error");
    } finally {
        hideLoading();
    }
}

/**
 * Загружает список threads пользователя
 */
async function loadChatThreads() {
    try {
        const response = await apiRequest("/chat/threads", "GET");

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
        console.error("Ошибка при загрузке списка threads:", error);
        showNotification("Не удалось загрузить историю threads", "error");
    }
}

/**
 * Отображает список threads в боковой панели
 * @param {Array} threads - Массив объектов с данными threads
 */
function renderChatThreads(threads) {
    const chatList = document.getElementById("chat-list");
    if (!chatList) {
        console.error("Список чатов не найден");
        return;
    }

    chatList.innerHTML = "";

    // Сортируем threads по дате создания (новые сверху)
    threads.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    threads.forEach((thread) => {
        const chatItem = document.createElement("li");
        chatItem.className = "chat-item";
        chatItem.dataset.threadId = thread.id;

        // Форматируем дату
        const date = new Date(thread.created_at);
        const formattedDate = formatTimestamp(date);

        // Добавляем контент чата
        chatItem.innerHTML = `
            <div class="chat-info">
                <div class="chat-title">${thread.first_message || "Новый чат"}</div>
                <div class="chat-date">${formattedDate}</div>
            </div>
        `;

        // Обработчик клика
        chatItem.addEventListener("click", () => {
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
    console.log('Выбран чат с ID:', threadId);
    
    // Сохраняем ID треда в localStorage
    localStorage.setItem(config.storageThreadKey, threadId);
    console.log('Сохранен threadId в localStorage:', threadId);

    // Обновляем UI - подсвечиваем выбранный чат
    const chatItems = document.querySelectorAll(".chat-item");
    chatItems.forEach((item) => {
        if (item.dataset.threadId === threadId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    // Обновляем заголовок чата
    const currentChatId = document.getElementById("current-chat-id");
    if (currentChatId) {
        currentChatId.textContent = threadId;
    }

    // Очищаем контейнер сообщений
    const messagesContainer = document.getElementById("messages-container");
    if (messagesContainer) {
        messagesContainer.innerHTML = "";
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
        const messages = await apiRequest(`/messages/${threadId}`, "GET");
        console.log('Получены сообщения от сервера:', messages);

        if (Array.isArray(messages)) {
            console.log(`Найдено ${messages.length} сообщений`);
            // Проверяем наличие временных меток и форматируем их, если необходимо
            const formattedMessages = messages.map((message) => {
                console.log('Обработка сообщения:', message);
                // Если у сообщения нет временной метки, добавляем текущую дату
                if (!message.created_at) {
                    console.warn(
                        `Сообщение без временной метки: ${message.id || "без ID"}`,
                    );
                    message.created_at = new Date().toISOString();
                }

                // Убедимся, что строка даты/времени корректно форматируется
                try {
                    const testDate = new Date(message.created_at);
                    if (isNaN(testDate.getTime())) {
                        console.warn(
                            `Некорректная дата в сообщении: ${message.created_at}`,
                        );
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
        } else {
            // Если сервер вернул не массив, это действительно ошибка
            console.warn("Получен неверный формат данных от сервера:", messages);
            renderChatMessages([]);
            showNotification("Не удалось загрузить сообщения чата", "error");
        }
    } catch (error) {
        // Показываем ошибку только если это действительно ошибка запроса
        console.error("Ошибка при загрузке сообщений:", error);
        showNotification("Не удалось загрузить сообщения чата", "error");
    }
}

/**
 * Отображает сообщения чата с использованием временных меток
 * @param {Array} messages - Массив объектов с сообщениями
 */
function renderChatMessages(messages) {
    console.log('Начало рендеринга сообщений:', messages);
    const messagesContainer = document.getElementById("messages-container");
    if (!messagesContainer) {
        console.error("Контейнер сообщений не найден");
        return;
    }

    messagesContainer.innerHTML = "";

    if (!messages || messages.length === 0) {
        console.log('Сообщений нет, показываем приветственное сообщение');
        // Если сообщений нет, показываем приветственное сообщение
        addAssistantMessage(
            "Здравствуйте! Я юридический ассистент LawGPT. Чем я могу вам помочь?"
        );
        return;
    }

    console.log(`Рендеринг ${messages.length} сообщений`);
    // Добавляем все сообщения с сохранением временных меток
    messages.forEach((message, index) => {
        console.log(`Рендеринг сообщения ${index + 1}:`, message);
        // Преобразуем строку с датой в объект Date
        const timestamp = message.created_at
            ? new Date(message.created_at)
            : new Date();

        if (message.role === "user") {
            console.log('Добавляем сообщение пользователя');
            addUserMessage(message.content, timestamp);
        } else if (message.role === "assistant") {
            console.log('Добавляем сообщение ассистента');
            addAssistantMessage(message.content, timestamp);
        } else {
            console.warn('Неизвестная роль сообщения:', message.role);
        }
    });

    // Прокручиваем к последнему сообщению
    scrollToBottom();
    console.log('Рендеринг сообщений завершен');
}

/**
 * Отправляет сообщение пользователя
 */
async function sendMessage() {
    const messageInput = document.getElementById("message-input");
    const fileUpload = document.getElementById("file-upload");

    if (!messageInput || !fileUpload) {
        console.error("Элементы ввода сообщения не найдены");
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
        showNotification("Ошибка: чат не выбран", "error");
        return;
    }

    // Фиксируем время отправки сообщения пользователя
    const userTimestamp = new Date();

    // Добавляем сообщение пользователя в чат с зафиксированным временем
    if (text) {
        addUserMessage(text, userTimestamp);
    }

    // Очищаем поле ввода
    messageInput.value = "";
    messageInput.style.height = "auto";

    const sendBtn = document.getElementById("send-btn");
    if (sendBtn) {
        sendBtn.disabled = true;
    }

    // Показываем индикатор набора текста с обновляемым статусом
    showTypingIndicatorWithStatus();

    try {
        // Отправляем запрос на /deep-research/
        const response = await fetch("/deep-research/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem(config.storageTokenKey)}`
            },
            body: JSON.stringify({
                query: text,
                thread_id: threadId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Скрываем индикатор набора текста
        hideTypingIndicatorWithStatus();

        // Фиксируем время получения ответа ассистента
        const assistantTimestamp = new Date();

        if (data && data.results) {
            // Если есть reasoning_content, показываем его
            if (data.results.reasoning_content) {
                addReasoningMessage(data.results.reasoning_content);
            }
            
            // Добавляем основной ответ ассистента
            addAssistantMessage(data.results.analysis || data.results, assistantTimestamp);
        } else {
            addAssistantMessage("Не удалось получить ответ от ассистента", assistantTimestamp);
        }

    } catch (error) {
        hideTypingIndicatorWithStatus();
        showNotification(`Ошибка при отправке сообщения: ${error.message}`, "error");
        console.error("Ошибка при отправке сообщения:", error);
    } finally {
        if (sendBtn) {
            sendBtn.disabled = false;
        }
    }

    // Прокручиваем к последнему сообщению
    scrollToBottom();
}

// Вспомогательная функция для форматирования размера файла
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Байт';
    const k = 1024;
    const sizes = ['Байт', 'КБ', 'МБ', 'ГБ'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Обновляет текст в индикаторе набора текста
 * @param {string} message - Сообщение о статусе обработки
 */
function updateTypingIndicator(message) {
    const typingContainer = document.getElementById(
        "typing-indicator-container",
    );

    if (!typingContainer) {
        showTypingIndicator();
        setTimeout(() => updateTypingIndicator(message), 100);
        return;
    }

    // Создаем или обновляем текстовый элемент
    let statusText = typingContainer.querySelector(".typing-status");
    if (!statusText) {
        statusText = document.createElement("div");
        statusText.className = "typing-status";
        statusText.style.marginLeft = "10px";
        statusText.style.fontSize = "12px";
        statusText.style.color = "rgba(255, 255, 255, 0.7)";

        // Добавляем текст после индикатора с точками
        const indicator = typingContainer.querySelector(".typing-indicator");
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
 * @param {Date|null} timestamp - Временная метка (опционально)
 */
function addUserMessage(text, timestamp = null) {
    console.log('Добавление сообщения пользователя:', { text, timestamp });
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Контейнер сообщений не найден');
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-user';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Используем markdown для форматирования текста пользователя
    if (window.MarkdownProcessor) {
        contentDiv.innerHTML = MarkdownProcessor.markdownToHtml(text);
        // Инициализируем специальные компоненты (подсветка кода и т.д.)
        MarkdownProcessor.processMessage(messageDiv);
    } else {
        contentDiv.textContent = text;
    }
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = timestamp ? formatTimestamp(timestamp) : getCurrentTime();
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    messagesContainer.appendChild(messageDiv);
    
    // Добавляем обработку кнопок копирования кода
    if (window.MarkdownProcessor) {
        MarkdownProcessor.initSpecialComponents(messageDiv);
    }
    
    scrollToBottom();
    console.log('Сообщение пользователя добавлено');
}

/**
 * Добавляет сообщение ассистента в чат
 * @param {string} text - Текст сообщения
 * @param {Date|null} timestamp - Временная метка (опционально)
 */
function addAssistantMessage(text, timestamp = null) {
    if (typeof text !== 'string') {
        try {
            text = JSON.stringify(text);
        } catch {
            text = String(text);
        }
    }
    console.log('Добавление сообщения ассистента:', { text, timestamp });
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) {
        console.error('Контейнер сообщений не найден');
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-assistant';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    contentDiv.setAttribute('data-original-text', text);
    
    if (window.MarkdownProcessor) {
        contentDiv.innerHTML = MarkdownProcessor.markdownToHtml(text);
    } else {
        contentDiv.textContent = text;
    }
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = timestamp ? formatTimestamp(timestamp) : getCurrentTime();
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    messagesContainer.appendChild(messageDiv);
    
    if (window.MarkdownProcessor) {
        MarkdownProcessor.initSpecialComponents(messageDiv);
    }

    scrollToBottom();
    console.log('Сообщение ассистента добавлено');
}

/**
 * Показывает индикатор набора текста ассистентом
 */
function showTypingIndicator() {
    const messagesContainer = document.getElementById("messages-container");
    if (!messagesContainer) {
        console.error("Контейнер сообщений не найден");
        return;
    }

    // Сначала проверяем, существует ли уже индикатор
    let indicator = document.getElementById("typing-indicator-container");

    // Если индикатор уже существует, просто показываем его
    if (indicator) {
        indicator.style.display = "flex";
        return;
    }

    // Создаем новый индикатор
    const container = document.createElement("div");
    container.className = "message message-assistant";
    container.id = "typing-indicator-container";

    // Создаем индикатор с анимированными точками
    const typingIndicator = document.createElement("div");
    typingIndicator.className = "typing-indicator";
    typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    // Добавляем индикатор в контейнер
    container.appendChild(typingIndicator);

    // Добавляем контейнер в список сообщений
    messagesContainer.appendChild(container);

    // Прокручиваем к нижней части контеeнера
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Скрывает индикатор набора текста
 */
function hideTypingIndicator() {
    const indicator = document.getElementById("typing-indicator-container");
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
        showNotification(
            `Размер файла превышает ${config.maxFileSize / (1024 * 1024)} МБ`,
            "error",
        );
        e.target.value = "";
        return;
    }



    // Показываем предпросмотр файла
    const fileNameElement = document.getElementById("file-name");
    if (fileNameElement) {
        fileNameElement.textContent = file.name;
    }

    const uploadPreview = document.getElementById("upload-preview");
    if (uploadPreview) {
        uploadPreview.classList.remove("hidden");
    }

    // Активируем кнопку отправки
    const sendBtn = document.getElementById("send-btn");
    if (sendBtn) {
        sendBtn.disabled = false;
    }
}

/**
 * Удаляет загруженный файл
 */
function removeUploadedFile() {
    const fileUpload = document.getElementById("file-upload");
    if (fileUpload) {
        fileUpload.value = "";
    }

    const uploadPreview = document.getElementById("upload-preview");
    if (uploadPreview) {
        uploadPreview.classList.add("hidden");
    }

    // Проверяем статус кнопки отправки
    const messageInput = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-btn");
    if (messageInput && sendBtn) {
        sendBtn.disabled = messageInput.value.trim() === "";
    }
}

/**
 * Загружает профиль пользователя
 */
async function loadUserProfile() {
    try {
        const response = await apiRequest("/profile", "GET");

        if (response) {
            const userName = `${response.first_name} ${response.last_name}`;
            const userNameElement = document.getElementById("user-name");
            if (userNameElement) {
                userNameElement.textContent = userName;
            }
        }
    } catch (error) {
        console.error("Ошибка при загрузке профиля:", error);
    }
}

/**
 * Прокручивает контейнер сообщений к последнему сообщению
 */
function scrollToBottom() {
    if (!config.autoscrollEnabled) return;

    const messagesContainer = document.getElementById("messages-container");
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

/**
 * Переключает видимость между основным приложением и экранами аутентификации
 * @param {boolean} showAppScreen - true для показа основного приложения, false для экранов аутентификации
 */
function toggleAppVisibility(showAppScreen) {
    const authScreens = document.getElementById("auth-screens");
    const mainApp = document.getElementById("main-app");

    if (!authScreens || !mainApp) {
        console.error(
            "Не найдены необходимые элементы для переключения видимости",
        );
        return;
    }

    if (showAppScreen) {
        authScreens.style.display = "none";
        mainApp.style.display = "flex";
    } else {
        mainApp.style.display = "none";
        authScreens.style.display = "flex";
    }
}

// Финальная инициализация
document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM загружен, начинаем инициализацию приложения");

    try {
        console.log("Проверка состояния страницы...");
        console.log("Форма входа найдена:", document.getElementById("login-form") !== null);
        console.log("Форма регистрации найдена:", document.getElementById("register-form") !== null);
        console.log("Кнопка перехода к регистрации найдена:", document.getElementById("to-register") !== null);
        console.log("Кнопка перехода к входу найдена:", document.getElementById("to-login") !== null);

        // Инициализация обработчиков форм аутентификации и переключателей между ними
        initAuthForms();
        console.log("Обработчики форм инициализированы");

        initAuthSwitchers();
        console.log("Переключатели форм инициализированы");

        // Первичная инициализация мобильных улучшений
        initMobileEnhancements();
        console.log("Мобильные улучшения инициализированы");

        // Инициализация основного приложения
        initApp();
        console.log("Основное приложение инициализировано");

        // Инициализация социальных ссылок
        initSocialLinks();
        console.log("Социальные ссылки инициализированы");

        // Загрузка и инициализация библиотек для обработки Markdown
        if (config.markdownEnabled && window.marked) {
            window.markdown = marked;
            window.markdown.setOptions({
                breaks: true,
                gfm: true,
            });

            if (window.hljs) {
                window.markdown.setOptions({
                    highlight: function (code, lang) {
                        if (lang && window.hljs.getLanguage(lang)) {
                            return window.hljs.highlight(code, { language: lang })
                                .value;
                        }
                        return window.hljs.highlightAuto(code).value;
                    },
                });
            }
            console.log("Markdown поддержка инициализирована");
        }

        // Обработчик изменения размера окна для переинициализации мобильных улучшений
        window.addEventListener("resize", function() {
            if (isMobile() && !window.mobileEnhancementsInitialized) {
                initMobileMenu();
                window.mobileEnhancementsInitialized = true;
            }
        });

        // Инициализация Mermaid для диаграмм
        if (window.mermaid) {
            mermaid.initialize({
                startOnLoad: false,
                theme: "dark",
                securityLevel: "loose",
            });
            console.log("Mermaid инициализирован");
        }

        // Проверяем наличие ссылки на Telegram в футере
        ensureTelegramLink();
        console.log("Ссылка на Telegram проверена");

        // Оптимизируем стили футера
        fixFooterStyles();
        console.log("Стили футера оптимизированы");

        // Добавляем прямую инициализацию форм авторизации через JavaScript
        const loginForm = document.getElementById("login-form");
        if (loginForm) {
            console.log("Дополнительная регистрация обработчика формы входа");
            loginForm.onsubmit = function(e) {
                e.preventDefault();
                console.log("Форма входа отправлена (прямой обработчик)");
                handleLogin(e);
                return false;
            };
        }

        const toRegisterBtn = document.getElementById("to-register");
        if (toRegisterBtn) {
            console.log("Дополнительная регистрация обработчика перехода к регистрации");
            toRegisterBtn.onclick = function(e) {
                e.preventDefault();
                console.log("Клик на кнопке перехода к регистрации (прямой обработчик)");
                showAuthScreen("register-screen");
                return false;
            };
        }

        console.log("Инициализация приложения завершена");
    } catch (error) {
        console.error("Ошибка при инициализации приложения:", error);
        // Вывод подробной информации об ошибке
        console.error("Детали ошибки:", {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
    }
});

/**
 * Отображает кнопку загрузки файла
 * @param {string} downloadUrl - URL для скачивания файла
 */
function displayDownloadButton(downloadUrl) {
    const messagesContainer = document.getElementById("messages-container");
    if (!messagesContainer) {
        console.error("Контейнер сообщений не найден");
        return;
    }

    const downloadButton = document.createElement("a");
    downloadButton.href = downloadUrl;
    downloadButton.download = true; // Устанавливаем атрибут download для загрузки
    downloadButton.className = "download-button";
    downloadButton.textContent = "Скачать файл";
    messagesContainer.appendChild(downloadButton);
}

async function downloadRecognizedText(text, filename) {
    try {
        // Проверяем, не слишком ли большой текст для отправки через FormData
        if (text.length > 500000) {
            // если текст больше ~500KB
            // Создаем Blob напрямую в браузере
            const blob = new Blob([decodeURIComponent(text)], {
                type: "text/plain;charset=utf-8",
            });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            return;
        }

        // Для более коротких текстов используем серверный API
        const formData = new FormData();
        formData.append("file_content", decodeURIComponent(text));
        formData.append("file_name", filename);

        const response = await fetch("/api/download_recognized_text", {
            method: "POST",
            body: formData,
            headers: {
                Authorization: `Bearer ${localStorage.getItem(config.storageTokenKey)}`,
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP ошибка ${response.status}`);
        }

        // Создаем ссылку для скачивания файла
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showNotification("Файл успешно скачан", "success");
    } catch (error) {
        console.error("Ошибка при скачивании распознанного текста:", error);
        showNotification(`Ошибка при скачивании: ${error.message}`, "error");
    }
}

function displayMessageWithFile(
    message,
    isUser = false,
    allowDownload = false,
    fullText = "",
) {
    const messagesContainer = document.querySelector(".messages-container");
    const messageDiv = document.createElement("div");
    messageDiv.className = isUser
        ? "message user-message"
        : "message assistant-message";

    // Обработка Markdown и подсветка кода
    const renderedContent = marked.parse(message);

    // Добавляем кнопку загрузки текста, если это ответ с распознанным документом
    let downloadButton = "";
    if (!isUser && allowDownload && fullText) {
        downloadButton = `
            <div class="download-text-button">
                <button class="download-btn" onclick="downloadRecognizedText('${encodeURIComponent(fullText.replace(/'/g, "\\'")).substring(0, 1000)}...')"><i class="fas fa-download"></i> Скачать полный текст
                </button>
            </div>
        `;
    }

    const messageHTML = `
        <div class="message-content">
            ${renderedContent}
            ${downloadButton}
        </div>
    `;

    messageDiv.innerHTML = messageHTML;
    messagesContainer.appendChild(messageDiv);

    // Применяем подсветку синтаксиса Prism ко всем блокам кода
    Prism.highlightAllUnder(messageDiv);

    // Прокрутка вниз
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setupDownloadButton(docxUrl, txtUrl) {
    console.log("Настройка кнопок скачивания с URL:", { docxUrl, txtUrl });
    const container = document.getElementById("download-container");

    if (!container) {
        console.error("Не найден контейнер для кнопок скачивания");
        return;
    }

    container.innerHTML = "";

    if (docxUrl) {
        const docxLink = document.createElement("a");
        docxLink.className = "download-btn";
        docxLink.innerHTML = '<i class="fas fa-file-word"></i> Скачать DOCX';
        // Вместо прямой ссылки используем обработчик клика с передачей токена
        docxLink.addEventListener("click", function (e) {
            e.preventDefault();
            console.log("Клик по кнопке скачивания DOCX");
            downloadRecognizedText(docxUrl, "recognized_text.docx");
        });
        container.appendChild(docxLink);
    }

    if (txtUrl) {
        const txtLink = document.createElement("a");
        txtLink.className = "download-btn";
        txtLink.innerHTML = '<i class="fas fa-file-alt"></i> Скачать TXT';
        // Вместо прямой ссылки используем обработчик клика с передачей токена
        txtLink.addEventListener("click", function (e) {
            e.preventDefault();
            console.log("Клик по кнопке скачивания TXT");
            downloadRecognizedText(txtUrl, "recognized_text.txt");
        });
        container.appendChild(txtLink);
    }

    container.style.display = docxUrl || txtUrl ? "flex" : "none";
}

// Инициализация markdown при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    if (window.markdown && window.hljs) {
        // Настраиваем markdown
        markdown.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (__) {}
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true,
            gfm: true
        });
    }
});

// === Добавляем функцию для reasoning_content ===
function addReasoningMessage(reasoningText) {
    if (typeof reasoningText !== 'string') {
        try {
            reasoningText = JSON.stringify(reasoningText);
        } catch {
            reasoningText = String(reasoningText);
        }
    }
    let reasoningDiv = document.getElementById('reasoning-message');
    if (!reasoningDiv) {
        reasoningDiv = document.createElement('div');
        reasoningDiv.className = 'message message-reasoning';
        reasoningDiv.id = 'reasoning-message';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        reasoningDiv.appendChild(contentDiv);
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.appendChild(reasoningDiv);
    }
    const contentDiv = reasoningDiv.querySelector('.message-content');
    contentDiv.textContent = reasoningText;
    scrollToBottom();
}
function removeReasoningMessage() {
    const reasoningDiv = document.getElementById('reasoning-message');
    if (reasoningDiv) reasoningDiv.remove();
}

// === WebSocket обработка reasoning_content ===
function handleReasoningWebSocketMessage(event) {
    let data;
    try {
        data = JSON.parse(event.data);
    } catch (e) {
        showNotification("Ошибка парсинга ответа reasoning_content", "error");
        return;
    }
    if (data.error) {
        // Показываем только текст ошибки, не используем селектор с длинным текстом
        showNotification("Ошибка WebSocket reasoning: " + String(data.error), "error");
        removeReasoningMessage();
        return;
    }
    // Выводим reasoning_content и analysis, если есть
    let reasoning = typeof data.reasoning_content === 'string' ? data.reasoning_content : '';
    let content = typeof data.analysis === 'string' ? data.analysis : (typeof data.content === 'string' ? data.content : '');
    if (reasoning) {
        addReasoningMessage(reasoning);
    }
    if (content && !data.is_streaming) {
        // Финальный ответ — добавляем как обычное сообщение ассистента
        addAssistantMessage(content);
        removeReasoningMessage();
    }
}

// Переопределяем showNotification для безопасности
window.showNotification = function(message, type = 'info', duration = 3000) {
    // Обрезаем слишком длинные сообщения для безопасности селектора и отображения
    let safeMessage = String(message);
    if (safeMessage.length > 300) {
        safeMessage = safeMessage.slice(0, 297) + '...';
    }
    // Просто показываем текст, не используем data-атрибуты с длинным текстом
    const notification = document.getElementById("notification");
    if (notification) {
        notification.textContent = safeMessage;
        notification.className = `notification ${type}`;
        notification.style.display = "block";
        setTimeout(() => {
            notification.style.display = "none";
        }, duration);
    }
};

// Показывает индикатор набора текста ассистентом и статус подготовки
function showTypingIndicatorWithStatus() {
    const messagesContainer = document.getElementById("messages-container");
    if (!messagesContainer) {
        console.error("Контейнер сообщений не найден");
        return;
    }

    // Проверяем, существует ли уже индикатор
    let indicator = document.getElementById("typing-indicator-container");
    if (indicator) {
        indicator.style.display = "flex";
        return;
    }

    // Создаем новый индикатор
    const container = document.createElement("div");
    container.className = "message message-assistant";
    container.id = "typing-indicator-container";

    // Индикатор с анимированными точками
    const typingIndicator = document.createElement("div");
    typingIndicator.className = "typing-indicator";
    typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    container.appendChild(typingIndicator);

    // Статус
    const statusDiv = document.createElement("div");
    statusDiv.className = "typing-status";
    statusDiv.style.marginLeft = "10px";
    statusDiv.style.fontSize = "12px";
    statusDiv.style.color = "rgba(255, 255, 255, 0.7)";
    container.appendChild(statusDiv);

    messagesContainer.appendChild(container);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Последовательность статусов с индивидуальными задержками
    const statuses = [
        { text: "Анализ запроса...", delay: 700 },
        { text: "Поиск релевантных документов...", delay: 200 },
        { text: "Извлечение ключевой информации...", delay: 950 },
        { text: "Формирование ответа...", delay: 2000 },
        { text: "Финальная проверка...", delay: 200 }
    ];
    let statusIdx = 0;
    statusDiv.textContent = statuses[0].text;
    window._typingStatusTimeout = setTimeout(() => {
        statusIdx = (statusIdx + 1) % statuses.length;
        showNextStatus();
    }, statuses[0].delay);
}

function hideTypingIndicatorWithStatus() {
    const indicator = document.getElementById("typing-indicator-container");
    if (indicator) {
        indicator.remove();
    }
    if (window._typingStatusTimeout) {
        clearTimeout(window._typingStatusTimeout);
        window._typingStatusTimeout = null;
    }
}

// --- Заменяем showTypingIndicator/hideTypingIndicator на новые ---
window.showTypingIndicator = showTypingIndicatorWithStatus;
window.hideTypingIndicator = hideTypingIndicatorWithStatus;

function showNextStatus() {
    statusDiv.textContent = statuses[statusIdx].text;
    window._typingStatusTimeout = setTimeout(() => {
        statusIdx = (statusIdx + 1) % statuses.length;
        showNextStatus();
    }, statuses[statusIdx].delay);
}