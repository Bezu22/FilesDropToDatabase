from datetime import datetime
from pathlib import Path
import customtkinter as ctk


class BottomPanel(ctk.CTkFrame):
    """Panel dolny podzielony na dwie kolumny, wyświetlający daty modyfikacji

    dla elementów zaznaczonych w lewym i prawym panelu.
    """

    def __init__(self, parent):
        super().__init__(parent, height=35)
        self.pack_propagate(False)

        # Siatka 1 wiersz, 2 kolumny o równej szerokości
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)

        # Lewa kolumna (Komputer Lokalny)
        self.left_label = ctk.CTkLabel(
            self,
            text="Lokalny: Brak zaznaczenia",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.left_label.grid(row=0, column=0, padx=10, pady=2, sticky="ew")

        # Prawa kolumna (Baza Główna)
        self.right_label = ctk.CTkLabel(
            self,
            text="Baza: Brak zaznaczenia",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.right_label.grid(row=0, column=1, padx=10, pady=2, sticky="ew")

    def _format_date(self, path):
        """Format pomocniczy do odczytu daty pliku/folderu."""
        if not path:
            return "Brak zaznaczenia"

        target_path = Path(path)
        if not target_path.exists():
            return f"{target_path.name} | [Brak pliku]"

        try:
            mtime = target_path.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            return f"{target_path.name} | Data: {date_str}"
        except Exception:
            return f"{target_path.name} | Błąd daty"

    def update_left_info(self, path):
        """Aktualizuje tekst w lewej kolumnie (zaznaczenie z lewego panelu)."""
        text_info = self._format_date(path)
        self.left_label.configure(text=f"Lokalnie: {text_info}")

    def update_right_info(self, path):
        """Aktualizuje tekst w prawej kolumnie (zaznaczenie z prawego panelu)."""
        text_info = self._format_date(path)
        self.right_label.configure(text=f"Baza: {text_info}")