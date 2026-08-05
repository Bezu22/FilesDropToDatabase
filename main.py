from datetime import datetime
import hashlib
import os
import shutil
import tkinter.messagebox as messagebox
import customtkinter as ctk

from config import MACHINES, MAIN_DB_PATH
from panels.bottom_panel import BottomPanel
from panels.database_panel import DatabasePanel
from panels.machine_panel import MachinePanel

ctk.set_appearance_mode("Dark")


def calculate_sha256(file_path):
    """Oblicza sumę kontrolną SHA-256 pliku, aby zagwarantować spójność danych."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Odczyt w kawałkach (chunks) dla wydajności przy większych plikach
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class NetworkFileManager(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Network File Manager")
        self.geometry("1100x700")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

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
        self.right_panel.set_search_query(file_name)

    def verify_file_integrity(self, source_path, dest_path):
        """Weryfikuje rozmiar oraz sumę kontrolną SHA-256 kopiowanego pliku."""
        # 1. Sprawdzenie czy plik istnieje
        if not dest_path.exists():
            return False, "Plik docelowy nie istnieje."

        # 2. Sprawdzenie rozmiarów plików
        if source_path.stat().st_size != dest_path.stat().st_size:
            return False, "Rozmiary plików się nie zgadzają!"

        # 3. Sprawdzenie SHA-256
        if calculate_sha256(source_path) != calculate_sha256(dest_path):
            return False, "Suma kontrolna SHA-256 jest niezgodna!"

        return True, "Plik zweryfikowany pomyślnie."

    def archive_file_to_database(self, file_path, machine_name):
        try:
            # 1. Generowanie daty i nazwy katalogu
            mtime = os.path.getmtime(file_path)
            file_date = datetime.fromtimestamp(mtime)
            date_str = file_date.strftime("%d_%m_%y %H_%M")

            folder_name = f"WYKONANIE {machine_name} {date_str}"
            destination_dir = self.right_panel.current_path / folder_name

            # 2. Tworzenie katalogu
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination_file_path = destination_dir / file_path.name

            # 3. Kopiowanie
            shutil.copy2(file_path, destination_file_path)

            # 4. GWARANCJA I WERYFIKACJA SPÓJNOŚCI PLIKU
            is_valid, msg = self.verify_file_integrity(
                file_path, destination_file_path
            )

            if not is_valid:
                raise Exception(f"Błąd weryfikacji pliku: {msg}")

            # 5. AUTOMATYCZNE INDEKSOWANIE W SZYBKIEJ BAZIE SQLITE
            self.right_panel.db.add_single_path(destination_dir, is_dir=True)
            self.right_panel.db.add_single_path(
                destination_file_path, is_dir=False
            )

            # 6. ODŚWIEŻENIE WIDOKU PRAWEGO PANELU
            self.right_panel.refresh_view()

            # Informacja dla użytkownika
            self.left_panel.status_label.configure(
                text=f"🟢 Zarchiwizowano i zweryfikowano: {file_path.name}",
                text_color="#55FF55",
            )

            # OPCJONALNIE: Jeśli w przyszłości zechcesz usuwać plik z maszyny,
            # robimy to dopiero po przejściu testu is_valid:
            # os.remove(file_path)

        except Exception as e:
            messagebox.showerror(
                "Błąd archiwizacji",
                f"Nie udało się przenieść/zarchiwizować pliku:\n{str(e)}",
            )


if __name__ == "__main__":
    app = NetworkFileManager()
    app.mainloop()