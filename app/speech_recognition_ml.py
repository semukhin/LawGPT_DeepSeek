import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import librosa

class LegalSpeechRecognitionModel:
    def __init__(self, language='ru'):
        """
        Специализированная модель распознавания речи для юридической лексики
        
        :param language: Язык распознавания ('ru', 'en')
        """
        self.language = language
        self.model = None
        self.scaler = StandardScaler()
        self.legal_vocabulary = self._load_legal_vocabulary()
    
    def _load_legal_vocabulary(self):
        """
        Загрузка юридической лексики для специализированного распознавания
        """
        vocabularies = {
            'ru': [
                'договор', 'право', 'закон', 'иск', 
                'судебное', 'решение', 'арбитраж', 
                'гражданский', 'уголовный', 'ответственность'
            ],
            'en': [
                'contract', 'law', 'legal', 'lawsuit', 
                'court', 'litigation', 'arbitration', 
                'civil', 'criminal', 'liability'
            ]
        }
        return vocabularies.get(self.language, [])
    
    def extract_features(self, audio_path):
        """
        Извлечение акустических признаков из аудиофайла
        """
        try:
            # Загрузка аудио
            audio, sample_rate = librosa.load(audio_path, res_type='kaiser_fast')
            
            # Извлечение mel-спектрограммы
            mel_spectrogram = librosa.feature.melspectrogram(
                y=audio, 
                sr=sample_rate, 
                n_mels=128,
                fmax=8000
            )
            
            # Логарифмическая шкала энергии
            log_mel_spectrogram = librosa.power_to_db(mel_spectrogram)
            
            # Нормализация
            features = self.scaler.fit_transform(
                log_mel_spectrogram.T
            )
            
            return features
        except Exception as e:
            print(f"Ошибка при извлечении признаков: {e}")
            return None
    
    def build_model(self, input_shape):
        """
        Построение нейронной сети для распознавания речи
        """
        self.model = Sequential([
            LSTM(256, return_sequences=True, input_shape=input_shape),
            Dropout(0.3),
            LSTM(128),
            Dropout(0.3),
            Dense(64, activation='relu'),
            Dense(len(self.legal_vocabulary), activation='softmax')
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
    
    def train(self, audio_paths, labels):
        """
        Тренировка модели на юридических аудиозаписях
        
        :param audio_paths: Список путей к аудиофайлам
        :param labels: Метки классов
        """
        # Подготовка данных
        X = []
        for path in audio_paths:
            features = self.extract_features(path)
            if features is not None:
                X.append(features)
        
        X = np.array(X)
        y = tf.keras.utils.to_categorical(labels, num_classes=len(self.legal_vocabulary))
        
        # Разделение на train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Построение модели
        self.build_model((X_train.shape[1], X_train.shape[2]))
        
        # Обучение
        self.model.fit(
            X_train, y_train, 
            epochs=50, 
            batch_size=32, 
            validation_split=0.2
        )
        
        # Оценка модели
        test_loss, test_accuracy = self.model.evaluate(X_test, y_test)
        print(f"Точность на тестовых данных: {test_accuracy * 100:.2f}%")
    
    def predict(self, audio_path):
        """
        Распознавание речи с использованием обученной модели
        
        :param audio_path: Путь к аудиофайлу
        :return: Распознанный текст
        """
        features = self.extract_features(audio_path)
        
        if features is None:
            return None
        
        # Предсказание
        prediction = self.model.predict(np.expand_dims(features, axis=0))
        
        # Получаем индекс наиболее вероятного класса
        predicted_class_index = np.argmax(prediction)
        
        return self.legal_vocabulary[predicted_class_index]

# Пример использования
def train_legal_speech_model(audio_directory):
    """
    Тренировка модели на директории с юридическими аудиозаписями
    """
    model = LegalSpeechRecognitionModel(language='ru')
    
    # Сбор путей к аудиофайлам и меток
    audio_paths = []
    labels = []
    
    for filename in os.listdir(audio_directory):
        if filename.endswith(('.wav', '.mp3')):
            audio_paths.append(os.path.join(audio_directory, filename))
            # Определение метки на основе имени файла или структуры директории
            label = determine_label(filename)
            labels.append(label)
    
    model.train(audio_paths, labels)
    return model

def determine_label(filename):
    """
    Определение метки класса на основе имени файла
    """
    # Простая логика присвоения меток
    legal_categories = {
        'contract': 0,
        'lawsuit': 1,
        'court_decision': 2
    }
    
    for category, label in legal_categories.items():
        if category in filename.lower():
            return label
    
    return 0  # Метка по умолчанию