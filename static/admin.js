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
    apiRequest('GET', '/stats')
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
        reply_pending: formData.get('reply_pending') || '',
        counter_name: formData.get('counter_name') || ''
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
        document.getElementById('modalDelay').value = '10';
        document.getElementById('modalMatchMode').value = 'prefix';
        document.getElementById('modalRequirePhoto').value = 'false';
        document.getElementById('modalReplyOk').value = '';
        document.getElementById('modalReplyNeedPhoto').value = '';
        document.getElementById('modalThreadName').value = '';
        document.getElementById('modalReplyDuplicate').value = '';
        document.getElementById('modalModerationEnabled').value = 'false';
        document.getElementById('modalReplyPending').value = '';
        document.getElementById('modalCounterName').value = '';
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
        document.getElementById('modalReplyOk').value = tag.reply_ok || '';
        document.getElementById('modalReplyNeedPhoto').value = tag.reply_need_photo || '';
        
        // Настройки треда
        document.getElementById('modalThreadName').value = tag.thread_name || '';
        
        // Настройки дублирования
        document.getElementById('modalReplyDuplicate').value = tag.reply_duplicate || '';
        
        // Настройки модерации
        document.getElementById('modalModerationEnabled').value = tag.moderation_enabled ? 'true' : 'false';
        document.getElementById('modalReplyPending').value = tag.reply_pending || '';
        
        // Название счетчика
        document.getElementById('modalCounterName').value = tag.counter_name || '';
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
    const counterName = item.counter_name ? escapeHtml(item.counter_name) : '';
    
    element.innerHTML = `
        <div class="moderation-header">
            <div class="moderation-info">
                <div class="moderation-user">👤 ${username}</div>
                <div class="moderation-tag">
                    <span>${emoji}</span>
                    <span>${tag}</span>
                    ${counterName ? `<span class="counter-name">📊 ${counterName}</span>` : ''}
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
        <div class="log-item ${log.status === 'failed' ? 'log-item-failed' : ''}">
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
                    ${log.status === 'failed' ? '<div class="log-status-badge failed">❌ Ошибка</div>' : '<div class="log-status-badge success">✅</div>'}
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

// === МАССОВАЯ РАССЫЛКА ===

// Проверка подключения к Supabase
async function checkSupabaseConnection() {
    const statusIndicator = document.getElementById('supabaseStatus');

    // Показываем загрузку
    statusIndicator.innerHTML = '<span class="status-dot status-unknown"></span><span class="status-text">Проверка...</span>';

    try {
        const response = await apiRequest('POST', '/broadcast/preview', {});

        if (response.success) {
            // Supabase настроен и работает
            statusIndicator.innerHTML = '<span class="status-dot status-connected"></span><span class="status-text">Подключено</span>';
            showNotification('Supabase подключен успешно', 'success');
        } else {
            // Ошибка подключения
            statusIndicator.innerHTML = '<span class="status-dot status-error"></span><span class="status-text">Ошибка</span>';
            showNotification('Ошибка подключения к Supabase: ' + response.message, 'error');
        }
    } catch (error) {
        statusIndicator.innerHTML = '<span class="status-dot status-error"></span><span class="status-text">Ошибка</span>';
        showNotification('Не удалось проверить подключение', 'error');
    }
}

// Загрузка предпросмотра получателей
async function loadBroadcastPreview() {
    const previewResult = document.getElementById('broadcastPreviewResult');
    const userCountEl = document.getElementById('previewUserCount');
    const usersListEl = document.getElementById('previewUsersList');
    const sendBtn = document.getElementById('sendBroadcastBtn');

    try {
        showNotification('Загрузка списка получателей...', 'info');

        const response = await apiRequest('POST', '/broadcast/preview', {});

        if (response.success) {
            const users = response.users || [];
            const count = response.count || 0;

            userCountEl.textContent = count;

            if (count === 0) {
                usersListEl.innerHTML = '<div class="alert-warning">Пользователи с привязанным Telegram не найдены</div>';
                sendBtn.disabled = true;
            } else {
                // Показываем список пользователей
                let html = '<table class="users-table"><thead><tr><th>Telegram ID</th><th>Username</th><th>Email</th><th>Имя</th><th>Действия</th></tr></thead><tbody>';

                users.slice(0, 50).forEach(user => {  // Показываем максимум 50
                    html += `<tr>
                        <td><code>${user.tg_user_id}</code></td>
                        <td>${escapeHtml(user.username || '-')}</td>
                        <td>${escapeHtml(user.email || '-')}</td>
                        <td>${escapeHtml(user.full_name || '-')}</td>
                        <td>
                            <button
                                class="btn btn-small btn-secondary"
                                onclick="sendTestToUser('${user.tg_user_id}', '${escapeHtml(user.username || '')}')"
                                title="Отправить тестовое сообщение">
                                📨 Тест
                            </button>
                        </td>
                    </tr>`;
                });

                html += '</tbody></table>';

                if (users.length > 50) {
                    html += `<p class="text-muted">Показано 50 из ${users.length} пользователей</p>`;
                }

                usersListEl.innerHTML = html;
                sendBtn.disabled = false;
            }

            previewResult.style.display = 'block';
            showNotification(`Найдено ${count} получателей`, 'success');
        } else {
            showNotification('Ошибка: ' + response.message, 'error');
            previewResult.style.display = 'none';
            sendBtn.disabled = true;
        }
    } catch (error) {
        console.error('Ошибка загрузки предпросмотра:', error);
        showNotification('Ошибка загрузки предпросмотра', 'error');
        previewResult.style.display = 'none';
        sendBtn.disabled = true;
    }
}

// Отправка массовой рассылки
async function sendBroadcast() {
    const sendBtn = document.getElementById('sendBroadcastBtn');
    const resultDiv = document.getElementById('broadcastResult');
    const resultContent = document.getElementById('broadcastResultContent');

    const message = getBroadcastMessage().trim();
    const parseMode = 'HTML'; // Всегда используем HTML

    // Валидация
    if (!message) {
        showNotification('Введите текст сообщения', 'error');
        return;
    }

    if (message.length > 4096) {
        showNotification('Сообщение слишком длинное (максимум 4096 символов)', 'error');
        return;
    }

    // Подтверждение
    if (!confirm(`Вы уверены что хотите отправить рассылку?\n\nСообщение будет отправлено всем пользователям с привязанным Telegram.`)) {
        return;
    }

    try {
        sendBtn.disabled = true;
        sendBtn.textContent = '⏳ Отправка...';
        showNotification('Начинаем рассылку...', 'info');

        const disableLinkPreview = document.getElementById('disableLinkPreview')?.checked ?? true;
        const button = getButtonData();

        const response = await apiRequest('POST', '/broadcast/send', {
            message: message,
            parse_mode: parseMode,
            filters: null,
            disable_web_page_preview: disableLinkPreview,
            button: button
        });

        if (response.success) {
            const data = response.data || {};
            const total = data.total || 0;
            const success = data.success || 0;
            const failed = data.failed || 0;
            const failedUsers = data.failed_users || [];

            // Показываем результат
            let html = `
                <div class="alert-success">
                    <h4>✅ Рассылка завершена!</h4>
                    <p>${response.message}</p>
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <strong>Всего:</strong> ${total}
                    </div>
                    <div class="stat-item">
                        <strong>Успешно:</strong> <span class="text-success">${success}</span>
                    </div>
                    <div class="stat-item">
                        <strong>Ошибок:</strong> <span class="text-danger">${failed}</span>
                    </div>
                </div>
            `;

            if (failed > 0 && failedUsers.length > 0) {
                html += '<h4>Ошибки отправки:</h4><div class="failed-users-list">';
                failedUsers.forEach(user => {
                    html += `<div class="failed-user">
                        <strong>${user.username || user.tg_user_id}</strong>: ${user.error}
                    </div>`;
                });
                html += '</div>';
            }

            resultContent.innerHTML = html;
            resultDiv.style.display = 'block';

            showNotification('Рассылка завершена успешно', 'success');

            // Очищаем форму
            clearBroadcastForm();
        } else {
            showNotification('Ошибка: ' + response.message, 'error');
        }
    } catch (error) {
        console.error('Ошибка отправки рассылки:', error);
        showNotification('Ошибка отправки рассылки', 'error');
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = '📤 Отправить рассылку';
    }
}

// Очистка формы рассылки
function clearBroadcastForm() {
    const messageEl = document.getElementById('broadcastMessage');
    if (messageEl) messageEl.value = '';

    document.getElementById('broadcastPreviewResult').style.display = 'none';
    document.getElementById('sendBroadcastBtn').disabled = true;

    // Сбросить preview сообщения
    const previewEl = document.getElementById('messagePreview');
    if (previewEl) {
        previewEl.innerHTML = '<span class="tg-placeholder">Введите текст сообщения...</span>';
    }

    // Сбросить счетчик символов
    const charCountEl = document.getElementById('charCount');
    if (charCountEl) {
        charCountEl.textContent = '0';
        charCountEl.style.color = '#94a3b8';
    }

    // Сбросить настройки кнопки
    const enableButton = document.getElementById('enableButton');
    if (enableButton) enableButton.checked = false;

    const buttonText = document.getElementById('buttonText');
    if (buttonText) buttonText.value = '';

    const buttonUrl = document.getElementById('buttonUrl');
    if (buttonUrl) buttonUrl.value = '';

    const buttonFields = document.getElementById('buttonFields');
    if (buttonFields) buttonFields.style.display = 'none';

    const buttonPreview = document.getElementById('buttonPreview');
    if (buttonPreview) buttonPreview.style.display = 'none';
}

// === ФУНКЦИИ ДЛЯ ТЕСТОВОЙ РАССЫЛКИ ===

function showTestMessageDialog() {
    // Копируем сообщение из основной формы если оно есть
    const mainMessage = getBroadcastMessage();
    if (mainMessage) {
        document.getElementById('testMessage').value = mainMessage;
    }

    document.getElementById('testMessageModal').style.display = 'block';
}

function closeTestMessageModal() {
    document.getElementById('testMessageModal').style.display = 'none';
    document.getElementById('testTgUserId').value = '';
    document.getElementById('testMessage').value = '';
}

async function sendTestMessage() {
    const tgUserId = document.getElementById('testTgUserId').value;
    const message = document.getElementById('testMessage').value;
    const parseMode = 'HTML'; // Всегда используем HTML

    // Валидация
    if (!tgUserId) {
        showNotification('Введите Telegram User ID', 'error');
        return;
    }

    if (!message) {
        showNotification('Введите текст сообщения', 'error');
        return;
    }

    try {
        showNotification('Отправка тестового сообщения...', 'info');

        const disableLinkPreview = document.getElementById('disableLinkPreview')?.checked ?? true;
        const button = getButtonData();

        const response = await apiRequest('POST', '/broadcast/test', {
            tg_user_id: parseInt(tgUserId),
            message: message,
            parse_mode: parseMode,
            disable_web_page_preview: disableLinkPreview,
            button: button
        });

        if (response.success) {
            showNotification('Тестовое сообщение отправлено успешно!', 'success');
            closeTestMessageModal();
        } else {
            showNotification('Ошибка: ' + response.message, 'error');
        }
    } catch (error) {
        console.error('Ошибка отправки тестового сообщения:', error);
        showNotification('Ошибка отправки тестового сообщения', 'error');
    }
}

// Функция для быстрой отправки тестового сообщения из списка
function sendTestToUser(tgUserId, username) {
    document.getElementById('testTgUserId').value = tgUserId;

    // Если есть сообщение в основной форме, используем его
    const mainMessage = getBroadcastMessage();
    if (mainMessage) {
        document.getElementById('testMessage').value = mainMessage;
    } else {
        document.getElementById('testMessage').value = `Привет! Это тестовое сообщение для @${username || tgUserId}`;
    }

    showTestMessageDialog();
}

// Расширяем функцию showTab для автоматической проверки Supabase
(function() {
    const originalShowTab = window.showTab;
    window.showTab = function(tabName) {
        if (originalShowTab) {
            originalShowTab.call(this, tabName);
        }

        // При открытии вкладки рассылки проверяем подключение и загружаем марафоны
        if (tabName === 'broadcast') {
            setTimeout(() => {
                checkSupabaseConnection();
                loadMarathons();
            }, 100);
        }
    };
})();

// === ФИЛЬТРЫ РАССЫЛКИ ===

let currentMarathons = [];
let lastPreviewUsers = []; // Сохраняем последний предпросмотр для отправки

// Загрузка списка марафонов
async function loadMarathons() {
    try {
        const response = await apiRequest('GET', '/marathons');

        if (response.success) {
            currentMarathons = response.data || [];

            const selectEl = document.getElementById('filterMarathon');
            if (selectEl) {
                selectEl.innerHTML = '<option value="">-- Все марафоны --</option>';
                currentMarathons.forEach(marathon => {
                    selectEl.innerHTML += `<option value="${marathon.reference_id}">${escapeHtml(marathon.title)}</option>`;
                });
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки марафонов:', error);
    }
}

// Собрать текущие фильтры из формы
function collectFilters() {
    const filters = {};

    const marathonRef = document.getElementById('filterMarathon').value;
    if (marathonRef) filters.marathon_ref_id = marathonRef;

    const isPurchased = document.getElementById('filterIsPurchased').value;
    if (isPurchased !== '') filters.is_purchased = isPurchased === 'true';

    const daysMin = document.getElementById('filterCompletedDaysMin').value;
    if (daysMin !== '') filters.completed_days_min = parseInt(daysMin);

    const daysMax = document.getElementById('filterCompletedDaysMax').value;
    if (daysMax !== '') filters.completed_days_max = parseInt(daysMax);

    return filters;
}

// Сбросить фильтры
function clearFilters() {
    document.getElementById('filterMarathon').value = '';
    document.getElementById('filterIsPurchased').value = '';
    document.getElementById('filterCompletedDaysMin').value = '';
    document.getElementById('filterCompletedDaysMax').value = '';

    // Скрываем предпросмотр
    document.getElementById('broadcastPreviewResult').style.display = 'none';
    document.getElementById('sendBroadcastBtn').disabled = true;
    document.getElementById('previewUserCount').textContent = '—';
    lastPreviewUsers = [];

    // Обновляем отображение активных фильтров
    updateActiveFiltersDisplay();

    showNotification('Фильтры сброшены', 'success');
}

// Загрузка предпросмотра по фильтрам
async function loadFilteredPreview() {
    const previewResult = document.getElementById('broadcastPreviewResult');
    const userCountEl = document.getElementById('previewUserCount');
    const usersListEl = document.getElementById('previewUsersList');
    const sendBtn = document.getElementById('sendBroadcastBtn');
    const showingCountEl = document.getElementById('audienceShowingCount');
    const searchInput = document.getElementById('audienceSearchInput');

    const filters = collectFilters();

    try {
        showNotification('Загрузка списка получателей...', 'info');

        const response = await apiRequest('POST', '/broadcast/preview-filtered', { filters });

        if (response.success) {
            const users = response.users || [];
            const count = response.count || 0;

            lastPreviewUsers = users; // Сохраняем для отправки
            userCountEl.textContent = count;

            // Сбрасываем поиск
            if (searchInput) searchInput.value = '';

            if (count === 0) {
                usersListEl.innerHTML = '<div class="empty-state" style="padding: 20px; text-align: center; color: #64748b;">Пользователи не найдены</div>';
                sendBtn.disabled = true;
                if (showingCountEl) showingCountEl.textContent = '';
            } else {
                renderAudienceList(users);
                sendBtn.disabled = false;
            }

            previewResult.style.display = 'block';
            showNotification(`Найдено ${count} получателей`, 'success');
        } else {
            showNotification('Ошибка: ' + response.message, 'error');
            previewResult.style.display = 'none';
            sendBtn.disabled = true;
        }
    } catch (error) {
        console.error('Ошибка загрузки предпросмотра:', error);
        showNotification('Ошибка загрузки предпросмотра', 'error');
        previewResult.style.display = 'none';
        sendBtn.disabled = true;
    }
}

// Отрисовка списка аудитории
function renderAudienceList(users, searchTerm = '') {
    const usersListEl = document.getElementById('previewUsersList');
    const showingCountEl = document.getElementById('audienceShowingCount');

    // Дедупликация по tg_user_id
    const seen = new Set();
    let uniqueUsers = users.filter(user => {
        if (seen.has(user.tg_user_id)) return false;
        seen.add(user.tg_user_id);
        return true;
    });

    let filteredUsers = uniqueUsers;

    // Фильтрация по поиску
    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filteredUsers = uniqueUsers.filter(user => {
            const name = (user.username || user.full_name || '').toLowerCase();
            const email = (user.email || '').toLowerCase();
            return name.includes(term) || email.includes(term);
        });
    }

    if (filteredUsers.length === 0) {
        usersListEl.innerHTML = '<div class="empty-state" style="padding: 20px; text-align: center; color: #64748b;">Ничего не найдено</div>';
        if (showingCountEl) showingCountEl.textContent = '0';
        return;
    }

    const showCount = Math.min(filteredUsers.length, 50);
    let html = '';

    filteredUsers.slice(0, showCount).forEach(user => {
        const displayName = user.username || user.full_name || 'User';
        const email = user.email || '';
        html += `<div class="audience-item">
            <div class="audience-item-info">
                <span class="audience-item-name">${escapeHtml(displayName)}</span>
                ${email ? `<span class="audience-item-email">${escapeHtml(email)}</span>` : ''}
                <span class="audience-item-id">${user.tg_user_id}</span>
            </div>
            <button class="btn btn-test" onclick="sendTestToUser('${user.tg_user_id}', '${escapeHtml(user.username || '')}')">Тест</button>
        </div>`;
    });

    usersListEl.innerHTML = html;

    if (showingCountEl) {
        if (searchTerm) {
            showingCountEl.textContent = filteredUsers.length > showCount ? `${showCount}/${filteredUsers.length}` : `${filteredUsers.length}`;
        } else {
            showingCountEl.textContent = uniqueUsers.length > showCount ? `${showCount}/${uniqueUsers.length}` : `${uniqueUsers.length}`;
        }
    }
}

// Фильтрация списка аудитории по имени/email
function filterAudienceList() {
    const searchInput = document.getElementById('audienceSearchInput');
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    renderAudienceList(lastPreviewUsers, searchTerm);
}

// Отправка рассылки по текущим фильтрам
async function sendBroadcastWithFilters() {
    if (lastPreviewUsers.length === 0) {
        showNotification('Сначала загрузите предпросмотр получателей', 'error');
        return;
    }

    const sendBtn = document.getElementById('sendBroadcastBtn');
    const resultDiv = document.getElementById('broadcastResult');
    const resultContent = document.getElementById('broadcastResultContent');

    const message = getBroadcastMessage().trim();
    const parseMode = 'HTML'; // Всегда используем HTML

    if (!message) {
        showNotification('Введите текст сообщения', 'error');
        return;
    }

    if (message.length > 4096) {
        showNotification('Сообщение слишком длинное (максимум 4096 символов)', 'error');
        return;
    }

    const filters = collectFilters();
    const filterDescription = getFilterDescription(filters);

    if (!confirm(`Вы уверены что хотите отправить рассылку?\n\n${filterDescription}\nКоличество получателей: ${lastPreviewUsers.length}`)) {
        return;
    }

    try {
        sendBtn.disabled = true;
        sendBtn.textContent = '⏳ Отправка...';
        showNotification('Начинаем рассылку...', 'info');

        const disableLinkPreview = document.getElementById('disableLinkPreview')?.checked ?? true;
        const button = getButtonData();

        const response = await apiRequest('POST', '/broadcast/send-filtered', {
            message: message,
            parse_mode: parseMode,
            filters: filters,
            disable_web_page_preview: disableLinkPreview,
            button: button
        });

        if (response.success) {
            const data = response.data || {};
            const total = data.total || 0;
            const success = data.success || 0;
            const failed = data.failed || 0;
            const failedUsers = data.failed_users || [];

            let html = `
                <div class="alert-success">
                    <h4>✅ Рассылка завершена!</h4>
                    <p>${response.message}</p>
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <strong>Всего:</strong> ${total}
                    </div>
                    <div class="stat-item">
                        <strong>Успешно:</strong> <span class="text-success">${success}</span>
                    </div>
                    <div class="stat-item">
                        <strong>Ошибок:</strong> <span class="text-danger">${failed}</span>
                    </div>
                </div>
            `;

            if (failed > 0 && failedUsers.length > 0) {
                html += '<h4>Ошибки отправки:</h4><div class="failed-users-list">';
                failedUsers.forEach(user => {
                    html += `<div class="failed-user">
                        <strong>${user.username || user.tg_user_id}</strong>: ${user.error}
                    </div>`;
                });
                html += '</div>';
            }

            resultContent.innerHTML = html;
            resultDiv.style.display = 'block';

            showNotification('Рассылка завершена успешно', 'success');
            clearBroadcastForm();
        } else {
            showNotification('Ошибка: ' + response.message, 'error');
        }
    } catch (error) {
        console.error('Ошибка отправки рассылки:', error);
        showNotification('Ошибка отправки рассылки', 'error');
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg> Отправить рассылку`;
    }
}

