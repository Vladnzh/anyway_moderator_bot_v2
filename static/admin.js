// Глобальные переменные
let authToken = localStorage.getItem('adminToken') || '';
let currentTags = [];
let currentTagId = null;

// API базовый URL
const API_BASE = '/api';

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    if (authToken) {
        document.getElementById('tokenInput').value = authToken;
        showAdminPanel();
        loadAllData();
    } else {
        showLoginPrompt();
    }
    
    // Обработчики форм
    document.getElementById('tagForm').addEventListener('submit', saveTag);
    document.getElementById('addTagBtn').addEventListener('click', () => openTagModal());
    
    // Обработчик Enter в поле токена
    document.getElementById('loginToken').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            login();
        }
    });
    
    document.getElementById('tokenInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            login();
        }
    });
});

// === АВТОРИЗАЦИЯ ===
function login() {
    const token = document.getElementById('loginToken').value || document.getElementById('tokenInput').value;
    if (!token) {
        showNotification('Введите токен', 'error');
        return;
    }
    
    authToken = token;
    localStorage.setItem('adminToken', token);
    document.getElementById('tokenInput').value = token;
    
    // Проверяем токен запросом к API
    apiRequest('GET', '/config')
        .then(() => {
            showAdminPanel();
            loadAllData();
            showNotification('Успешная авторизация', 'success');
        })
        .catch(() => {
            logout();
            showNotification('Неверный токен', 'error');
        });
}

function logout() {
    authToken = '';
    localStorage.removeItem('adminToken');
    document.getElementById('tokenInput').value = '';
    document.getElementById('loginToken').value = '';
    showLoginPrompt();
}

function showLoginPrompt() {
    document.getElementById('loginPrompt').style.display = 'flex';
    document.getElementById('adminPanel').style.display = 'none';
    document.getElementById('loginBtn').style.display = 'inline-block';
    document.getElementById('logoutBtn').style.display = 'none';
}

function showAdminPanel() {
    document.getElementById('loginPrompt').style.display = 'none';
    document.getElementById('adminPanel').style.display = 'block';
    document.getElementById('loginBtn').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'inline-block';
}

// === API ЗАПРОСЫ ===
async function apiRequest(method, endpoint, data = null) {
    const url = `${API_BASE}${endpoint}`;
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(url, options);
    const result = await response.json();
    
    if (!response.ok) {
        throw new Error(result.message || 'API Error');
    }
    
    if (!result.success) {
        throw new Error(result.message || 'Request failed');
    }
    
    return result;
}

// === ЗАГРУЗКА ДАННЫХ ===
async function loadAllData() {
    try {
        await Promise.all([
            loadTags(),
            loadStats(),
            loadLogs()
        ]);
    } catch (error) {
        console.error('Error loading data:', error);
        showNotification('Ошибка загрузки данных: ' + error.message, 'error');
    }
}


async function loadTags() {
    try {
        const tagsResponse = await apiRequest('GET', '/tags');
        currentTags = tagsResponse.data;
        renderTags();
        updateTagFilter();
    } catch (error) {
        console.error('Error loading tags:', error);
        showNotification('Ошибка загрузки тегов: ' + error.message, 'error');
    }
}

async function loadStats() {
    try {
        const statsResponse = await apiRequest('GET', '/stats');
        const stats = statsResponse.data;
        
        document.getElementById('totalLogs').textContent = stats.total_logs || 0;
        document.getElementById('totalTags').textContent = currentTags.length || 0;
        
        // Отображаем топ тегов
        const topTagsContainer = document.getElementById('topTags');
        topTagsContainer.innerHTML = '';
        
        if (stats.tag_stats && stats.tag_stats.length > 0) {
            stats.tag_stats.slice(0, 10).forEach(tagStat => {
                const tagElement = document.createElement('div');
                tagElement.className = 'tag-stat';
                tagElement.innerHTML = `
                    <span class="tag">${tagStat.tag}</span>
                    <span class="count">${tagStat.count}</span>
                `;
                topTagsContainer.appendChild(tagElement);
            });
        } else {
            topTagsContainer.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 20px;">Нет данных</div>';
        }
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showNotification('Ошибка загрузки статистики: ' + error.message, 'error');
    }
}

