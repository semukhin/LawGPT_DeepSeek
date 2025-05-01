/**
 * Модуль для обработки загрузки и скачивания файлов
 * @version 1.0.0
 */

// Проверяем, не существует ли уже FileUploader
if (typeof window.FileUploader === 'undefined') {
    class FileUploader {
        constructor() {
            this.fileInput = document.getElementById('file-upload');
            this.maxFileSize = 50 * 1024 * 1024; // 50 МБ
            this.allowedFileTypes = [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'image/jpeg',
                'image/png',
                'text/plain'
            ];
            this.fileUploadProgress = document.getElementById('file-upload-progress');
            this.fileUploadProgressBar = document.getElementById('file-upload-progress-bar');
            this.fileInfoContainer = document.getElementById('file-info-container');
            this.chatForm = document.getElementById('chat-form');

            // Инициализация
            this.init();
        }

        init() {
            // Проверяем наличие элементов интерфейса
            if (this.fileInput) {
                console.log('Инициализация модуля загрузки файлов');
                this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
            }

            // Инициализация функций скачивания
            this.patchAppJsDownloadFunction();

            // Создаем элементы для отображения прогресса загрузки, если их нет
            if (!this.fileUploadProgress) {
                const progressContainer = document.createElement('div');
                progressContainer.id = 'file-upload-progress';
                progressContainer.className = 'file-upload-progress';

                const progressBar = document.createElement('div');
                progressBar.id = 'file-upload-progress-bar';
                progressBar.className = 'file-upload-progress-bar';

                progressContainer.appendChild(progressBar);
                if(this.chatForm) this.chatForm.appendChild(progressContainer);

                this.fileUploadProgress = progressContainer;
                this.fileUploadProgressBar = progressBar;
            }

            // Создаем контейнер для информации о файле, если его нет
            if (!this.fileInfoContainer) {
                const infoContainer = document.createElement('div');
                infoContainer.id = 'file-info-container';
                infoContainer.className = 'file-info-container';
                if(this.chatForm) this.chatForm.appendChild(infoContainer);
                this.fileInfoContainer = infoContainer;
            }
        }

        /**
         * Обработчик выбора файла
         * @param {Event} event - Событие выбора файла
         */
        handleFileSelect(event) {
            const file = event.target.files[0];

            if (!file) return;

            // Проверка размера файла
            if (file.size > this.maxFileSize) {
                showNotification(`Размер файла превышает ${this.maxFileSize / (1024 * 1024)} МБ`, 'error');
                event.target.value = '';
                return;
            }

            // Проверка типа файла
            const allowedTypes = ['.pdf', '.doc', '.docx', '.xlsx', '.jpg', '.jpeg', '.tif', '.tiff'];
            const fileType = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            if (!this.allowedFileTypes.includes(file.type) && !allowedTypes.includes(fileType)) {
                showNotification('Этот тип файла не поддерживается', 'error');
                event.target.value = '';
                return;
            }

            // Показываем предпросмотр файла
            this.showFilePreview(file);
            this.displayFileInfo(file);
            const sendBtn = document.getElementById('send-btn');
            if (sendBtn) sendBtn.removeAttribute('disabled');
        }

        /**
         * Показывает предпросмотр выбранного файла
         * @param {File} file - Выбранный файл
         */
        showFilePreview(file) {
            const fileNameElement = document.getElementById('file-name');
            if (fileNameElement) {
                fileNameElement.textContent = file.name;
            }

            const uploadPreview = document.getElementById('upload-preview');
            if (uploadPreview) {
                uploadPreview.classList.remove('hidden');
            }
        }

        /**
         * Отображение информации о файле
         * @param {File} file
         */
        displayFileInfo(file) {
            if (!file) return;

            const fileName = file.name;
            const fileSize = this.formatFileSize(file.size);
            const fileExtension = fileName.split('.').pop().toLowerCase();

            this.fileInfoContainer.innerHTML = `
                <div class="file-meta file-${fileExtension}">
                    <div class="file-icon">${this.getFileIcon(fileExtension)}</div>
                    <div class="file-name">${fileName}</div>
                    <div class="file-size">${fileSize}</div>
                    <button type="button" class="file-remove-button" aria-label="Удалить файл">×</button>
                </div>
            `;

            // Обработчик для кнопки удаления файла
            const removeButton = this.fileInfoContainer.querySelector('.file-remove-button');
            if (removeButton) {
                removeButton.addEventListener('click', () => {
                    this.removeUploadedFile();
                });
            }
        }

        /**
         * Удаляет загруженный файл
         */
        removeUploadedFile() {
            this.fileInput.value = '';
            this.fileInfoContainer.innerHTML = '';
            this.fileUploadProgress.classList.remove('active');
            this.fileUploadProgressBar.style.width = '0%';

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
         * Патчит глобальную функцию скачивания файла из app.js
         */
        patchAppJsDownloadFunction() {
            // Глобальная функция для скачивания распознанного текста
            window.downloadRecognizedText = (text, filename) => {
                this.downloadRecognizedText(text, filename);
            };
        }

        /**
         * Скачивает распознанный текст как файл
         * @param {string|Object} content - Текст или объект Gemini API для скачивания
         * @param {string} filename - Имя файла
         */
        async downloadRecognizedText(content, filename) {
            // Создаём красивый индикатор загрузки с этапами обработки
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'download-loading-indicator';

            // Добавляем стили для индикатора, если их еще нет
            if (!document.getElementById('file-upload-styles')) {
                const style = document.createElement('style');
                style.id = 'file-upload-styles';
                style.textContent = `
                    .download-loading-indicator {
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        background: rgba(0, 0, 0, 0.8);
                        color: white;
                        padding: 20px 30px;
                        border-radius: 10px;
                        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
                        z-index: 10000;
                        text-align: center;
                        min-width: 300px;
                        font-size: 16px;
                        font-weight: bold;
                    }

                    .download-loading-indicator:after {
                        content: '';
                        display: block;
                        width: 0;
                        height: 3px;
                        background: #4CAF50;
                        margin-top: 10px;
                        animation: progress 5s linear forwards;
                    }

                    @keyframes progress {
                        0% { width: 0; }
                        100% { width: 100%; }
                    }

                    .file-meta {
                        display: flex;
                        align-items: center;
                        padding: 10px;
                        background: #f5f5f5;
                        border-radius: 8px;
                        margin-bottom: 10px;
                        border: 1px solid #ddd;
                    }

                    .file-icon {
                        margin-right: 10px;
                        color: #2196F3;
                    }

                    .file-name {
                        flex: 1;
                        font-weight: bold;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }

                    .file-size {
                        color: #666;
                        margin: 0 10px;
                    }

                    .file-remove-button {
                        background: none;
                        border: none;
                        color: #f44336;
                        font-size: 20px;
                        cursor: pointer;
                        padding: 0 8px;
                    }

                    .download-btn {
                        display: inline-block;
                        background: #4CAF50;
                        color: white;
                        padding: 10px 20px;
                        margin: 10px 0;
                        border-radius: 4px;
                        text-decoration: none;
                        font-weight: bold;
                        text-align: center;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                        transition: all 0.3s ease;
                    }

                    .download-btn:hover {
                        background: #45a049;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                        transform: translateY(-2px);
                    }
                `;
                document.head.appendChild(style);
            }

            // Определяем список статусов и времени их показа
            const processingSteps = [
                { message: "Подготовка распознанного текста...", delay: 800 },
                { message: "Обработка полного текста документа...", delay: 600 },
                { message: "Форматирование документа...", delay: 700 },
                { message: "Подготовка к скачиванию...", delay: 500 },
                { message: "Сохранение документа...", delay: 400 }
            ];

            // Начинаем с первого статуса
            loadingIndicator.innerHTML = `<span>${processingSteps[0].message}</span>`;
            document.body.appendChild(loadingIndicator);

            // Функция смены индикатора
            let currentStepIndex = 0;
            const stepTimer = setInterval(() => {
                currentStepIndex++;
                if (currentStepIndex < processingSteps.length) {
                    loadingIndicator.innerHTML = `<span>${processingSteps[currentStepIndex].message}</span>`;
                } else {
                    clearInterval(stepTimer);
                }
            }, 1000); // Каждую секунду меняем статус

            try {
                console.log('Запуск скачивания распознанного текста...');

                // Функция для гарантированного удаления индикатора загрузки
                const removeLoader = () => {
                    clearInterval(stepTimer);
                    if (document.body.contains(loadingIndicator)) {
                        document.body.removeChild(loadingIndicator);
                        console.log('Индикатор загрузки удален');
                    }
                };

                // Убеждаемся, что расширение файла всегда будет с .txt расширением
                let downloadFilename = this.ensureTxtExtension(filename);
                console.log('Итоговое имя файла для скачивания:', downloadFilename);

                // Проверяем, является ли content объектом Gemini API Response
                if (content && typeof content === 'object' && content.toString().includes('GenerateContentResponse')) {
                    console.log('Обнаружен объект ответа Gemini API, извлекаем текст...');
                    // Попытка извлечь текст из объекта Gemini API
                    try {
                        // Пробуем различные свойства, которые могут содержать текст
                        let extractedText = '';

                        if (typeof content.text === 'function') {
                            extractedText = content.text();
                        } else if (content.text) {
                            extractedText = content.text;
                        } else if (content.candidates && content.candidates[0] && content.candidates[0].content) {
                            // Проверяем структуру объекта candidates
                            if (content.candidates[0].content.parts && content.candidates[0].content.parts[0]) {
                                if (typeof content.candidates[0].content.parts[0].text === 'string') {
                                    extractedText = content.candidates[0].content.parts[0].text;
                                } else if (content.candidates[0].content.parts[0].text) {
                                    // Если текст есть, но не является строкой
                                    extractedText = String(content.candidates[0].content.parts[0].text);
                                }
                            }
                        } 

                        // Если всё еще не получили текст, пробуем получить полное текстовое представление объекта
                        if (!extractedText && content._response) {
                            extractedText = content._response.text();
                        }

                        // Последняя попытка - преобразовать объект в строку
                        if (!extractedText) {
                            // Если не удалось извлечь текст, используем строковое представление объекта
                            extractedText = "Извлеченный текст из документа:\n\n" + String(content);
                        }

                        // Проверка, что получили не пустой текст
                        if (!extractedText.trim()) {
                            extractedText = "Не удалось извлечь текст из документа. Попробуйте еще раз.";
                        }

                        console.log(`Размер извлеченного текста: ${extractedText.length} символов`);
                        
                        // Гарантируем, что имя файла будет с расширением .txt
                        downloadFilename = this.ensureTxtExtension(downloadFilename || 'recognized_text.txt');
                        console.log('Имя файла для сохранения:', downloadFilename);
                        
                        await this.downloadAsText(extractedText, downloadFilename);
                        removeLoader();
                        return;
                    } catch (extractError) {
                        console.error('Ошибка при извлечении текста из объекта Gemini:', extractError);
                        // Продолжаем выполнение других методов
                    }
                }

                // Если content - это текст, а не URL, создаем blob и скачиваем напрямую
                if (content && typeof content === 'string' && content.length > 0 && !content.startsWith('http') && !content.startsWith('/')) {
                    console.log(`Прямое скачивание текстового контента размером ${content.length} символов`);
                    await this.downloadAsText(content, downloadFilename);
                    removeLoader();
                    return;
                }

                // Получаем токен из localStorage
                const token = localStorage.getItem(config && config.storageTokenKey ? config.storageTokenKey : 'lawgpt_token');

                // Для URL-адресов
                if (content && typeof content === 'string' && (content.startsWith('http') || content.startsWith('/'))) {
                    // Проверяем, является ли это API-запросом для скачивания
                    if (content.includes('/api/download')) {
                        await this.downloadFromApi(content, downloadFilename, token);
                    } else {
                        await this.downloadFromDirectUrl(content, downloadFilename);
                    }
                    removeLoader();
                    return;
                }

                // Если не удалось определить способ скачивания
                console.error('Не удалось определить способ скачивания', typeof content, content);
                removeLoader();
                showNotification('Ошибка при скачивании файла: неизвестный формат данных', 'error');

            } catch (error) {
                console.error('Ошибка при скачивании распознанного текста:', error);
                showNotification(`Ошибка при скачивании: ${error.message}`, 'error');

                // Удаляем индикатор загрузки
                clearInterval(stepTimer);
                if (document.body.contains(loadingIndicator)) {
                    document.body.removeChild(loadingIndicator);
                }
            } finally {
                // Гарантированное удаление индикатора загрузки через таймаут
                setTimeout(() => {
                    clearInterval(stepTimer);
                    if (document.body.contains(loadingIndicator)) {
                        document.body.removeChild(loadingIndicator);
                        console.log('Индикатор загрузки удален через таймаут');
                    }
                }, 2000); // 2 секунды максимальное время жизни индикатора
            }
        }

        /**
         * Убеждается, что имя файла имеет расширение .txt
         * @param {string} filename - Имя файла
         * @returns {string} - Имя файла с расширением .txt
         */
        ensureTxtExtension(filename) {
            if (!filename) {
                return 'recognized_text.txt';
            }

            // Убираем все кавычки из имени файла
            filename = filename.replace(/["']/g, '');

            // Получаем имя без расширения
            let basename = filename.replace(/\.[^/.]+$/, '');
            
            // Удаляем временные метки из имени
            basename = basename.replace(/^\d{8}_\d{6}_/, '');
            
            // Удаляем технические суффиксы
            basename = basename.replace(/(_recognized|_ocr|_text|_extracted)(?=\.|$)/gi, '');

            // Добавляем суффикс _recognized если его нет
            if (!basename.includes('_recognized')) {
                basename += '_recognized';
            }

            // Возвращаем имя с расширением .txt
            return `${basename}.txt`;
        }

        /**
         * Скачивает текст как файл
         * @param {string} text - Текст для скачивания
         * @param {string} filename - Имя файла
         */
        async downloadAsText(text, filename) {
            try {
                // Гарантируем расширение .txt для файла
                filename = this.ensureTxtExtension(filename);
                console.log(`📄 Подготовка к скачиванию текста как ${filename}`);

                // Декодируем text если это строка в формате URL-encoded
                let contentText;
                try {
                    contentText = decodeURIComponent(text);
                } catch (decodeError) {
                    // Если декодирование не удалось, используем исходный текст
                    console.log('Текст не требует декодирования, используем как есть');
                    contentText = text;
                }

                // Проверяем размер текста и логируем для отладки
                console.log(`Размер текста для скачивания: ${contentText.length} символов`);

                // Проверка текста на целостность и вывод информации
                if (contentText.length > 0) {
                    console.log(`Первые 100 символов: "${contentText.substring(0, 100)}..."`);
                    console.log(`Последние 100 символов: "...${contentText.substring(contentText.length - 100)}"`);
                }

                // Показываем уведомление о размере скачиваемого текста
                if (contentText.length > 5000) {
                    showNotification(`Подготовка к скачиванию ${Math.round(contentText.length/1000)}КБ текста...`, 'info');
                }

                // Создаем Blob для скачивания с явным указанием кодировки
                const blob = new Blob([contentText], { type: 'text/plain;charset=utf-8' });
                const url = window.URL.createObjectURL(blob);

                // Создаем ссылку для скачивания и стилизуем ее красиво для видимости
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                    a.click();

                // Очищаем ресурсы
                    setTimeout(() => {
                            window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showNotification('Файл успешно скачан', 'success');
                }, 100);

            } catch (error) {
                console.error('Ошибка при скачивании текста:', error);
                showNotification(`Ошибка при скачивании: ${error.message}`, 'error');
                throw error;
            }
        }

        /**
         * Скачивает файл по URL из API
         * @param {string} apiUrl - URL API для скачивания
         * @param {string} filename - Имя файла
         * @param {string} token - Токен авторизации
         */
        async downloadFromApi(apiUrl, filename, token) {
            try {
                const response = await fetch(apiUrl, {
                    method: 'GET',
                    headers: {
                        'Authorization': token ? `Bearer ${token}` : '',
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ошибка ${response.status}`);
                }

                // Получаем заголовок Content-Disposition для определения имени файла
                const contentDisposition = response.headers.get('Content-Disposition');
                let serverFilename = null;

                if (contentDisposition) {
                    // Извлекаем имя файла из заголовка Content-Disposition
                    const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                    if (filenameMatch && filenameMatch[1]) {
                        serverFilename = filenameMatch[1];
                        console.log('Получено имя файла из сервера:', serverFilename);
                    }
                }

                // Используем имя файла с сервера, если оно есть, иначе используем переданное имя
                const downloadFilename = serverFilename || filename;
                console.log('Итоговое имя файла для скачивания:', downloadFilename);

                // Получаем Blob из ответа
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);

                // Создаем и активируем ссылку для скачивания
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = downloadFilename;
                document.body.appendChild(a);
                a.click();

                // Удаляем индикатор загрузки, если он есть
                const loadingIndicator = document.querySelector('.download-loading-indicator');
                if (loadingIndicator) {
                    document.body.removeChild(loadingIndicator);
                }

                setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }, 100);

                showNotification('Файл успешно скачан', 'success');
            } catch (error) {
                console.error('Ошибка при скачивании файла из API:', error);
                throw error;
            }
        }

        /**
         * Скачивает файл напрямую по URL
         * @param {string} fileUrl - URL файла
         * @param {string} filename - Имя файла
         */
        async downloadFromDirectUrl(fileUrl, filename) {
            // ВАЖНО: Принудительно меняем расширение в URL, если оно не .txt
            if (!fileUrl.toLowerCase().endsWith('.txt')) {
                console.log('Преобразование URL для скачивания в .txt:', fileUrl);
                fileUrl = fileUrl.replace(/\.[^/.]+$/, '') + '.txt';
                console.log('Новый URL с расширением .txt:', fileUrl);
            }

            // Вместо прямой ссылки для скачивания используем fetch с перезаписью типа
            try {
                const response = await fetch(fileUrl);
                const blob = await response.blob();

                // ПРИНУДИТЕЛЬНО устанавливаем тип MIME как text/plain
                const newBlob = new Blob([await blob.text()], { type: 'text/plain;charset=UTF-8' });

                const url = window.URL.createObjectURL(newBlob);

                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();

                setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }, 100);

                showNotification('Файл успешно скачан', 'success');
            } catch (error) {
                console.error('Ошибка при скачивании файла по прямой ссылке:', error);
                throw error;
            }
        }

        // Получение иконки на основе типа файла
        getFileIcon(fileType) {
            const iconMap = {
                'pdf': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
                'doc': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
                'docx': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
                'xlsx': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
                'jpg': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="7" x2="8" y2="7"></line></svg>',
                'jpeg': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="7" x2="8" y2="7"></line></svg>',
                'tiff': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="7" x2="8" y2="7"></line></svg>',
                'tif': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="7" x2="8" y2="7"></line></svg>'
            };

            return iconMap[fileType] || iconMap['doc'];
        }

        // Форматирование размера файла
        formatFileSize(bytes) {
            if (bytes === 0) return '0 Байт';

            const k = 1024;
            const sizes = ['Байт', 'КБ', 'МБ', 'ГБ'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));

            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    }

    // Создаем и экспортируем экземпляр класса
    window.fileUploader = new FileUploader();
} else {
    console.warn('FileUploader уже определен. Пропускаем повторную инициализацию.');
}

// Добавляем глобальные обработчики
document.addEventListener('DOMContentLoaded', function() {
    // Обработчик для кнопки удаления файла
    const removeFileBtn = document.getElementById('remove-file-btn');
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', () => {
            window.fileUploader.removeUploadedFile();
        });
    }

    // Вызываем патч функции при загрузке скрипта
    window.fileUploader.patchAppJsDownloadFunction();

    //Функция для показа уведомлений
    // Функция для отображения уведомлений
    function createNotification(message, type = 'info', duration = 3000) {
        // Предотвращаем дублирование уведомлений с тем же сообщением
        const existingNotification = document.querySelector(`.notification[data-message="${message}"]`);
        if (existingNotification) {
            return;
        }

        // Создаем контейнер для уведомлений, если его еще нет
        let notificationsContainer = document.getElementById('notifications-container');
        if (!notificationsContainer) {
            notificationsContainer = document.createElement('div');
            notificationsContainer.id = 'notifications-container';
            document.body.appendChild(notificationsContainer);
        }

        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.setAttribute('data-message', message);
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-message">${message}</div>
                <button class="notification-close">&times;</button>
            </div>
        `;

        // Добавляем уведомление в контейнер
        notificationsContainer.appendChild(notification);

        // Добавляем слушатель для закрытия уведомления
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.classList.add('hiding');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        });

        // Показываем уведомление (для анимации)
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // Автоматически скрываем уведомление через указанное время
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.add('hiding');
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.parentNode.removeChild(notification);
                        }
                    }, 300);
                }
            }, duration);
        }

        // Логируем для отладки
        console.log("Показано уведомление:", message);

        // Возвращаем DOM элемент уведомления для возможных дальнейших манипуляций
        return notification;
    }

    // Экспортируем функцию во внешний интерфейс
    window.showNotification = function(message, type = 'info', duration = 3000) {
        console.log("Итоговое имя файла для скачивания:", message);
        return createNotification(message, type, duration);
    };

    // Функция для загрузки документа в базу данных пользователя
    async function uploadDocument(event) {
        event.preventDefault();

        // Получаем файл и описание
        const fileInput = document.getElementById('document-file');
        const descriptionInput = document.getElementById('document-description');
        const extractTextCheckbox = document.getElementById('extract-text-checkbox');

        if (!fileInput.files || fileInput.files.length === 0) {
            showNotification('Выберите файл для загрузки', 'error');
            return;
        }

        const file = fileInput.files[0];
        const description = descriptionInput.value;
        const extractText = extractTextCheckbox && extractTextCheckbox.checked;

        // Создаем FormData для отправки файла
        const formData = new FormData();
        formData.append('file', file);
        if (description) {
            formData.append('description', description);
        }
        if (extractText) {
            formData.append('extract_text', 'true');
        }

        showLoading();

        try {
            // Отправляем запрос с токеном аутентификации
            const token = localStorage.getItem(config.storageTokenKey);

            const response = await fetch('/api/user/upload-document', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                hideLoading();

                // Показываем извлеченный текст, если он есть
                if (data.extracted_text) {
                    // Создаем модальное окно для отображения извлеченного текста
                    showExtractedTextModal(data.extracted_text, data.document.file_name);
                } else {
                    showNotification('Документ успешно загружен', 'success');

                    // Очищаем форму
                    fileInput.value = '';
                    descriptionInput.value = '';

                    // Закрываем модальное окно
                    closeModal('document-upload-modal');
                }

                // Обновляем список документов, если функция существует
                if (typeof loadUserDocuments === 'function') {
                    loadUserDocuments();
                }
            } else {
                hideLoading();
                showNotification(`Ошибка при загрузке документа: ${data.detail || 'неизвестная ошибка'}`, 'error');
            }
        } catch(error) {
            hideLoading();
            showNotification(`Ошибка при загрузке документа: ${error.message}`, 'error');
        }
    }

    /**
     * Показывает модальное окно с извлеченным текстом
     * @param {string} text - Извлеченный текст
     * @param {string} fileName - Имя файла
     */
    function showExtractedTextModal(text, fileName) {
        let modal = document.getElementById('extracted-text-modal');
        if (!modal) {
            // Если модальное окно не существует, создаем его
            modal = document.createElement('div');
            modal.id = 'extracted-text-modal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Извлеченный текст</h2>
                        <span class="close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <p class="file-name"></p>
                        <div class="extracted-text-container">
                            <textarea class="extracted-text" readonly></textarea>
                        </div>
                        <div class="button-container">
                            <button id="copy-text-button" class="btn btn-primary">Копировать текст</button>
                            <button id="close-extract-modal-button" class="btn btn-secondary">Закрыть</button>
                        </div>
                        <div id="download-container"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Добавляем обработчики событий
            const closeBtn = modal.querySelector('.close');
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
                // Очищаем форму загрузки документа
                document.getElementById('document-file').value = '';
                document.getElementById('document-description').value = '';
                closeModal('document-upload-modal');
            });

            const closeButton = modal.querySelector('#close-extract-modal-button');
            closeButton.addEventListener('click', () => {
                modal.style.display = 'none';
                // Очищаем форму загрузки документа
                document.getElementById('document-file').value = '';
                document.getElementById('document-description').value = '';
                closeModal('document-upload-modal');
            });

            const copyButton = modal.querySelector('#copy-text-button');
            copyButton.addEventListener('click', () => {
                const textArea = modal.querySelector('.extracted-text');
                textArea.select();
                document.execCommand('copy');
                showNotification('Текст скопирован в буфер обмена', 'success');
            });
        }

        modal.querySelector('.file-name').textContent = `Файл: ${fileName}`;
        modal.querySelector('.extracted-text').value = text;

        // Настраиваем кнопку скачивания текста
        setupDownloadButton(text, fileName);

        // Показываем модальное окно
        modal.style.display = 'block';
    }

    /**
     * Настраивает кнопку скачивания текста
     * @param {string} text - Извлеченный текст
     * @param {string} filename - Имя файла (опционально)
     */
    function setupDownloadButton(text, filename) {
        const container = document.getElementById('download-container');
        container.innerHTML = '';

        if (text) {
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'download-btn';
            downloadBtn.innerHTML = '<i class="fas fa-file-download"></i> Скачать распознанный текст';
            
            // Гарантируем расширение .txt для имени файла
            const txtFilename = filename ? 
                (filename.toLowerCase().endsWith('.txt') ? filename : filename.replace(/\.[^/.]+$/, '') + '.txt') 
                : 'recognized_text.txt';
            
            downloadBtn.addEventListener('click', () => {
                handleDownloadClick(`/api/download/${txtFilename}`);
            });
            
            container.appendChild(downloadBtn);
        }

        container.style.display = text ? 'flex' : 'none';
    }

    // Привязываем функцию uploadDocument к форме загрузки документа
    const documentUploadForm = document.getElementById('document-upload-form');
    if (documentUploadForm) {
        documentUploadForm.addEventListener('submit', uploadDocument);
    }

    //Функции showLoading и hideLoading (предполагается их наличие в другом месте кода)
    function showLoading(){
        //Здесь реализация показа индикатора загрузки
    }

    function hideLoading(){
        //Здесь реализация скрытия индикатора загрузки
    }

    function closeModal(modalId){
        //Здесь реализация закрытия модального окна
    }
});

