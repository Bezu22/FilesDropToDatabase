import logging
from pathlib import Path

# Ścieżka do pliku z logami
LOG_FILE_PATH = Path("app_activity.log")

def setup_logger():
    """Konfiguruje i zwraca obiekt loggera zapisanego do pliku .txt."""
    logger = logging.getLogger("NetworkFileManager")
    logger.setLevel(logging.INFO)

    # Zapobiegamy powielaniu uchwytów (handlers) przy wielokrotnym wywołaniu
    if not logger.handlers:
        # FileHandler odpowiada za zapis do pliku w trybie dopisywania (append, utf-8)
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        
        # Formatowanie: Data i czas | Poziom (INFO/ERROR) | Wiadomość
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)

    return logger

# Tworzymy jedną gotową instancję, z której będziemy korzystać w całym projekcie
app_logger = setup_logger()