// Получить текстовое описание фильтров
function getFilterDescription(filters) {
    if (!filters || Object.keys(filters).length === 0) {
        return 'Фильтры: Все пользователи';
    }

    const parts = [];

    if (filters.marathon_ref_id) {
        const marathon = currentMarathons.find(m => m.reference_id === filters.marathon_ref_id);
        parts.push(`Марафон: ${marathon ? marathon.title : filters.marathon_ref_id}`);
    }

    if (filters.is_purchased === true) parts.push('Купили');
    if (filters.is_purchased === false) parts.push('Не купили');

    if (filters.completed_days_min !== undefined || filters.completed_days_max !== undefined) {
        const min = filters.completed_days_min || 0;
        const max = filters.completed_days_max !== undefined ? filters.completed_days_max : '∞';
        parts.push(`Выполнено: ${min}-${max} дней`);
    }

    return parts.length > 0 ? `Фильтры: ${parts.join(', ')}` : 'Фильтры: Все пользователи';
}

// === НОВЫЕ ФУНКЦИИ ДЛЯ UI РАССЫЛКИ ===

// Открытие попапа фильтров
function openFilterPopup() {
    loadMarathons(); // Обновить список марафонов
    document.getElementById('filterPopup').style.display = 'block';
}

// Закрытие попапа фильтров
function closeFilterPopup() {
    document.getElementById('filterPopup').style.display = 'none';
}

