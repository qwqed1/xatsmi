import os
import io
import base64
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import cv2
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Конфигурация
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# Создаем необходимые папки
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_base64(image):
    """Конвертирует PIL Image в base64 строку"""
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def base64_to_image(base64_str):
    """Конвертирует base64 строку в PIL Image"""
    if base64_str.startswith('data:image'):
        base64_str = base64_str.split(',')[1]
    image_data = base64.b64decode(base64_str)
    return Image.open(io.BytesIO(image_data))

class ImageProcessor:
    @staticmethod
    def upscale_image(image, scale_factor=1.5):
        """Увеличение разрешения изображения"""
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        
        # Конвертируем PIL в OpenCV для лучшего апскейлинга
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        upscaled = cv2.resize(cv_image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Конвертируем обратно в PIL
        upscaled_rgb = cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB)
        return Image.fromarray(upscaled_rgb)
    
    @staticmethod
    def apply_blur(image, radius=2):
        """Применение размытия"""
        return image.filter(ImageFilter.GaussianBlur(radius=radius))
    
    @staticmethod
    def remove_blur(image, strength=1.5):
        """Уменьшение размытия (повышение резкости)"""
        return image.filter(ImageFilter.UnsharpMask(radius=2, percent=int(strength * 100), threshold=3))
    
    @staticmethod
    def adjust_brightness(image, factor=1.2):
        """Регулировка яркости"""
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)
    
    @staticmethod
    def adjust_contrast(image, factor=1.2):
        """Регулировка контрастности"""
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)
    
    @staticmethod
    def adjust_saturation(image, factor=1.2):
        """Регулировка насыщенности"""
        enhancer = ImageEnhance.Color(image)
        return enhancer.enhance(factor)
    
    @staticmethod
    def apply_grayscale(image):
        """Черно-белый фильтр"""
        return ImageOps.grayscale(image).convert('RGB')
    
    @staticmethod
    def apply_sepia(image):
        """Сепия фильтр"""
        pixels = np.array(image)
        
        # Матрица для сепии
        sepia_filter = np.array([
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131]
        ])
        
        sepia_img = pixels.dot(sepia_filter.T)
        sepia_img = np.clip(sepia_img, 0, 255)
        return Image.fromarray(sepia_img.astype(np.uint8))
    
    @staticmethod
    def apply_vintage(image):
        """Винтажный фильтр"""
        # Снижаем яркость и контрастность
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(0.9)
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        # Добавляем желтоватый оттенок
        pixels = np.array(image)
        pixels[:, :, 0] = np.clip(pixels[:, :, 0] + 10, 0, 255)  # Красный
        pixels[:, :, 1] = np.clip(pixels[:, :, 1] + 5, 0, 255)   # Зеленый
        
        return Image.fromarray(pixels)
    
    @staticmethod
    def enhance_image(image):
        """Автоматическое улучшение изображения"""
        # Небольшое повышение контрастности и резкости
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Открываем изображение
            image = Image.open(file.stream)
            
            # Конвертируем в RGB если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Возвращаем base64 изображения
            base64_img = image_to_base64(image)
            
            return jsonify({
                'success': True,
                'image': base64_img,
                'width': image.width,
                'height': image.height
            })
        
        except Exception as e:
            return jsonify({'error': f'Error processing image: {str(e)}'}), 400
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/process', methods=['POST'])
def process_image():
    data = request.json
    
    if 'image' not in data or 'operation' not in data:
        return jsonify({'error': 'Missing image or operation'}), 400
    
    try:
        # Получаем изображение из base64
        image = base64_to_image(data['image'])
        processor = ImageProcessor()
        
        operation = data['operation']
        params = data.get('params', {})
        
        # Применяем нужную операцию
        if operation == 'upscale':
            scale = params.get('scale', 1.5)
            processed_image = processor.upscale_image(image, scale)
            
        elif operation == 'blur':
            radius = params.get('radius', 2)
            processed_image = processor.apply_blur(image, radius)
            
        elif operation == 'sharpen':
            strength = params.get('strength', 1.5)
            processed_image = processor.remove_blur(image, strength)
            
        elif operation == 'brightness':
            factor = params.get('factor', 1.2)
            processed_image = processor.adjust_brightness(image, factor)
            
        elif operation == 'contrast':
            factor = params.get('factor', 1.2)
            processed_image = processor.adjust_contrast(image, factor)
            
        elif operation == 'saturation':
            factor = params.get('factor', 1.2)
            processed_image = processor.adjust_saturation(image, factor)
            
        elif operation == 'grayscale':
            processed_image = processor.apply_grayscale(image)
            
        elif operation == 'sepia':
            processed_image = processor.apply_sepia(image)
            
        elif operation == 'vintage':
            processed_image = processor.apply_vintage(image)
            
        elif operation == 'enhance':
            processed_image = processor.enhance_image(image)
            
        else:
            return jsonify({'error': 'Unknown operation'}), 400
        
        # Возвращаем обработанное изображение
        result_base64 = image_to_base64(processed_image)
        
        return jsonify({
            'success': True,
            'image': result_base64,
            'width': processed_image.width,
            'height': processed_image.height
        })
    
    except Exception as e:
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_image():
    data = request.json
    
    if 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        # Получаем изображение из base64
        image = base64_to_image(data['image'])
        
        # Сохраняем во временный файл
        filename = f"processed_{hash(str(data['image'])[:100])}.png"
        filepath = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        
        image.save(filepath, 'PNG')
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{filename}'
        })
    
    except Exception as e:
        return jsonify({'error': f'Error preparing download: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

if __name__ == '__main__':
    # HTML шаблон будет создан отдельно
    html_template = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Редактор изображений</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Редактор изображений</h1>
        
        <div class="upload-section">
            <input type="file" id="fileInput" accept="image/*" style="display: none;">
            <button id="uploadBtn" class="btn-primary">Загрузить изображение</button>
        </div>
        
        <div id="imageSection" class="image-section hidden">
            <div class="image-container">
                <div class="image-box">
                    <h3>Исходное изображение</h3>
                    <img id="originalImage" alt="Original">
                    <div class="image-info" id="originalInfo"></div>
                </div>
                
                <div class="image-box">
                    <h3>Обработанное изображение</h3>
                    <img id="processedImage" alt="Processed">
                    <div class="image-info" id="processedInfo"></div>
                </div>
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <h3>Качество изображения</h3>
                    <div class="control-buttons">
                        <button class="btn-secondary" onclick="processImage('upscale', {scale: 1.5})">Увеличить до 1080p</button>
                        <button class="btn-secondary" onclick="processImage('upscale', {scale: 2})">Увеличить 2x</button>
                        <button class="btn-secondary" onclick="processImage('enhance')">Автоулучшение</button>
                    </div>
                </div>
                
                <div class="control-group">
                    <h3>Размытие и резкость</h3>
                    <div class="control-buttons">
                        <button class="btn-secondary" onclick="processImage('blur', {radius: 1})">Легкое размытие</button>
                        <button class="btn-secondary" onclick="processImage('blur', {radius: 3})">Сильное размытие</button>
                        <button class="btn-secondary" onclick="processImage('sharpen', {strength: 1.5})">Повысить резкость</button>
                        <button class="btn-secondary" onclick="processImage('sharpen', {strength: 2})">Сильная резкость</button>
                    </div>
                </div>
                
                <div class="control-group">
                    <h3>Настройки изображения</h3>
                    <div class="control-buttons">
                        <button class="btn-secondary" onclick="processImage('brightness', {factor: 1.3})">Увеличить яркость</button>
                        <button class="btn-secondary" onclick="processImage('brightness', {factor: 0.8})">Уменьшить яркость</button>
                        <button class="btn-secondary" onclick="processImage('contrast', {factor: 1.3})">Увеличить контраст</button>
                        <button class="btn-secondary" onclick="processImage('saturation', {factor: 1.4})">Насыщенность</button>
                    </div>
                </div>
                
                <div class="control-group">
                    <h3>Фильтры</h3>
                    <div class="control-buttons">
                        <button class="btn-secondary" onclick="processImage('grayscale')">Черно-белый</button>
                        <button class="btn-secondary" onclick="processImage('sepia')">Сепия</button>
                        <button class="btn-secondary" onclick="processImage('vintage')">Винтаж</button>
                    </div>
                </div>
                
                <div class="download-section">
                    <button id="downloadBtn" class="btn-primary">Скачать результат</button>
                </div>
            </div>
        </div>
        
        <div id="loading" class="loading hidden">Обработка...</div>
    </div>
    
    <script src="/static/script.js"></script>
</body>
</html>'''
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("Сервер запущен на http://127.0.0.1:5000")
    print("Убедитесь, что установлены все зависимости:")
    print("pip install flask flask-cors pillow opencv-python numpy")
    
    app.run(debug=True)