/**
 * Показывает индикатор прогресса распознавания
 * @param {Object} status - Объект с информацией о статусе
 */
function updateRecognitionStatus(status) {
    let statusContainer = document.getElementById('recognition-status');
    if (!statusContainer) {
        statusContainer = document.createElement('div');
        statusContainer.id = 'recognition-status';
        statusContainer.className = 'recognition-status';
        document.getElementById('messages-container').appendChild(statusContainer);
    }

    const progress = Math.round(status.progress);
    const timeElapsed = status.time_elapsed ? Math.round(status.time_elapsed) : 0;

    statusContainer.innerHTML = `
        <div class="recognition-header">
            <span class="recognition-text">${status.message}</span>
            <span class="recognition-percent">${progress}%</span>
        </div>
        <div class="recognition-progress-bar">
            <div class="recognition-progress-fill" style="width: ${progress}%"></div>
        </div>
        <div class="recognition-details">
            Время обработки: ${timeElapsed} сек
        </div>
    `;

    // Если процесс завершен, добавляем класс для анимации
    if (progress === 100) {
        statusContainer.querySelector('.recognition-progress-fill').classList.add('complete');
        
        // Через 3 секунды скрываем индикатор
        setTimeout(() => {
            statusContainer.classList.add('fade-out');
            setTimeout(() => statusContainer.remove(), 500);
        }, 3000);
    }
}