// Применить фильтры и закрыть попап
function applyFilters() {
    closeFilterPopup();
    updateActiveFiltersDisplay();
    loadFilteredPreview(); // Автоматически загрузить preview
}

// Обновить отображение активных фильтров в виде тегов
function updateActiveFiltersDisplay() {
    const container = document.getElementById('activeFiltersDisplay');
    if (!container) return;

    const filters = collectFilters();
    const tags = [];

    if (filters.marathon_ref_id) {
        const marathon = currentMarathons.find(m => m.reference_id === filters.marathon_ref_id);
        tags.push({ key: 'marathon', label: marathon ? marathon.title : 'Марафон' });
    }

    if (filters.is_purchased === true) tags.push({ key: 'purchased', label: 'Купили' });
    if (filters.is_purchased === false) tags.push({ key: 'purchased', label: 'Не купили' });

    if (filters.completed_days_min !== undefined || filters.completed_days_max !== undefined) {
        const min = filters.completed_days_min || 0;
        const max = filters.completed_days_max !== undefined ? filters.completed_days_max : '∞';
        tags.push({ key: 'days', label: `${min}-${max} дней` });
    }

    if (tags.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = tags.map(tag =>
        `<span class="filter-tag">${escapeHtml(tag.label)}<span class="remove-filter" onclick="removeFilter('${tag.key}')">&times;</span></span>`
    ).join('');
}

// Удалить конкретный фильтр
function removeFilter(key) {
    switch(key) {
        case 'marathon':
            document.getElementById('filterMarathon').value = '';
            break;
        case 'purchased':
            document.getElementById('filterIsPurchased').value = '';
            break;
        case 'days':
            document.getElementById('filterCompletedDaysMin').value = '';
            document.getElementById('filterCompletedDaysMax').value = '';
            break;
    }
    updateActiveFiltersDisplay();
    loadFilteredPreview();
}

// Обновить preview сообщения в реальном времени (HTML режим)
function updateMessagePreview() {
    const previewEl = document.getElementById('messagePreview');
    const charCountEl = document.getElementById('charCount');
    const message = getBroadcastMessage();

    // Обновить счетчик символов
    if (charCountEl) {
        charCountEl.textContent = message.length;
        charCountEl.style.color = message.length > 4096 ? '#ef4444' : '#94a3b8';
    }

    // Обновить preview
    if (!previewEl) return;

    if (!message.trim()) {
        previewEl.innerHTML = '<span class="tg-placeholder">Введите текст сообщения...</span>';
        return;
    }

    // Парсим HTML теги для preview
    let formattedMessage = message
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/&lt;b&gt;(.*?)&lt;\/b&gt;/gi, '<b>$1</b>')
        .replace(/&lt;strong&gt;(.*?)&lt;\/strong&gt;/gi, '<strong>$1</strong>')
        .replace(/&lt;i&gt;(.*?)&lt;\/i&gt;/gi, '<i>$1</i>')
        .replace(/&lt;em&gt;(.*?)&lt;\/em&gt;/gi, '<em>$1</em>')
        .replace(/&lt;u&gt;(.*?)&lt;\/u&gt;/gi, '<u>$1</u>')
        .replace(/&lt;s&gt;(.*?)&lt;\/s&gt;/gi, '<s>$1</s>')
        .replace(/&lt;strike&gt;(.*?)&lt;\/strike&gt;/gi, '<s>$1</s>')
        .replace(/&lt;code&gt;(.*?)&lt;\/code&gt;/gi, '<code>$1</code>')
        .replace(/&lt;pre&gt;(.*?)&lt;\/pre&gt;/gis, '<pre>$1</pre>')
        // Ссылки с двойными кавычками
        .replace(/&lt;a href="(.*?)"&gt;(.*?)&lt;\/a&gt;/gi, '<a href="$1" target="_blank">$2</a>')
        // Ссылки с одинарными кавычками
        .replace(/&lt;a href='(.*?)'&gt;(.*?)&lt;\/a&gt;/gi, '<a href="$1" target="_blank">$2</a>');

    // Сохраняем переносы строк
    formattedMessage = formattedMessage.replace(/\n/g, '<br>');

    previewEl.innerHTML = formattedMessage;

    // Обновляем превью кнопки
    updateButtonPreview();
}

