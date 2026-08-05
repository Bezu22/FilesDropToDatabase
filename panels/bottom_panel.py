from datetime import datetime
import os
from pathlib import Path
import subprocess
import customtkinter as ctk


class BottomPanel(ctk.CTkFrame):
    """Panel dolny wyświetlający daty modyfikacji elementów zaznaczonych

    w lewym i prawym panelu oraz przycisk otwierania w Eksploratorze.
    """

    def __init__(self, parent):
        super().__init__(parent, height=35)
        self.pack_propagate(False)

        # Siatka: kolumny 0 i 1 rozciągają się po równo, kolumna 2 mieści przycisk Explorer
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

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

        # Przycisk otwierania w Eksploratorze Windows
        self.btn_explorer = ctk.CTkButton(
            self,
            text="📂 Explorer",
            width=90,
            command=self.open_in_explorer,
        )
        self.btn_explorer.grid(row=0, column=2, padx=(5, 10), pady=2, sticky="e")

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

    def open_in_explorer(self):
        """Otwiera OSTATNIO zaznaczony element (z dowolnego panelu) w Eksploratorze Windows."""
        app = self.winfo_toplevel()
        last_path = getattr(app, "last_selected_path", None)

        if not last_path:
            return

        path_obj = Path(last_path)

        if not path_obj.exists():
            return

        try:
            if path_obj.is_file():
                # Przełącznik /select otwiera folder nadrzędny i zaznacza plik
                subprocess.Popen(f'explorer /select,"{path_obj}"')
            else:
                # Otwiera folder
                subprocess.Popen(f'explorer "{path_obj}"')
        except Exception as e:
            print(f"Błąd otwierania w eksploratorze: {e}")