/**
 * Обработчик загрузки файла с отображением предпросмотра
 * @param {Event} e - Событие загрузки файла
 */
async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    // Проверка размера файла
    if (file.size > config.maxFileSize) {
        showNotification(`Размер файла превышает ${config.maxFileSize / (1024 * 1024)} МБ`, 'error');
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
}

/**
 * Обработчик клика по кнопке скачивания
 * @param {string} downloadUrl - URL для скачивания
 */
async function handleDownloadClick(downloadUrl) {
    try {
        // Убеждаемся, что URL ведет на .txt файл
        if (!downloadUrl.toLowerCase().endsWith('.txt')) {
            downloadUrl = downloadUrl.replace(/\.[^/.]+$/, '') + '.txt';
        }
        
        const response = await fetch(downloadUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Получаем имя файла из заголовка Content-Disposition или из URL
        let filename = '';
        const contentDisposition = response.headers.get('Content-Disposition');
        if (contentDisposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        // Если имя файла не получено из заголовка, берем из URL
        if (!filename) {
            filename = downloadUrl.split('/').pop();
        }
        
        // Гарантируем расширение .txt
        if (!filename.toLowerCase().endsWith('.txt')) {
            filename = filename.replace(/\.[^/.]+$/, '') + '.txt';
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        
        document.body.appendChild(a);
        a.click();
        
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showNotification('Файл успешно скачан', 'success');
    } catch (error) {
        console.error('Ошибка при скачивании:', error);
        showNotification(`Ошибка при скачивании: ${error.message}`, 'error');
    }
}