// Старая функция loadLogs удалена (была дублирующаяся)

// === ОТОБРАЖЕНИЕ ДАННЫХ ===
function renderTags() {
    const container = document.getElementById('tagsList');
    container.innerHTML = '';
    
    if (currentTags.length === 0) {
        container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 20px;">Теги не настроены</div>';
        return;
    }
    
    currentTags.forEach((tag, index) => {
        const tagElement = document.createElement('div');
        tagElement.className = 'tag-item';
        
        // Получаем настройки тега или значения по умолчанию
        const matchMode = tag.match_mode || 'equals';
        const requirePhoto = tag.require_photo !== undefined ? tag.require_photo : true;
        const replyOk = tag.reply_ok || '';
        const replyNeedPhoto = tag.reply_need_photo || '';
        const threadName = tag.thread_name || '';
        
        tagElement.innerHTML = `
            <div class="tag-info">
                <div class="tag-field">
                    <label>Тег</label>
                    <div class="value">${tag.tag}</div>
                </div>
                <div class="tag-field">
                    <label>Реакция</label>
                    <div class="value">${tag.emoji}</div>
                </div>
                <div class="tag-field">
                    <label>Задержка</label>
                    <div class="value">${tag.delay || 0} сек</div>
                </div>
                <div class="tag-field">
                    <label>Режим</label>
                    <div class="value">${matchMode === 'prefix' ? 'Префикс' : 'Строгий'}</div>
                </div>
                <div class="tag-field">
                    <label>Медиа</label>
                    <div class="value">${requirePhoto ? '✅ Требуется' : '❌ Не требуется'}</div>
                </div>
                <div class="tag-field">
                    <label>Тред</label>
                    <div class="value">${threadName || '🌐 Любой'}</div>
                </div>
                <div class="tag-field">
                    <label>Модерация</label>
                    <div class="value">${tag.moderation_enabled ? '🔍 Включена' : '⚡ Авто'}</div>
                </div>
            </div>
            <div class="tag-actions">
                <button class="btn btn-secondary btn-small" onclick="editTag('${tag.id}')">✏️ Настроить</button>
                <button class="btn btn-danger btn-small" onclick="deleteTag('${tag.id}')">🗑️ Удалить</button>
            </div>
        `;
        container.appendChild(tagElement);
    });
}

function renderLogs(logs) {
    const container = document.getElementById('logsContainer');
    container.innerHTML = '';
    
    if (!logs || logs.length === 0) {
        container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 20px;">Нет записей</div>';
        return;
    }
    
    // Заголовок таблицы
    const header = document.createElement('div');
    header.className = 'log-header';
    header.innerHTML = `
        <div>Время (UTC)</div>
        <div>Пользователь</div>
        <div>Чат</div>
        <div>Теги</div>
        <div>Текст</div>
    `;
    container.appendChild(header);
    
    // Записи
    logs.forEach(log => {
        const logElement = document.createElement('div');
        logElement.className = 'log-item';
        
        const time = log.when ? new Date(log.when).toLocaleString('ru-RU') : '-';
        const user = log.user || '-';
        const chat = log.chat || '-';
        const tags = (log.tags || []).join(', ') || '-';
        const text = (log.text || log.caption || '').substring(0, 100) + 
                    ((log.text || log.caption || '').length > 100 ? '...' : '');
        
        logElement.innerHTML = `
            <div class="log-time">${time}</div>
            <div class="log-user">${escapeHtml(user)}</div>
            <div class="log-chat">${escapeHtml(chat)}</div>
            <div class="log-tags">${escapeHtml(tags)}</div>
            <div class="log-text">${escapeHtml(text)}</div>
        `;
        container.appendChild(logElement);
    });
}