// Показать/скрыть поля для кнопки
function toggleButtonSettings() {
    const enabled = document.getElementById('enableButton').checked;
    const fields = document.getElementById('buttonFields');
    if (fields) {
        fields.style.display = enabled ? 'block' : 'none';
    }
    updateButtonPreview();
}

// Обновить превью кнопки
function updateButtonPreview() {
    const buttonPreview = document.getElementById('buttonPreview');
    const buttonPreviewText = document.getElementById('buttonPreviewText');
    const enabled = document.getElementById('enableButton')?.checked;
    const buttonText = document.getElementById('buttonText')?.value?.trim();

    if (buttonPreview && buttonPreviewText) {
        if (enabled && buttonText) {
            buttonPreview.style.display = 'block';
            buttonPreviewText.textContent = buttonText;
        } else {
            buttonPreview.style.display = 'none';
        }
    }
}

// Получить данные кнопки для отправки
function getButtonData() {
    const enabled = document.getElementById('enableButton')?.checked;
    const buttonText = document.getElementById('buttonText')?.value?.trim();
    const buttonUrl = document.getElementById('buttonUrl')?.value?.trim();

    if (enabled && buttonText && buttonUrl) {
        return {
            text: buttonText,
            url: buttonUrl
        };
    }
    return null;
}

