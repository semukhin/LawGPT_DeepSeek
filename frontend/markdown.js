/**
 * Улучшенный модуль для обработки Markdown в сообщениях
 * Включает расширенную обработку кодовых блоков, специальных символов и элементов Markdown
 */

// Настройка Markdown.js и highlight.js
const configureMarkdown = () => {
    markdown.setOptions({
        renderer: createCustomRenderer(),
        highlight: highlightCode,
        gfm: true,                 // GitHub Flavored Markdown
        breaks: true,              // Поддержка переводов строк
        pedantic: false,           // Не строгий режим
        sanitize: false,           // Разрешаем HTML
        smartypants: true,         // Типографские улучшения
        xhtml: false               // Не требуем закрытия тегов в стиле XHTML
    });
};

/**
 * Создаёт кастомный рендерер для Markdown.js с улучшенным форматированием
 * @returns {markdown.Renderer} - Кастомный рендерер для Markdown.js
 */
const createCustomRenderer = () => {
    const renderer = new markdown.Renderer();
    
    // Улучшенная обработка кодовых блоков с поддержкой Mermaid
    renderer.code = (code, language) => {
        // Специальная обработка для Mermaid диаграмм
        if (language === 'mermaid') {
            return `<div class="mermaid">${code}</div>`;
        }
        
        // Для обычного кода используем highlight.js
        const validLanguage = hljs.getLanguage(language) ? language : 'plaintext';
        const highlightedCode = hljs.highlight(validLanguage, code).value;
        
        return `
            <pre class="code-block-container">
                <code class="hljs language-${validLanguage}">${highlightedCode}</code>
                <button class="copy-code-button" title="Копировать код">
                    <i class="fas fa-copy"></i>
                </button>
            </pre>
        `;
    };
    
    // Кастомизация ссылок с безопасностью и внешними индикаторами
    renderer.link = (href, title, text) => {
        const safeHref = encodeURI(href);
        const titleAttr = title ? ` title="${title}"` : '';
        const isExternal = /^https?:\/\//.test(href);
        
        return `
            <a href="${safeHref}"${titleAttr}
                ${isExternal ? 'target="_blank" rel="noopener noreferrer"' : ''}>
                ${text}
                ${isExternal ? '<i class="fas fa-external-link-alt" style="margin-left: 4px; font-size: 0.8em;"></i>' : ''}
            </a>
        `;
    };
    
    // Расширенная обработка заголовков с якорями
    renderer.heading = (text, level) => {
        const escapedText = text.toLowerCase().replace(/[^\w]+/g, '-');
        return `
            <h${level} id="${escapedText}">
                ${text}
                <a href="#${escapedText}" class="header-anchor">#</a>
            </h${level}>
        `;
    };
    
    // Улучшенное форматирование таблиц
    renderer.table = (header, body) => `
        <div class="table-responsive">
            <table class="markdown-table">
                <thead>${header}</thead>
                <tbody>${body}</tbody>
            </table>
        </div>
    `;
    
    // Улучшенное отображение цитат
    renderer.blockquote = (quote) => {
        return `<blockquote class="elegant-quote">${quote}</blockquote>`;
    };

    return renderer;
};

/**
 * Подсветка синтаксиса кода с использованием highlight.js
 * @param {string} code - Код для подсветки
 * @param {string} lang - Язык кода
 * @returns {string} - HTML с подсвеченным кодом
 */
const highlightCode = (code, lang) => {
    if (!lang || lang === 'plaintext') {
        return hljs.highlightAuto(code).value;
    }
    
    try {
        // Пытаемся использовать указанный язык
        return hljs.highlight(lang, code).value;
    } catch (e) {
        // В случае ошибки используем автоматическое определение
        return hljs.highlightAuto(code).value;
    }
};

/**
 * Преобразует текст с разметкой Markdown в HTML с форматированием
 * @param {string} text - Текст в формате Markdown
 * @returns {string} - HTML с отформатированным текстом
 */