function updateTagFilter() {
    const select = document.getElementById('logTagFilter');
    const currentValue = select.value;
    
    // Очищаем и добавляем опцию "все"
    select.innerHTML = '<option value="">(все)</option>';
    
    // Добавляем уникальные теги
    const uniqueTags = [...new Set(currentTags.map(tag => tag.tag))];
    uniqueTags.forEach(tag => {
        const option = document.createElement('option');
        option.value = tag;
        option.textContent = tag;
        if (tag === currentValue) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

// === СОХРАНЕНИЕ ДАННЫХ ===

async function saveTag(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const tagData = {
        tag: formData.get('tag'),
        emoji: formData.get('emoji'),
        delay: parseInt(formData.get('delay')) || 0,
        match_mode: formData.get('match_mode'),
        require_photo: formData.get('require_photo') === 'true',
        reply_ok: formData.get('reply_ok') || '',
        reply_need_photo: formData.get('reply_need_photo') || '',
        thread_name: formData.get('thread_name') || '',
        reply_duplicate: formData.get('reply_duplicate') || '',
        moderation_enabled: formData.get('moderation_enabled') === 'true',
        reply_pending: formData.get('reply_pending') || ''
    };
    
    try {
        if (currentTagId === null) {
            // Создание нового тега
            await apiRequest('POST', '/tags', tagData);
            showNotification('Тег создан', 'success');
        } else {
            // Обновление существующего тега
            await apiRequest('PUT', `/tags/${currentTagId}`, tagData);
            showNotification('Тег обновлен', 'success');
        }
        
        closeTagModal();
        await loadTags();
        await loadStats();
        
    } catch (error) {
        showNotification('Ошибка сохранения тега: ' + error.message, 'error');
    }
}

async function deleteTag(tagId) {
    if (!confirm('Удалить этот тег?')) {
        return;
    }
    
    try {
        await apiRequest('DELETE', `/tags/${tagId}`);
        showNotification('Тег удален', 'success');
        await loadTags();
        await loadStats();
    } catch (error) {
        showNotification('Ошибка удаления тега: ' + error.message, 'error');
    }
}

// === МОДАЛЬНОЕ ОКНО ===
function openTagModal(tagId = null) {
    currentTagId = tagId;
    const modal = document.getElementById('tagModal');
    const form = document.getElementById('tagForm');
    
    if (tagId === null) {
        // Новый тег - устанавливаем значения по умолчанию
        document.getElementById('modalTitle').textContent = 'Добавить тег';
        form.reset();
        document.getElementById('modalMatchMode').value = 'equals';
        document.getElementById('modalRequirePhoto').value = 'true';
        document.getElementById('modalReplyOk').value = 'Зараховано! 🦋';
        document.getElementById('modalReplyNeedPhoto').value = 'Щоб зарахувати — додай фото і повтори з хештегом.';
        document.getElementById('modalThreadName').value = '';
        document.getElementById('modalReplyDuplicate').value = '';
        document.getElementById('modalModerationEnabled').value = 'false';
        document.getElementById('modalReplyPending').value = '';
    } else {
        // Редактирование существующего тега
        document.getElementById('modalTitle').textContent = 'Настроить тег';
        const tag = currentTags.find(t => t.id === tagId);
        
        // Основные настройки тега
        document.getElementById('modalTag').value = tag.tag;
        document.getElementById('modalEmoji').value = tag.emoji;
        document.getElementById('modalDelay').value = tag.delay || 0;
        
        // Настройки поведения
        document.getElementById('modalMatchMode').value = tag.match_mode || 'equals';
        document.getElementById('modalRequirePhoto').value = tag.require_photo !== undefined ? tag.require_photo.toString() : 'true';
        
        // Настройки сообщений
        document.getElementById('modalReplyOk').value = tag.reply_ok || 'Зараховано! 🦋';
        document.getElementById('modalReplyNeedPhoto').value = tag.reply_need_photo || 'Щоб зарахувати — додай фото і повтори з хештегом.';
        
        // Настройки треда
        document.getElementById('modalThreadName').value = tag.thread_name || '';
        
        // Настройки дублирования
        document.getElementById('modalReplyDuplicate').value = tag.reply_duplicate || '';
        
        // Настройки модерации
        document.getElementById('modalModerationEnabled').value = tag.moderation_enabled ? 'true' : 'false';
        document.getElementById('modalReplyPending').value = tag.reply_pending || '';
    }
    
    modal.style.display = 'block';
}

function closeTagModal() {
    document.getElementById('tagModal').style.display = 'none';
    currentTagId = null;
}

function editTag(tagId) {
    openTagModal(tagId);
}

// === УВЕДОМЛЕНИЯ ===
function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Автоматическое удаление через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
    
    // Удаление по клику
    notification.addEventListener('click', () => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    });
}

// === УТИЛИТЫ ===
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// === ОБРАБОТЧИКИ СОБЫТИЙ ===
// Закрытие модального окна по клику вне его
window.addEventListener('click', function(event) {
    const modal = document.getElementById('tagModal');
    if (event.target === modal) {
        closeTagModal();
    }
});

// Обработчик Escape для закрытия модального окна
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeTagModal();
    }
});