// Закрытие модальных окон по клику вне них и по Escape
window.addEventListener('click', function(event) {
    const testModal = document.getElementById('testMessageModal');
    const filterPopup = document.getElementById('filterPopup');

    if (event.target === testModal) {
        closeTestMessageModal();
    }
    if (event.target === filterPopup) {
        closeFilterPopup();
    }
});

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const testModal = document.getElementById('testMessageModal');
        const filterPopup = document.getElementById('filterPopup');

        if (testModal && testModal.style.display === 'block') {
            closeTestMessageModal();
        }
        if (filterPopup && filterPopup.style.display === 'block') {
            closeFilterPopup();
        }
    }
});

// ========================================
// HTML Editor Functions
// ========================================

// Получить текст из редактора
function getBroadcastMessage() {
    const textareaEl = document.getElementById('broadcastMessage');
    return textareaEl ? textareaEl.value : '';
}

// Установить текст в редактор
function setBroadcastMessage(text) {
    const textareaEl = document.getElementById('broadcastMessage');
    if (textareaEl) {
        textareaEl.value = text;
    }
    updateMessagePreview();
}

// Вставить HTML тег вокруг выделенного текста
function insertTag(tagName) {
    const textarea = document.getElementById('broadcastMessage');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);
    const beforeText = textarea.value.substring(0, start);
    const afterText = textarea.value.substring(end);

    const openTag = `<${tagName}>`;
    const closeTag = `</${tagName}>`;

    if (selectedText) {
        // Оборачиваем выделенный текст
        textarea.value = beforeText + openTag + selectedText + closeTag + afterText;
        textarea.selectionStart = start + openTag.length;
        textarea.selectionEnd = start + openTag.length + selectedText.length;
    } else {
        // Вставляем пустые теги и ставим курсор между ними
        textarea.value = beforeText + openTag + closeTag + afterText;
        textarea.selectionStart = textarea.selectionEnd = start + openTag.length;
    }

    textarea.focus();
    updateMessagePreview();
}