const markdownToHtml = (text) => {
    // Проверяем настроен ли markdown.js
    if (!window.markdown) {
        console.error('Markdown.js не загружен');
        return escapeHtml(text);
    }
    
    try {
        // Выполняем преобразование Markdown в HTML
        return markdown.parse(text);
    } catch (error) {
        console.error('Ошибка при обработке Markdown:', error);
        // В случае ошибки возвращаем безопасный HTML
        return escapeHtml(text);
    }
};

/**
 * Безопасное экранирование HTML для предотвращения XSS
 * @param {string} text - Исходный текст
 * @returns {string} - Экранированный HTML
 */
const escapeHtml = (text) => {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

/**
 * Обработка сообщений при добавлении в DOM
 * @param {HTMLElement} messageElement - DOM элемент сообщения
 */
const processMessage = (messageElement) => {
    // Применяем Markdown только к сообщениям ассистента
    if (messageElement.classList.contains('message-assistant')) {
        const contentElement = messageElement.querySelector('.message-content');
        
        if (contentElement) {
            const rawContent = contentElement.innerHTML;
            
            // Проверяем, содержит ли сообщение форматирование Markdown
            const hasMarkdown = /[#*`_~\[\]()]/.test(rawContent) || 
                               /\n\n/.test(rawContent) ||
                               /\d+\.\s/.test(rawContent);
            
            // Применяем Markdown только если в тексте есть признаки разметки
            if (hasMarkdown) {
                const formattedContent = markdownToHtml(rawContent);
                contentElement.innerHTML = formattedContent;
            }
        }
    }
    
    // Инициализация специальных компонентов, если они есть
    initSpecialComponents(messageElement);
};

/**
 * Функция для добавления кнопок копирования в блоки кода
 */
function addCodeCopyButtons() {
    document.querySelectorAll('pre.code-block-container').forEach(container => {
        const copyButton = container.querySelector('.copy-code-button');
        copyButton.addEventListener('click', () => {
            const code = container.querySelector('code').textContent;
            navigator.clipboard.writeText(code).then(() => {
                copyButton.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            }).catch(err => {
                console.error('Ошибка при копировании кода:', err);
                copyButton.innerHTML = '<i class="fas fa-times"></i>';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            });
        });
    });
}

/**
 * Инициализация специальных компонентов внутри сообщения
 * @param {HTMLElement} element - DOM элемент сообщения
 */
const initSpecialComponents = (element) => {
    // Инициализация Mermaid диаграмм
    if (window.mermaid) {
        const mermaidDivs = element.querySelectorAll('.mermaid');
        if (mermaidDivs.length > 0) {
            mermaid.init(undefined, mermaidDivs);
        }
    }
    
    // Добавление кнопок копирования для блоков кода
    const codeBlocks = element.querySelectorAll('pre code');
    codeBlocks.forEach(codeBlock => {
        const pre = codeBlock.parentNode;
        
        // Создаем кнопку копирования
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-code-button';
        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
        copyButton.title = 'Копировать код';
        
        // Добавляем обработчик клика
        copyButton.addEventListener('click', () => {
            const code = codeBlock.textContent;
            
            navigator.clipboard.writeText(code)
                .then(() => {
                    copyButton.innerHTML = '<i class="fas fa-check"></i>';
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                    }, 2000);
                })
                .catch(err => {
                    console.error('Ошибка при копировании кода:', err);
                    copyButton.innerHTML = '<i class="fas fa-times"></i>';
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                    }, 2000);
                });
        });
        
        // Оборачиваем pre в контейнер для позиционирования кнопки
        const container = document.createElement('div');
        container.className = 'code-block-container';
        pre.parentNode.insertBefore(container, pre);
        container.appendChild(pre);
        container.appendChild(copyButton);
    });
}

// Инициализируем Markdown.js при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    if (window.markdown) {
        configureMarkdown();
    }
});

// Экспортируем функции для использования в основном скрипте
const MarkdownProcessor = {
    markdownToHtml,
    processMessage,
    initSpecialComponents,
    escapeHtml
};