// Периодическое обновление данных (каждые 30 секунд)
setInterval(() => {
    if (authToken && document.getElementById('adminPanel').style.display !== 'none') {
        loadStats();
    }
}, 30000);

// ========= Управление вкладками =========
function showTab(tabName) {
    // Скрываем все вкладки
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.style.display = 'none');
    
    // Убираем активный класс со всех кнопок
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Показываем выбранную вкладку
    const targetTab = document.getElementById(tabName + 'Tab');
    if (targetTab) {
        targetTab.style.display = 'block';
    }
    
    // Добавляем активный класс к кнопке
    event.target.classList.add('active');
    
    // Загружаем данные для вкладки
    try {
        if (tabName === 'stats') {
            loadStats();
        } else if (tabName === 'logs') {
            loadLogs();
        } else if (tabName === 'tags') {
            loadAllData();
        } else if (tabName === 'moderation') {
            console.log('Переключение на вкладку модерации...');
            loadModerationData();
        }
    } catch (error) {
        console.error(`Ошибка загрузки данных для вкладки ${tabName}:`, error);
        showNotification(`Ошибка загрузки вкладки ${tabName}`, 'error');
    }
}

// ========= API Тестирование =========
function testEndpoint(method, path) {
    const tester = document.getElementById('apiTester');
    const methodBadge = document.getElementById('testMethod');
    const urlInput = document.getElementById('testUrl');
    const bodyGroup = document.getElementById('testBodyGroup');
    const bodyTextarea = document.getElementById('testBody');
    const resultDiv = document.getElementById('testResult');
    
    // Настраиваем форму
    methodBadge.textContent = method;
    methodBadge.className = `method-badge method ${method.toLowerCase()}`;
    urlInput.value = window.location.origin + path;
    
    // Показываем/скрываем поле для тела запроса
    if (method === 'GET' || method === 'DELETE') {
        bodyGroup.style.display = 'none';
        bodyTextarea.value = '';
    } else {
        bodyGroup.style.display = 'block';
        bodyTextarea.value = '{}';
    }
    
    // Скрываем результат и показываем тестер
    resultDiv.style.display = 'none';
    tester.style.display = 'block';
    tester.scrollIntoView({ behavior: 'smooth' });
}

function showTestForm(method, path, type) {
    testEndpoint(method, path);
    
    const bodyTextarea = document.getElementById('testBody');
    
    // Предзаполняем тело запроса примерами
    if (type === 'tag') {
        bodyTextarea.value = JSON.stringify({
            "tag": "#api_test",
            "emoji": "🧪",
            "delay": 0,
            "match_mode": "equals",
            "require_photo": false,
            "reply_ok": "API тест прошел!",
            "reply_need_photo": "Добавьте медиафайл",
            "thread_name": "",
            "reply_duplicate": "Дублирование обнаружено"
        }, null, 2);
    }
}

async function executeApiTest() {
    const method = document.getElementById('testMethod').textContent;
    const url = document.getElementById('testUrl').value;
    const bodyTextarea = document.getElementById('testBody');
    const resultDiv = document.getElementById('testResult');
    const resultContent = document.getElementById('testResultContent');
    
    try {
        const options = {
            method: method,
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        };
        
        // Добавляем тело запроса если нужно
        if (method !== 'GET' && method !== 'DELETE' && bodyTextarea.value.trim()) {
            try {
                JSON.parse(bodyTextarea.value); // Проверяем валидность JSON
                options.body = bodyTextarea.value;
            } catch (e) {
                throw new Error('Невалидный JSON в теле запроса: ' + e.message);
            }
        }
        
        const response = await fetch(url, options);
        const data = await response.json();
        
        const result = {
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries()),
            body: data
        };
        
        resultContent.textContent = JSON.stringify(result, null, 2);
        resultDiv.style.display = 'block';
        
        if (response.ok) {
            resultContent.style.color = '#10b981';
        } else {
            resultContent.style.color = '#ef4444';
        }
        
    } catch (error) {
        resultContent.textContent = `Ошибка: ${error.message}`;
        resultContent.style.color = '#ef4444';
        resultDiv.style.display = 'block';
    }
}

