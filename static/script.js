let originalImageData = null;
let processedImageData = null;

document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const imageSection = document.getElementById('imageSection');
    const loading = document.getElementById('loading');
    const originalImage = document.getElementById('originalImage');
    const processedImage = document.getElementById('processedImage');
    const originalInfo = document.getElementById('originalInfo');
    const processedInfo = document.getElementById('processedInfo');
    const downloadBtn = document.getElementById('downloadBtn');

    // Обработчик кнопки загрузки
    uploadBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // Обработчик выбора файла
    fileInput.addEventListener('change', handleFileUpload);

    // Обработчик скачивания
    downloadBtn.addEventListener('click', downloadImage);

    // Drag & Drop функциональность
    setupDragAndDrop();

    function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        showLoading();
        
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                originalImageData = data.image;
                processedImageData = data.image; // Изначально копия оригинала
                
                displayImages(data.image, data.image, data);
                showImageSection();
            } else {
                showError(data.error);
            }
        })
        .catch(error => {
            hideLoading();
            showError('Ошибка загрузки файла: ' + error.message);
        });
    }

    function displayImages(originalBase64, processedBase64, info) {
        originalImage.src = originalBase64;
        processedImage.src = processedBase64;
        
        originalInfo.textContent = `Размер: ${info.width}x${info.height}px`;
        processedInfo.textContent = `Размер: ${info.width}x${info.height}px`;
    }

    function showImageSection() {
        imageSection.classList.remove('hidden');
    }

    function showLoading() {
        loading.classList.remove('hidden');
        loading.textContent = 'Загрузка изображения...';
    }

    function hideLoading() {
        loading.classList.add('hidden');
    }

    function showError(message) {
        alert('Ошибка: ' + message);
    }

    // Функция для обработки изображения
    window.processImage = function(operation, params = {}) {
        if (!originalImageData) {
            showError('Сначала загрузите изображение');
            return;
        }

        showLoading();
        loading.textContent = getProcessingMessage(operation);

        const requestData = {
            image: processedImageData, // Используем текущее обработанное изображение
            operation: operation,
            params: params
        };

        fetch('/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                processedImageData = data.image;
                processedImage.src = data.image;
                processedInfo.textContent = `Размер: ${data.width}x${data.height}px`;
                
                // Добавляем анимацию
                processedImage.style.transform = 'scale(1.05)';
                setTimeout(() => {
                    processedImage.style.transform = 'scale(1)';
                }, 300);
            } else {
                showError(data.error);
            }
        })
        .catch(error => {
            hideLoading();
            showError('Ошибка обработки: ' + error.message);
        });
    };

    function getProcessingMessage(operation) {
        const messages = {
            'upscale': 'Увеличение разрешения...',
            'blur': 'Применение размытия...',
            'sharpen': 'Повышение резкости...',
            'brightness': 'Настройка яркости...',
            'contrast': 'Настройка контраста...',
            'saturation': 'Настройка насыщенности...',
            'grayscale': 'Применение ч/б фильтра...',
            'sepia': 'Применение сепии...',
            'vintage': 'Применение винтажного фильтра...',
            'enhance': 'Автоматическое улучшение...'
        };
        return messages[operation] || 'Обработка изображения...';
    }

    function downloadImage() {
        if (!processedImageData) {
            showError('Нет обработанного изображения для скачивания');
            return;
        }

        showLoading();
        loading.textContent = 'Подготовка к скачиванию...';

        fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image: processedImageData
            })
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            
            if (data.success) {
                // Создаем ссылку для скачивания
                const link = document.createElement('a');
                link.href = data.download_url;
                link.download = 'processed_image.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                showError(data.error);
            }
        })
        .catch(error => {
            hideLoading();
            showError('Ошибка скачивания: ' + error.message);
        });
    }

    function setupDragAndDrop() {
        const body = document.body;

        body.addEventListener('dragover', (e) => {
            e.preventDefault();
            body.classList.add('drag-over');
        });

        body.addEventListener('dragleave', (e) => {
            if (!body.contains(e.relatedTarget)) {
                body.classList.remove('drag-over');
            }
        });

        body.addEventListener('drop', (e) => {
            e.preventDefault();
            body.classList.remove('drag-over');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type.startsWith('image/')) {
                    // Симулируем выбор файла
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    fileInput.files = dt.files;
                    
                    // Запускаем обработку
                    handleFileUpload({ target: { files: [file] } });
                } else {
                    showError('Пожалуйста, выберите файл изображения');
                }
            }
        });
    }

    // Добавляем кнопку сброса
    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Сбросить к оригиналу';
    resetBtn.className = 'btn-secondary';
    resetBtn.onclick = function() {
        if (originalImageData) {
            processedImageData = originalImageData;
            processedImage.src = originalImageData;
            
            // Получаем размеры из оригинального изображения
            const img = new Image();
            img.onload = function() {
                processedInfo.textContent = `Размер: ${img.width}x${img.height}px`;
            };
            img.src = originalImageData;
        }
    };

    // Добавляем кнопку сброса в секцию загрузки
    const downloadSection = document.querySelector('.download-section');
    if (downloadSection) {
        downloadSection.insertBefore(resetBtn, downloadBtn);
    }

    // Добавляем горячие клавиши
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey) {
            switch(e.key) {
                case 'o':
                    e.preventDefault();
                    fileInput.click();
                    break;
                case 's':
                    e.preventDefault();
                    if (processedImageData) downloadImage();
                    break;
                case 'z':
                    e.preventDefault();
                    resetBtn.click();
                    break;
            }
        }
    });

    // Показываем подсказки по горячим клавишам
    const shortcutsInfo = document.createElement('div');
    shortcutsInfo.innerHTML = `
        <div style="position: fixed; bottom: 20px; right: 20px; background: rgba(0,0,0,0.8); color: white; padding: 10px; border-radius: 10px; font-size: 12px; z-index: 1000;">
            <div>Ctrl+O - Открыть файл</div>
            <div>Ctrl+S - Сохранить</div>
            <div>Ctrl+Z - Сбросить</div>
        </div>
    `;
    document.body.appendChild(shortcutsInfo);
});