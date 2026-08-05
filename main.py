from datetime import datetime
import hashlib
import os
import shutil
import threading
import tkinter.messagebox as messagebox
import customtkinter as ctk

from config import MACHINES, MAIN_DB_PATH
from logger import app_logger  # <--- IMPORT NASZEGO LOGGERA
from panels.bottom_panel import BottomPanel
from panels.database_panel import DatabasePanel
from panels.machine_panel import MachinePanel

ctk.set_appearance_mode("Dark")


def calculate_sha256(file_path):
    """Oblicza sumę kontrolną SHA-256 pliku w porcjach 4 KB."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
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
            on_delete_callback=self.delete_item_from_machine,
        )
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.bottom_panel = BottomPanel(self)
        self.bottom_panel.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew"
        )
        
        # Logowanie startu aplikacji
        app_logger.info("Uruchomiono aplikację Network File Manager.")

    def search_file_in_database(self, file_name):
        self.right_panel.set_search_query(file_name)

    def verify_file_integrity(self, source_path, dest_path):
        if not dest_path.exists():
            return False, "Plik docelowy nie istnieje w ścieżce archiwum."

        if source_path.stat().st_size != dest_path.stat().st_size:
            return False, "Niezgodność rozmiaru plików!"

        if calculate_sha256(source_path) != calculate_sha256(dest_path):
            return False, "Suma kontrolna SHA-256 jest niezgodna!"

        return True, "Plik zweryfikowany pomyślnie."

    def archive_file_to_database(self, file_path, machine_name):
        self.left_panel.status_label.configure(
            text=f"⏳ Trwa archiwizacja pliku: {file_path.name}...",
            text_color="orange",
        )

        threading.Thread(
            target=self._async_archive_process,
            args=(file_path, machine_name),
            daemon=True,
        ).start()

    def _async_archive_process(self, file_path, machine_name):
        try:
            mtime = os.path.getmtime(file_path)
            file_date = datetime.fromtimestamp(mtime)
            date_str = file_date.strftime("%d_%m_%y %H_%M")

            folder_name = f"WYKONANIE {machine_name} {date_str}"
            destination_dir = self.right_panel.current_path / folder_name

            destination_dir.mkdir(parents=True, exist_ok=True)
            destination_file_path = destination_dir / file_path.name

            shutil.copy2(file_path, destination_file_path)

            is_valid, msg = self.verify_file_integrity(
                file_path, destination_file_path
            )

            if not is_valid:
                raise Exception(f"Błąd weryfikacji pliku: {msg}")

            self.right_panel.db.add_single_path(destination_dir, is_dir=True)
            self.right_panel.db.add_single_path(
                destination_file_path, is_dir=False
            )

            os.remove(file_path)

            # LOGOWANIE SUKCESU ARCHIWIZACJI
            app_logger.info(
                f"ZARCHIWIZOWANO: Plik '{file_path.name}' z maszyny '{machine_name}' do katalogu '{destination_dir.name}'."
            )

            self.after(
                0, lambda: self._on_archive_success(file_path, destination_dir)
            )

        except Exception as e:
            error_msg = str(e)
            # LOGOWANIE BŁĘDU ARCHIWIZACJI
            app_logger.error(
                f"BŁĄD ARCHIWIZACJI: Nie udało się zarchiwizować '{file_path}'. Powód: {error_msg}"
            )
            self.after(0, lambda: self._on_archive_error(error_msg))

    def _on_archive_success(self, file_path, destination_dir):
        self.right_panel.refresh_view()
        self.left_panel.refresh_view()
        self.left_panel._clear_selection()
        self.left_panel.status_label.configure(
            text=f"🟢 Przeniesiono i zweryfikowano: {file_path.name}",
            text_color="#55FF55",
        )

    def _on_archive_error(self, error_message):
        self.left_panel.status_label.configure(
            text="🔴 Błąd archiwizacji!", text_color="#FF5555"
        )
        messagebox.showerror(
            "Błąd archiwizacji",
            f"Nie udało się przenieść/zarchiwizować pliku:\n{error_message}",
        )

    def delete_item_from_machine(self, item_path, item_type):
        """Obsługuje bezpieczne usuwanie plików i katalogów z maszyny z potwierdzeniem."""
        try:
            if item_type == "file":
                confirm = messagebox.askyesno(
                    "Potwierdzenie usunięcia pliku",
                    f"Czy na pewno chcesz bezpowrotnie usunąć plik:\n\n{item_path.name}?",
                    icon="warning",
                )
                if confirm:
                    os.remove(item_path)
                    # LOGOWANIE USUNIĘCIA PLIKU
                    app_logger.info(f"USUNIĘTO PLIK: '{item_path}'")
                    self._post_delete_cleanup(f"Usunięto plik: {item_path.name}")

            elif item_type == "dir":
                contents = list(item_path.iterdir())
                is_empty = len(contents) == 0

                if is_empty:
                    confirm = messagebox.askyesno(
                        "Potwierdzenie usunięcia pustego folderu",
                        f"Katalog '{item_path.name}' jest pusty.\nCzy chcesz go usunąć?",
                        icon="question",
                    )
                    if confirm:
                        item_path.rmdir()
                        # LOGOWANIE USUNIĘCIA PUSTEGO FOLDERU
                        app_logger.info(f"USUNIĘTO PUSTY FOLDER: '{item_path}'")
                        self._post_delete_cleanup(f"Usunięto pusty folder: {item_path.name}")
                else:
                    confirm = messagebox.askyesno(
                        "Ostrzeżenie: Folder nie jest pusty!",
                        f"Katalog '{item_path.name}' zawiera pliki lub podfoldery ({len(contents)} elem.).\n\n"
                        f"Czy na pewno chcesz usunąć ten folder wraz z CAŁĄ ZAWARTOŚCIĄ?",
                        icon="warning",
                    )
                    if confirm:
                        shutil.rmtree(item_path)
                        # LOGOWANIE USUNIĘCIA FOLDERU Z ZAWARTOŚCIĄ
                        app_logger.info(f"USUNIĘTO FOLDER Z ZAWARTOŚCIĄ ({len(contents)} elem.): '{item_path}'")
                        self._post_delete_cleanup(f"Usunięto folder wraz z zawartością: {item_path.name}")

        except Exception as e:
            # LOGOWANIE BŁĘDU USUWANIA
            app_logger.error(f"BŁĄD USUWANIA: Nie udało się usunąć '{item_path}'. Powód: {str(e)}")
            messagebox.showerror(
                "Błąd usuwania",
                f"Nie udało się usunąć wskazanego elementu:\n{str(e)}",
            )

    def _post_delete_cleanup(self, status_msg):
        self.left_panel.refresh_view()
        self.left_panel._clear_selection()
        self.left_panel.status_label.configure(
            text=f"🗑️ {status_msg}", text_color="#FF5555"
        )


if __name__ == "__main__":
    app = NetworkFileManager()
    app.mainloop()