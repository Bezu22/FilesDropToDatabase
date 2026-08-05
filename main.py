from datetime import datetime
import hashlib
import os
import shutil
import threading
import tkinter.messagebox as messagebox
import customtkinter as ctk

# Import konfiguracji oraz paneli interfejsu
from config import MACHINES, MAIN_DB_PATH
from panels.bottom_panel import BottomPanel
from panels.database_panel import DatabasePanel
from panels.machine_panel import MachinePanel

# Ustawienie ciemnego motywu w customtkinter
ctk.set_appearance_mode("Dark")


def calculate_sha256(file_path):
    """Oblicza sumę kontrolną SHA-256 pliku.

    Funkcja czyta plik w małych fragmentach (4 KB), dzięki czemu nie przeciąża
    pamięci RAM nawet przy dużych plikach.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class NetworkFileManager(ctk.CTk):
    """Główne okno aplikacji zarządzania plikami i ich archiwizacją."""

    def __init__(self):
        super().__init__()

        # --- Konfiguracja Okna ---
        self.title("Network File Manager")
        self.geometry("1100x700")

        # Układ siatki (Grid)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # --- Inicjalizacja Paneli ---
        self.right_panel = DatabasePanel(self, MAIN_DB_PATH)
        self.right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.left_panel = MachinePanel(
            self,
            MACHINES,
            on_search_in_db_callback=self.search_file_in_database,
            on_archive_callback=self.archive_file_to_database,
        )
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.bottom_panel = BottomPanel(self)
        self.bottom_panel.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew"
        )

    def search_file_in_database(self, file_name):
        """Przekazuje nazwę pliku z lewego panelu do paska wyszukiwania w prawym panelu."""
        self.right_panel.set_search_query(file_name)

    def verify_file_integrity(self, source_path, dest_path):
        """Weryfikuje, czy kopiowanie przebiegło poprawnie (istnienie, rozmiar, SHA-256)."""
        if not dest_path.exists():
            return False, "Plik docelowy nie istnieje w ścieżce archiwum."

        if source_path.stat().st_size != dest_path.stat().st_size:
            return False, "Niezgodność rozmiaru plików!"

        if calculate_sha256(source_path) != calculate_sha256(dest_path):
            return False, "Suma kontrolna SHA-256 jest niezgodna!"

        return True, "Plik zweryfikowany pomyślnie."

    def archive_file_to_database(self, file_path, machine_name):
        """Uruchamia proces archiwizacji w osobnym wątku, aby uniknąć zawieszenia UI."""

        # 1. Informujemy użytkownika o rozpoczęciu pracy i blokujemy panel
        self.left_panel.status_label.configure(
            text=f"⏳ Trwa archiwizacja pliku: {file_path.name}...",
            text_color="orange",
        )

        # 2. Tworzymy i uruchamiamy wątek roboczy (Worker Thread)
        threading.Thread(
            target=self._async_archive_process,
            args=(file_path, machine_name),
            daemon=True,
        ).start()

    def _async_archive_process(self, file_path, machine_name):
        """Metoda wykonywana w tle (w osobnym wątku)."""
        try:
            # --- KROK 1: Przygotowanie ścieżki docelowej ---
            mtime = os.path.getmtime(file_path)
            file_date = datetime.fromtimestamp(mtime)
            date_str = file_date.strftime("%d_%m_%y %H_%M")

            folder_name = f"WYKONANIE {machine_name} {date_str}"
            destination_dir = self.right_panel.current_path / folder_name

            # --- KROK 2: Tworzenie folderu i kopiowanie ---
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination_file_path = destination_dir / file_path.name

            shutil.copy2(file_path, destination_file_path)

            # --- KROK 3: Weryfikacja spójności (długotrwałe przeliczenie SHA-256) ---
            is_valid, msg = self.verify_file_integrity(
                file_path, destination_file_path
            )

            if not is_valid:
                raise Exception(f"Błąd weryfikacji pliku: {msg}")

            # --- KROK 4: Indeksowanie w bazie SQLite ---
            self.right_panel.db.add_single_path(destination_dir, is_dir=True)
            self.right_panel.db.add_single_path(
                destination_file_path, is_dir=False
            )

            # --- KROK 5: Bezpieczne usuwanie pliku źródłowego ---
            os.remove(file_path)

            # --- KROK 6: Sukces - aktualizacja interfejsu z poziomu głównego wątku ---
            self.after(
                0, lambda: self._on_archive_success(file_path, destination_dir)
            )

        except Exception as e:
            # Reagujemy na błędy w głównym wątku UI
            error_msg = str(e)
            self.after(0, lambda: self._on_archive_error(error_msg))

    def _on_archive_success(self, file_path, destination_dir):
        """Służy do bezpiecznego odświeżenia elementów interfejsu po sukcesie."""
        # Odświeżenie prawego panelu z bazą
        self.right_panel.refresh_view()

        # Odświeżenie lewego panelu i reset zaznaczenia
        self.left_panel.refresh_view()
        self.left_panel._clear_selection()

        # Powiadomienie w pasek statusu
        self.left_panel.status_label.configure(
            text=f"🟢 Przeniesiono i zweryfikowano: {file_path.name}",
            text_color="#55FF55",
        )

    def _on_archive_error(self, error_message):
        """Służy do bezpiecznego wyświetlenia błędu w interfejsie."""
        self.left_panel.status_label.configure(
            text="🔴 Błąd archiwizacji!", text_color="#FF5555"
        )
        messagebox.showerror(
            "Błąd archiwizacji",
            f"Nie udało się przenieść/zarchiwizować pliku:\n{error_message}",
        )


if __name__ == "__main__":
    app = NetworkFileManager()
    app.mainloop()