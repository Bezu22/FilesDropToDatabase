from datetime import datetime
from pathlib import Path
import customtkinter as ctk


class BottomPanel(ctk.CTkFrame):
    """
    Dolny panel informacyjny.
    Wyświetla ścieżkę oraz datę ostatniej modyfikacji TYLKO dla zaznaczonego elementu.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Etykieta tekstowa do wyświetlania informacji
        self.info_label = ctk.CTkLabel(
            self,
            text="Wybierz plik lub folder, aby zobaczyć szczegóły...",
            anchor="w",
            font=("Arial", 12),
        )
        self.info_label.pack(fill="x", padx=10, pady=5)

    def update_info(self, file_path):
        """
        Pobiera i wyświetla datę modyfikacji oraz rozmiar dla JEDNEGO zaznaczonego obiektu.
        """
        p = Path(file_path)

        # Jeśli ścieżka nie istnieje na dysku (np. błąd w bazie)
        if not p.exists():
            self.info_label.configure(
                text=f"Wybrano: {p.name} (Brak pliku na dysku)"
            )
            return

        try:
            # Odczytujemy czas ostatniej modyfikacji z systemu plików
            mtime = p.stat().st_mtime
            date_formatted = datetime.fromtimestamp(mtime).strftime(
                "%d.%m.%Y %H:%M:%S"
            )

            if p.is_dir():
                self.info_label.configure(
                    text=f"📁 Zaznaczony folder: {p.name}  |  Data modyfikacji: {date_formatted}"
                )
            else:
                # Rozmiar pliku w KB
                size_kb = round(p.stat().st_size / 1024, 2)
                self.info_label.configure(
                    text=f"📄 Zaznaczony plik: {p.name}  |  Rozmiar: {size_kb} KB  |  Data modyfikacji: {date_formatted}"
                )
        except Exception as e:
            self.info_label.configure(text=f"Wybrano: {p.name}")