// Вставить ссылку
function insertLink() {
    const textarea = document.getElementById('broadcastMessage');
    if (!textarea) return;

    const url = prompt('Введите URL:', 'https://');
    if (!url) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end) || 'текст ссылки';
    const beforeText = textarea.value.substring(0, start);
    const afterText = textarea.value.substring(end);

    const linkHtml = `<a href="${url}">${selectedText}</a>`;

    textarea.value = beforeText + linkHtml + afterText;
    textarea.selectionStart = textarea.selectionEnd = start + linkHtml.length;

    textarea.focus();
    updateMessagePreview();
}

// Вставить emoji
function insertEmoji(emoji) {
    const textarea = document.getElementById('broadcastMessage');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const beforeText = textarea.value.substring(0, start);
    const afterText = textarea.value.substring(start);

    textarea.value = beforeText + emoji + afterText;
    textarea.selectionStart = textarea.selectionEnd = start + emoji.length;

    textarea.focus();
    updateMessagePreview();
}

// Обработка горячих клавиш
document.addEventListener('keydown', function(e) {
    const textarea = document.getElementById('broadcastMessage');
    if (!textarea || document.activeElement !== textarea) return;

    // Ctrl+B - жирный
    if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        insertTag('b');
    }
    // Ctrl+I - курсив
    if (e.ctrlKey && e.key === 'i') {
        e.preventDefault();
        insertTag('i');
    }
    // Ctrl+U - подчеркнутый
    if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        insertTag('u');
    }
    // Ctrl+K - ссылка
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        insertLink();
    }
});

// ========================================
// Emoji Picker
// ========================================