function hideTestForm() {
    document.getElementById('apiTester').style.display = 'none';
}

// ========= Утилиты =========
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========= Модерация =========
async function loadModerationData() {
    console.log('Начало загрузки данных модерации...');
    try {
        await Promise.all([
            loadModerationStats(),
            loadModerationQueue()
        ]);
        console.log('Данные модерации загружены успешно');
    } catch (error) {
        console.error('Ошибка загрузки данных модерации:', error);
        showNotification('Ошибка загрузки данных модерации', 'error');
    }
}

async function loadModerationStats() {
    try {
        const response = await apiRequest('GET', '/stats');
        const stats = response.data?.moderation || { pending: 0, approved: 0, rejected: 0, total: 0 };
        
        document.getElementById('pendingCount').textContent = stats.pending || 0;
        document.getElementById('approvedCount').textContent = stats.approved || 0;
        document.getElementById('rejectedCount').textContent = stats.rejected || 0;
        document.getElementById('totalModerationCount').textContent = stats.total || 0;
    } catch (error) {
        console.error('Ошибка загрузки статистики модерации:', error);
        // Устанавливаем значения по умолчанию при ошибке
        document.getElementById('pendingCount').textContent = '-';
        document.getElementById('approvedCount').textContent = '-';
        document.getElementById('rejectedCount').textContent = '-';
        document.getElementById('totalModerationCount').textContent = '-';
        showNotification('Ошибка загрузки статистики модерации', 'error');
    }
}