const emojiData = {
    smileys: ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '☺️', '😚', '😙', '🥲', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '🥸', '😎', '🤓', '🧐', '😕', '😟', '🙁', '☹️', '😮', '😯', '😲', '😳', '🥺', '😦', '😧', '😨', '😰', '😥', '😢', '😭', '😱', '😖', '😣', '😞', '😓', '😩', '😫', '🥱', '😤', '😡', '😠', '🤬', '😈', '👿', '💀', '☠️', '💩', '🤡', '👹', '👺', '👻', '👽', '👾', '🤖'],
    gestures: ['👋', '🤚', '🖐️', '✋', '🖖', '👌', '🤌', '🤏', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝', '🙏', '✍️', '💅', '🤳', '💪', '🦾', '🦿', '🦵', '🦶', '👂', '🦻', '👃', '🧠', '🫀', '🫁', '🦷', '🦴', '👀', '👁️', '👅', '👄', '👶', '🧒', '👦', '👧', '🧑', '👱', '👨', '🧔', '👩', '🧓', '👴', '👵', '🙍', '🙎', '🙅', '🙆', '💁', '🙋', '🧏', '🙇', '🤦', '🤷'],
    hearts: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '♥️', '🫶', '💌', '💋', '😻', '😽', '🥰', '😍', '😘', '😚', '💑', '👩‍❤️‍👨', '👨‍❤️‍👨', '👩‍❤️‍👩', '💏', '👩‍❤️‍💋‍👨', '👨‍❤️‍💋‍👨', '👩‍❤️‍💋‍👩'],
    animals: ['🐱', '🐶', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🐤', '🐣', '🐥', '🦆', '🦅', '🦉', '🦇', '🐺', '🐗', '🐴', '🦄', '🐝', '🪱', '🐛', '🦋', '🐌', '🐞', '🐜', '🪰', '🪲', '🪳', '🦟', '🦗', '🕷️', '🕸️', '🦂', '🐢', '🐍', '🦎', '🦖', '🦕', '🐙', '🦑', '🦐', '🦞', '🦀', '🐡', '🐠', '🐟', '🐬', '🐳', '🐋', '🦈', '🐊', '🐅', '🐆', '🦓', '🦍', '🦧', '🐘', '🦛', '🦏', '🐪', '🐫', '🦒', '🦘', '🦬', '🐃', '🐂', '🐄', '🐎', '🐖', '🐏', '🐑', '🦙', '🐐', '🦌', '🐕', '🐩', '🦮', '🐈', '🐓', '🦃', '🦤', '🦚', '🦜', '🦢', '🦩', '🐇', '🦝', '🦨', '🦡', '🦫', '🦦', '🦥', '🐁', '🐀', '🐿️', '🦔'],
    food: ['🍕', '🍔', '🍟', '🌭', '🍿', '🧂', '🥓', '🥚', '🍳', '🧇', '🥞', '🧈', '🍞', '🥐', '🥖', '🥨', '🧀', '🥗', '🥙', '🥪', '🌮', '🌯', '🫔', '🥫', '🍝', '🍜', '🍲', '🍛', '🍣', '🍱', '🥟', '🦪', '🍤', '🍙', '🍚', '🍘', '🍥', '🥠', '🥮', '🍢', '🍡', '🍧', '🍨', '🍦', '🥧', '🧁', '🍰', '🎂', '🍮', '🍭', '🍬', '🍫', '🍩', '🍪', '🌰', '🥜', '🍯', '🥛', '🍼', '☕', '🍵', '🧃', '🥤', '🧋', '🍶', '🍺', '🍻', '🥂', '🍷', '🥃', '🍸', '🍹', '🧉', '🍾', '🧊', '🥄', '🍴', '🍽️', '🥣', '🥡', '🥢', '🧂', '🍎', '🍏', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🫐', '🍈', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🍆', '🥑', '🥦', '🥬', '🥒', '🌶️', '🫑', '🌽', '🥕', '🫒', '🧄', '🧅', '🥔', '🍠'],
    activities: ['⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🎱', '🪀', '🏓', '🏸', '🏒', '🏑', '🥍', '🏏', '🪃', '🥅', '⛳', '🪁', '🏹', '🎣', '🤿', '🥊', '🥋', '🎽', '🛹', '🛼', '🛷', '⛸️', '🥌', '🎿', '⛷️', '🏂', '🪂', '🏋️', '🤼', '🤸', '🤺', '⛹️', '🤾', '🏌️', '🏇', '🧘', '🏄', '🏊', '🤽', '🚣', '🧗', '🚵', '🚴', '🏆', '🥇', '🥈', '🥉', '🏅', '🎖️', '🏵️', '🎗️', '🎫', '🎟️', '🎪', '🤹', '🎭', '🩰', '🎨', '🎬', '🎤', '🎧', '🎼', '🎹', '🥁', '🪘', '🎷', '🎺', '🪗', '🎸', '🪕', '🎻', '🎲', '♟️', '🎯', '🎳', '🎮', '🎰', '🧩'],
    travel: ['🚗', '🚕', '🚙', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐', '🛻', '🚚', '🚛', '🚜', '🦯', '🦽', '🦼', '🛴', '🚲', '🛵', '🏍️', '🛺', '🚨', '🚔', '🚍', '🚘', '🚖', '🚡', '🚠', '🚟', '🚃', '🚋', '🚞', '🚝', '🚄', '🚅', '🚈', '🚂', '🚆', '🚇', '🚊', '🚉', '✈️', '🛫', '🛬', '🛩️', '💺', '🛰️', '🚀', '🛸', '🚁', '🛶', '⛵', '🚤', '🛥️', '🛳️', '⛴️', '🚢', '⚓', '🪝', '⛽', '🚧', '🚦', '🚥', '🚏', '🗺️', '🗿', '🗽', '🗼', '🏰', '🏯', '🏟️', '🎡', '🎢', '🎠', '⛲', '⛱️', '🏖️', '🏝️', '🏜️', '🌋', '⛰️', '🏔️', '🗻', '🏕️', '⛺', '🛖', '🏠', '🏡', '🏘️', '🏚️', '🏗️', '🏭', '🏢', '🏬', '🏣', '🏤', '🏥', '🏦', '🏨', '🏪', '🏫', '🏩', '💒', '🏛️', '⛪', '🕌', '🕍', '🛕', '🕋', '⛩️'],
    objects: ['💡', '🔦', '🏮', '🪔', '📱', '📲', '💻', '🖥️', '🖨️', '⌨️', '🖱️', '🖲️', '💽', '💾', '💿', '📀', '🧮', '🎥', '🎞️', '📽️', '🎬', '📺', '📷', '📸', '📹', '📼', '🔍', '🔎', '🕯️', '💵', '💴', '💶', '💷', '💰', '💳', '💎', '⚖️', '🪜', '🧰', '🪛', '🔧', '🔨', '⚒️', '🛠️', '⛏️', '🪚', '🔩', '⚙️', '🪤', '🧱', '⛓️', '🧲', '🔫', '💣', '🧨', '🪓', '🔪', '🗡️', '⚔️', '🛡️', '🚬', '⚰️', '🪦', '⚱️', '🏺', '🔮', '📿', '🧿', '💈', '⚗️', '🔭', '🔬', '🕳️', '🩹', '🩺', '💊', '💉', '🩸', '🧬', '🦠', '🧫', '🧪', '🌡️', '🧹', '🪠', '🧺', '🧻', '🚽', '🚰', '🚿', '🛁', '🛀', '🧼', '🪥', '🪒', '🧽', '🪣', '🧴', '🛎️', '🔑', '🗝️', '🚪', '🪑', '🛋️', '🛏️', '🛌', '🧸', '🪆', '🖼️', '🪞', '🪟', '🛍️', '🛒', '🎁', '🎈', '🎏', '🎀', '🪄', '🎊', '🎉', '🎎', '🏮', '🎐', '🧧', '✉️', '📩', '📨', '📧', '💌', '📥', '📤', '📦', '🏷️', '🪧', '📪', '📫', '📬', '📭', '📮', '📯', '📜', '📃', '📄', '📑', '🧾', '📊', '📈', '📉', '🗒️', '🗓️', '📆', '📅', '🗑️', '📇', '🗃️', '🗳️', '🗄️', '📋', '📁', '📂', '🗂️', '🗞️', '📰', '📓', '📔', '📒', '📕', '📗', '📘', '📙', '📚', '📖', '🔖', '🧷', '🔗', '📎', '🖇️', '📐', '📏', '🧮', '📌', '📍', '✂️', '🖊️', '🖋️', '✒️', '🖌️', '🖍️', '📝', '✏️', '🔍', '🔎', '🔏', '🔐', '🔒', '🔓'],
    symbols: ['✅', '❌', '❓', '❗', '❕', '❔', '⭕', '🚫', '💯', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫', '⚪', '🟤', '🔶', '🔷', '🔸', '🔹', '🔺', '🔻', '💠', '🔘', '🔳', '🔲', '▪️', '▫️', '◾', '◽', '◼️', '◻️', '🟥', '🟧', '🟨', '🟩', '🟦', '🟪', '⬛', '⬜', '🟫', '♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓', '⛎', '🔀', '🔁', '🔂', '▶️', '⏩', '⏭️', '⏯️', '◀️', '⏪', '⏮️', '🔼', '⏫', '🔽', '⏬', '⏸️', '⏹️', '⏺️', '⏏️', '🎦', '🔅', '🔆', '📶', '📳', '📴', '♀️', '♂️', '⚧️', '✖️', '➕', '➖', '➗', '♾️', '‼️', '⁉️', '〰️', '💲', '⚕️', '♻️', '⚜️', '🔱', '📛', '🔰', '⭐', '🌟', '✨', '💫', '🌠', '🎇', '🎆', '🌈', '☀️', '🌤️', '⛅', '🌥️', '☁️', '🌦️', '🌧️', '⛈️', '🌩️', '🌨️', '❄️', '☃️', '⛄', '🌬️', '💨', '🌪️', '🌫️', '🌊', '💧', '💦', '☔', '🔥', '💥', '⚡', '✴️', '🆕', '🆙', '🆒', '🆓', '🆗', '🆖', '🆚', '🈁', '🈂️', '🈷️', '🈶', '🈯', '🉐', '🈹', '🈚', '🈲', '🉑', '🈸', '🈴', '🈳', '㊗️', '㊙️', '🈺', '🈵', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪', '🔘'],
    flags: ['🇺🇦', '🇺🇸', '🇬🇧', '🇩🇪', '🇫🇷', '🇮🇹', '🇪🇸', '🇵🇱', '🇨🇦', '🇦🇺', '🇯🇵', '🇰🇷', '🇨🇳', '🇮🇳', '🇧🇷', '🇲🇽', '🇦🇷', '🇨🇱', '🇨🇴', '🇵🇪', '🇻🇪', '🇪🇨', '🇧🇴', '🇵🇾', '🇺🇾', '🇵🇹', '🇳🇱', '🇧🇪', '🇨🇭', '🇦🇹', '🇸🇪', '🇳🇴', '🇩🇰', '🇫🇮', '🇮🇪', '🇮🇸', '🇬🇷', '🇹🇷', '🇷🇺', '🇮🇱', '🇪🇬', '🇿🇦', '🇳🇬', '🇰🇪', '🇹🇭', '🇻🇳', '🇮🇩', '🇵🇭', '🇲🇾', '🇸🇬', '🇳🇿', '🏳️', '🏴', '🏁', '🚩', '🎌', '🏳️‍🌈', '🏳️‍⚧️', '🏴‍☠️']
};

let currentEmojiCategory = 'smileys';
let emojiTargetField = null; // Целевое поле для вставки emoji

function openEmojiPicker() {
    emojiTargetField = null; // Сбрасываем, будет использоваться broadcastMessage
    document.getElementById('emojiPickerModal').style.display = 'block';
    document.getElementById('emojiSearch').value = '';
    showEmojiCategory('smileys');
}

function openEmojiPickerForField(fieldId) {
    emojiTargetField = fieldId; // Запоминаем целевое поле
    document.getElementById('emojiPickerModal').style.display = 'block';
    document.getElementById('emojiSearch').value = '';
    showEmojiCategory('smileys');
}

function closeEmojiPicker() {
    document.getElementById('emojiPickerModal').style.display = 'none';
}

function showEmojiCategory(category) {
    currentEmojiCategory = category;

    // Обновляем активную кнопку категории
    document.querySelectorAll('.emoji-cat-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.cat === category);
    });

    renderEmojis(emojiData[category]);
}

function renderEmojis(emojis) {
    const grid = document.getElementById('emojiGrid');
    grid.innerHTML = emojis.map(emoji =>
        `<button class="emoji-item" onclick="selectEmoji('${emoji}')" title="${emoji}">${emoji}</button>`
    ).join('');
}

function selectEmoji(emoji) {
    if (emojiTargetField) {
        // Вставляем в указанное поле (например, modalEmoji)
        const field = document.getElementById(emojiTargetField);
        if (field) {
            field.value = emoji;
            field.focus();
        }
    } else {
        // Стандартное поведение - вставляем в broadcastMessage
        insertEmoji(emoji);
    }
    closeEmojiPicker();
}

function filterEmojis() {
    const searchTerm = document.getElementById('emojiSearch').value.toLowerCase();

    if (!searchTerm) {
        showEmojiCategory(currentEmojiCategory);
        return;
    }

    // Поиск по всем категориям
    const allEmojis = Object.values(emojiData).flat();
    const filtered = allEmojis.filter(emoji => emoji.includes(searchTerm));

    // Убираем активную категорию при поиске
    document.querySelectorAll('.emoji-cat-btn').forEach(btn => btn.classList.remove('active'));

    renderEmojis(filtered.length > 0 ? filtered : allEmojis.slice(0, 50));
}

// Закрытие emoji picker по клику вне окна
window.addEventListener('click', function(event) {
    const modal = document.getElementById('emojiPickerModal');
    if (event.target === modal) {
        closeEmojiPicker();
    }
});

// Закрытие по Escape
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const emojiModal = document.getElementById('emojiPickerModal');
        if (emojiModal && emojiModal.style.display === 'block') {
            closeEmojiPicker();
        }
    }
});