async function loadModerationQueue() {
    try {
        const container = document.getElementById('moderationItems');
        if (!container) {
            console.error('Контейнер moderationItems не найден');
            return;
        }
        
        container.innerHTML = '<div class="moderation-loading">🔄 Загрузка очереди модерации...</div>';
        
        const response = await apiRequest('GET', '/moderation');
        const items = response.data || [];
        
        console.log('Загрузка очереди модерации:', {
            success: response.success,
            itemsCount: items.length,
            items: items
        });
        
        if (!Array.isArray(items) || items.length === 0) {
            container.innerHTML = `
                <div class="moderation-empty">
                    <div class="moderation-empty-icon">✅</div>
                    <h4>Очередь модерации пуста</h4>
                    <p>Все сообщения обработаны или нет сообщений, требующих модерации.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = '';
        items.forEach((item, index) => {
            try {
                console.log(`Создание элемента модерации ${index}:`, item);
                const itemElement = createModerationItemElement(item);
                container.appendChild(itemElement);
                console.log(`Элемент модерации ${index} успешно добавлен`);
            } catch (itemError) {
                console.error(`Ошибка создания элемента модерации ${index}:`, itemError, item);
            }
        });
        
    } catch (error) {
        console.error('Ошибка загрузки очереди модерации:', error);
        const container = document.getElementById('moderationItems');
        if (container) {
            container.innerHTML = `
                <div class="moderation-empty">
                    <div class="moderation-empty-icon">❌</div>
                    <h4>Ошибка загрузки</h4>
                    <p>Не удалось загрузить очередь модерации: ${error.message || 'Неизвестная ошибка'}</p>
                </div>
            `;
        }
        showNotification('Ошибка загрузки очереди модерации', 'error');
    }
}

function createModerationItemElement(item) {
    if (!item || !item.id) {
        throw new Error('Некорректные данные элемента модерации');
    }
    
    const element = document.createElement('div');
    element.className = 'moderation-item';
    element.setAttribute('data-id', item.id);
    
    // Форматируем дату с проверкой
    let formattedDate = 'Неизвестно';
    try {
        if (item.created_at) {
            const date = new Date(item.created_at);
            formattedDate = date.toLocaleString('ru-RU');
        }
    } catch (dateError) {
        console.warn('Ошибка форматирования даты:', dateError);
    }
    
    // Определяем медиа-бейджи с проверками
    const mediaBadges = [];
    const mediaInfo = item.media_info || {};
    if (mediaInfo.has_photo) mediaBadges.push('<span class="media-badge">📷 Фото</span>');
    if (mediaInfo.has_video) mediaBadges.push('<span class="media-badge">🎥 Видео</span>');
    
    // Безопасное получение значений
    const username = escapeHtml(item.username || 'Неизвестный пользователь');
    const tag = escapeHtml(item.tag || '#unknown');
    const emoji = item.emoji || '❓';
    const text = item.text ? escapeHtml(item.text) : '';
    const caption = item.caption ? escapeHtml(item.caption) : '';
    const threadName = item.thread_name ? escapeHtml(item.thread_name) : '';
    
    element.innerHTML = `
        <div class="moderation-header">
            <div class="moderation-info">
                <div class="moderation-user">👤 ${username}</div>
                <div class="moderation-tag">
                    <span>${emoji}</span>
                    <span>${tag}</span>
                </div>
                <div class="moderation-meta">
                    <span>🆔 <span class="moderation-id">${item.id}</span></span>
                    <span>🕒 ${formattedDate}</span>
                    ${threadName ? `<span>🧵 ${threadName}</span>` : ''}
                </div>
            </div>
        </div>
        
        <div class="moderation-content">
            ${text ? `<div class="moderation-text">${text}</div>` : ''}
            ${caption ? `<div class="moderation-caption">📝 ${caption}</div>` : ''}
            ${mediaBadges.length > 0 ? `<div class="moderation-media-badges">${mediaBadges.join('')}</div>` : ''}
            ${generateMediaPreview(mediaInfo)}
        </div>
        
        <div class="moderation-actions">
            <button class="btn-reject" onclick="rejectModeration('${item.id}')">
                ❌ Отклонить
            </button>
            <button class="btn-approve" onclick="approveModeration('${item.id}')">
                ✅ Одобрить
            </button>
        </div>
    `;
    
    return element;
}

async function approveModeration(itemId) {
    try {
        await apiRequest('POST', `/moderation/${itemId}/approve`);
        showNotification('Сообщение одобрено', 'success');
        
        // Удаляем элемент из интерфейса
        const element = document.querySelector(`[data-id="${itemId}"]`);
        if (element) {
            element.style.opacity = '0.5';
            element.style.pointerEvents = 'none';
            setTimeout(() => {
                element.remove();
                // Проверяем, не стала ли очередь пустой
                const container = document.getElementById('moderationItems');
                if (container.children.length === 0) {
                    loadModerationQueue();
                }
            }, 500);
        }
        
        // Обновляем статистику
        loadModerationStats();
        
    } catch (error) {
        console.error('Ошибка одобрения:', error);
        showNotification('Ошибка одобрения сообщения', 'error');
    }
}

async function rejectModeration(itemId) {
    try {
        await apiRequest('POST', `/moderation/${itemId}/reject`);
        showNotification('Сообщение отклонено', 'success');
        
        // Удаляем элемент из интерфейса
        const element = document.querySelector(`[data-id="${itemId}"]`);
        if (element) {
            element.style.opacity = '0.5';
            element.style.pointerEvents = 'none';
            setTimeout(() => {
                element.remove();
                // Проверяем, не стала ли очередь пустой
                const container = document.getElementById('moderationItems');
                if (container.children.length === 0) {
                    loadModerationQueue();
                }
            }, 500);
        }
        
        // Обновляем статистику
        loadModerationStats();
        
    } catch (error) {
        console.error('Ошибка отклонения:', error);
        showNotification('Ошибка отклонения сообщения', 'error');
    }
}

// === ФУНКЦИИ НАВИГАЦИИ (дублирующаяся функция удалена) ===

// === ФУНКЦИИ ДЛЯ РАБОТЫ С ЛОГАМИ ===

async function loadLogs() {
    try {
        const tagFilter = document.getElementById('logTagFilter')?.value || '';
        const limit = document.getElementById('logLimit')?.value || 50;
        
        let url = `/logs?limit=${limit}`;
        if (tagFilter) {
            url += `&tag=${encodeURIComponent(tagFilter)}`;
        }
        
        const response = await apiRequest('GET', url);
        
        if (response.success) {
            renderLogs(response.data || []);
            updateLogTagFilter();
        } else {
            showNotification('Ошибка загрузки логов: ' + response.message, 'error');
        }
    } catch (error) {
        console.error('Ошибка загрузки логов:', error);
        showNotification('Ошибка загрузки логов', 'error');
    }
}

function renderLogs(logs) {
    const container = document.getElementById('logsContainer');
    if (!container) return;
    
    if (!logs || logs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📝</div>
                <h3>Логи пусты</h3>
                <p>Логи будут появляться когда бот обработает сообщения с тегами</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = logs.map(log => `
        <div class="log-item">
            <div class="log-main">
                <div class="log-user-info">
                    <div class="log-user-avatar">${(log.username || 'U')[0].toUpperCase()}</div>
                    <div class="log-user-details">
                        <div class="log-user-name">${escapeHtml(log.username || 'Unknown User')}</div>
                        <div class="log-time">${formatDateTime(log.timestamp)}</div>
                    </div>
                </div>
                
                <div class="log-action">
                    <div class="log-trigger">${escapeHtml(log.trigger)}</div>
                    <div class="log-reaction">${log.emoji}</div>
                </div>
            </div>
            
            <div class="log-meta">
                <div class="log-chat-info">
                    💬 ${log.chat_id.toString().slice(-8)}...
                    ${log.thread_name ? `<span class="log-thread-name">🧵 ${escapeHtml(log.thread_name)}</span>` : ''}
                </div>
                
                <div class="log-extras">
                    ${log.media_type ? `
                        <div class="log-media-preview" onclick="showMediaModal(${log.chat_id}, ${log.message_id}, '${log.media_type}')">
                            <span class="media-icon">${log.media_type === 'photo' ? '🖼️' : '🎥'}</span>
                            <span class="media-text">Показать ${log.media_type === 'photo' ? 'фото' : 'видео'}</span>
                        </div>
                    ` : ''}
                    ${log.caption ? `<span class="log-caption">"${escapeHtml(log.caption.slice(0, 50))}${log.caption.length > 50 ? '...' : ''}"</span>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

async function clearLogs() {
    if (!confirm('Вы уверены, что хотите очистить все логи? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await apiRequest('DELETE', '/logs');
        
        if (response.success) {
            const data = response.data || {};
            const message = `Очищено: ${data.deleted_logs || 0} логов, ${data.deleted_reactions || 0} реакций, ${data.deleted_moderation || 0} модераций`;
            showNotification(message, 'success');
            await loadLogs(); // Перезагружаем логи
        } else {
            showNotification('Ошибка очистки логов: ' + response.message, 'error');
        }
    } catch (error) {
        console.error('Ошибка очистки логов:', error);
        showNotification('Ошибка очистки логов', 'error');
    }
}

function updateLogTagFilter() {
    const select = document.getElementById('logTagFilter');
    if (!select || !currentTags) return;
    
    // Сохраняем текущее значение
    const currentValue = select.value;
    
    // Очищаем и добавляем опции
    select.innerHTML = '<option value="">(все)</option>';
    
    currentTags.forEach(tag => {
        const option = document.createElement('option');
        option.value = tag.tag;
        option.textContent = tag.tag;
        select.appendChild(option);
    });
    
    // Восстанавливаем значение
    select.value = currentValue;
}

function formatDateTime(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (error) {
        return timestamp;
    }
}

// === ФУНКЦИИ ДЛЯ ПРОСМОТРА МЕДИА ===

function generateMediaPreview(mediaInfo) {
    if (!mediaInfo || (!mediaInfo.has_photo && !mediaInfo.has_video)) {
        return '';
    }
    
    const previews = [];
    
    // Превью фото
    if (mediaInfo.has_photo && mediaInfo.photo_file_id) {
        previews.push(`
            <div class="moderation-media-preview" onclick="showModerationMedia('${mediaInfo.photo_file_id}', 'photo')">
                <div class="media-preview-placeholder">
                    <div class="media-icon">🖼️</div>
                    <div class="media-text">Нажмите для просмотра фото</div>
                </div>
            </div>
        `);
    }
    
    // Превью видео
    if (mediaInfo.has_video && mediaInfo.video_file_id) {
        previews.push(`
            <div class="moderation-media-preview" onclick="showModerationMedia('${mediaInfo.video_file_id}', 'video')">
                <div class="media-preview-placeholder">
                    <div class="media-icon">🎥</div>
                    <div class="media-text">Нажмите для просмотра видео</div>
                </div>
            </div>
        `);
    }
    
    return previews.length > 0 ? `<div class="moderation-media-container">${previews.join('')}</div>` : '';
}

async function showModerationMedia(fileId, mediaType) {
    try {
        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'media-modal';
        modal.innerHTML = `
            <div class="media-modal-content">
                <div class="media-modal-header">
                    <h3>${mediaType === 'photo' ? '🖼️ Фото из модерации' : '🎥 Видео из модерации'}</h3>
                    <button class="media-modal-close" onclick="closeMediaModal()">&times;</button>
                </div>
                <div class="media-modal-body">
                    <div class="media-loading">⏳ Загрузка медиа из Telegram...</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Закрытие по клику вне модального окна
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeMediaModal();
            }
        });
        
        // Закрытие по Escape
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                closeMediaModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        // Загружаем реальное медиа через API
        const response = await apiRequest('GET', `/media/file/${fileId}`);
        const mediaBody = modal.querySelector('.media-modal-body');
        
        if (response.success) {
            if (mediaType === 'photo') {
                mediaBody.innerHTML = `
                    <img src="${response.file_url}" 
                         alt="Фото из модерации" 
                         class="media-preview-image"
                         onload="this.style.opacity=1"
                         style="opacity:0; transition: opacity 0.3s ease;">
                    <p class="media-info">
                        📁 ${response.file_path}<br>
                        📊 Размер: ${formatFileSize(response.file_size)}
                    </p>
                `;
            } else {
                mediaBody.innerHTML = `
                    <video controls class="media-preview-video" preload="metadata">
                        <source src="${response.file_url}" type="video/mp4">
                        Ваш браузер не поддерживает видео.
                    </video>
                    <p class="media-info">
                        📁 ${response.file_path}<br>
                        📊 Размер: ${formatFileSize(response.file_size)}
                    </p>
                `;
            }
        } else {
            mediaBody.innerHTML = `
                <div class="media-error">
                    ❌ Ошибка загрузки медиа: ${response.message}
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Ошибка показа медиа модерации:', error);
        showNotification('Ошибка загрузки медиа', 'error');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Б';
    const k = 1024;
    const sizes = ['Б', 'КБ', 'МБ', 'ГБ'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function showMediaModal(chatId, messageId, mediaType) {
    try {
        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'media-modal';
        modal.innerHTML = `
            <div class="media-modal-content">
                <div class="media-modal-header">
                    <h3>${mediaType === 'photo' ? '🖼️ Фото' : '🎥 Видео'}</h3>
                    <button class="media-modal-close" onclick="closeMediaModal()">&times;</button>
                </div>
                <div class="media-modal-body">
                    <div class="media-loading">⏳ Загрузка медиа...</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Закрытие по клику вне модального окна
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeMediaModal();
            }
        });
        
        // Закрытие по Escape
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                closeMediaModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        // Загружаем медиа (пока заглушка)
        setTimeout(() => {
            const mediaBody = modal.querySelector('.media-modal-body');
            if (mediaType === 'photo') {
                mediaBody.innerHTML = `
                    <img src="https://via.placeholder.com/600x400/334155/e2e8f0?text=Фото+${messageId}" 
                         alt="Media preview" class="media-preview-image">
                    <p class="media-info">Chat: ${chatId} | Message: ${messageId}</p>
                `;
            } else {
                mediaBody.innerHTML = `
                    <video controls class="media-preview-video">
                        <source src="https://sample-videos.com/zip/10/mp4/SampleVideo_360x240_1mb.mp4" type="video/mp4">
                        Ваш браузер не поддерживает видео.
                    </video>
                    <p class="media-info">Chat: ${chatId} | Message: ${messageId}</p>
                `;
            }
        }, 500);
        
    } catch (error) {
        console.error('Ошибка показа медиа:', error);
        showNotification('Ошибка загрузки медиа', 'error');
    }
}

function closeMediaModal() {
    const modal = document.querySelector('.media-modal');
    if (modal) {
        modal.remove();
    }
}
