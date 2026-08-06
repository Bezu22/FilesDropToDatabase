from datetime import datetime
import os
from pathlib import Path
import shutil
import threading
import tkinter.messagebox as messagebox
import customtkinter as ctk

from auto_archiver import AutoArchiver
from config import MACHINES, MAIN_DB_PATH
from logger import app_logger
from panels.bottom_panel import BottomPanel
from panels.database_panel import DatabasePanel
from panels.machine_panel import MachinePanel

ctk.set_appearance_mode("Dark")


class NetworkFileManager(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Network File Manager")
        self.geometry("1100x700")

        # Przechowuje ścieżkę OSTATNIO zaznaczonego pliku/folderu (z dowolnego panelu)
        self.last_selected_path = None

        # Moduł automatycznej archiwizacji
        self.auto_archiver = AutoArchiver(self)

        # Siatka okna głównego
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # 1. Prawy panel (Baza danych)
        self.right_panel = DatabasePanel(self, MAIN_DB_PATH)
        self.right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # 2. Lewy panel (Maszyny)
        self.left_panel = MachinePanel(
            self,
            MACHINES,
            on_search_in_db_callback=self.search_file_in_database,
            on_archive_callback=self.archive_file_to_database,
            on_delete_callback=self.delete_item_from_machine,
            on_auto_archive_callback=self.auto_archiver.run_auto_archive,
            on_sim_archive_callback=self.auto_archiver.run_simulation,
            on_clean_empty_callback=self.clean_empty_folders_in_current_directory,
        )
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # 3. Dolny panel (z podpięciem funkcji zmiany nazwy)
        self.bottom_panel = BottomPanel(
            self,
            on_rename_callback=self.rename_selected_item,
        )
        self.bottom_panel.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew"
        )

        app_logger.info("Uruchomiono aplikację Network File Manager.")

    def search_file_in_database(self, file_name):
        """Przekazuje nazwę pliku do pola wyszukiwania w prawym panelu."""
        self.right_panel.set_search_query(file_name)

    def rename_selected_item(self):
        """Zmiana nazwy ostatnio zaznaczonego pliku lub folderu."""
        if not self.last_selected_path:
            messagebox.showwarning(
                "Brak zaznaczenia",
                "Najpierw zaznacz plik lub folder, którego nazwę chcesz zmienić!",
            )
            return

        old_path = Path(self.last_selected_path)

        if not old_path.exists():
            messagebox.showerror(
                "Błąd", f"Wskazany element nie istnieje na dysku:\n{old_path}"
            )
            return

        # Okienko wprowadzania nowej nazwy
        dialog = ctk.CTkInputDialog(
            text=f"Wpisz nową nazwę dla:\n{old_path.name}", title="Zmiana nazwy"
        )
        new_name = dialog.get_input()

        # Jeśli anulowano lub pole jest puste
        if not new_name or new_name.strip() == "":
            return

        new_name = new_name.strip()
        new_path = old_path.parent / new_name

        if new_path.exists():
            messagebox.showerror(
                "Błąd",
                f"Element o nazwie '{new_name}' już istnieje w tej lokalizacji!",
            )
            return

        try:
            # Zmiana nazwy na dysku
            old_path.rename(new_path)

            # Aktualizacja ścieżki ostatniego zaznaczenia
            self.last_selected_path = str(new_path)

            # Logowanie i odświeżanie interfejsu
            app_logger.info(
                f"ZMIENIONO NAZWĘ: '{old_path.name}' -> '{new_name}'"
            )
            self.left_panel.refresh_view()
            self.right_panel.refresh_view()

            messagebox.showinfo(
                "Sukces", f"Pomyślnie zmieniono nazwę na:\n{new_name}"
            )

        except Exception as e:
            app_logger.error(
                f"BŁĄD ZMIANY NAZWY: '{old_path.name}'. Powód: {e}"
            )
            messagebox.showerror(
                "Błąd zmiany nazwy", f"Nie udało się zmienić nazwy:\n{e}"
            )

    def archive_file_to_database(self, file_path, machine_name):
        """Uruchamia proces manualnej archiwizacji w osobnym wątku."""
        file_path_obj = Path(file_path)
        self.left_panel.status_label.configure(
            text=f"⏳ Trwa archiwizacja pliku: {file_path_obj.name}...",
            text_color="orange",
        )

        threading.Thread(
            target=self._async_archive_process,
            args=(file_path_obj, machine_name),
            daemon=True,
        ).start()

    def _async_archive_process(self, file_path, machine_name):
        """Asynchroniczne wykonanie manualnego przeniesienia pliku."""
        try:
            mtime = os.path.getmtime(file_path)
            file_date = datetime.fromtimestamp(mtime)
            date_str = file_date.strftime("%d_%m_%y %H_%M")

            folder_name = f"WYKONANIE {machine_name} {date_str}"
            destination_dir = self.right_panel.current_path / folder_name

            destination_dir.mkdir(parents=True, exist_ok=True)
            destination_file_path = destination_dir / file_path.name

            shutil.copy2(file_path, destination_file_path)

            is_valid, msg = self.auto_archiver.verify_file_integrity(
                file_path, destination_file_path
            )

            if not is_valid:
                raise Exception(f"Błąd weryfikacji pliku: {msg}")

            self.right_panel.db.add_single_path(destination_dir, is_dir=True)
            self.right_panel.db.add_single_path(
                destination_file_path, is_dir=False
            )

            os.remove(file_path)

            app_logger.info(
                f"ZARCHIWIZOWANO: Plik '{file_path.name}' z maszyny '{machine_name}' do katalogu '{destination_dir.name}'."
            )

            self.after(
                0, lambda: self._on_archive_success(file_path, destination_dir)
            )

        except Exception as e:
            error_msg = str(e)
            app_logger.error(
                f"BŁĄD ARCHIWIZACJI: Nie udało się zarchiwizować '{file_path}'. Powód: {error_msg}"
            )
            self.after(0, lambda: self._on_archive_error(error_msg))

    def _on_archive_success(self, file_path, destination_dir):
        """Obsługa sukcesu manualnej archiwizacji w wątku głównym GUI."""
        self.right_panel.refresh_view()
        self.left_panel.refresh_view()
        self.left_panel._clear_selection()
        self.left_panel.status_label.configure(
            text=f"🟢 Przeniesiono i zweryfikowano: {file_path.name}",
            text_color="#55FF55",
        )

    def _on_archive_error(self, error_message):
        """Obsługa błędu archiwizacji w wątku głównym GUI."""
        self.left_panel.status_label.configure(
            text="🔴 Błąd archiwizacji!", text_color="#FF5555"
        )
        messagebox.showerror(
            "Błąd archiwizacji",
            f"Nie udało się przenieść/zarchiwizować pliku:\n{error_message}",
        )

    def delete_item_from_machine(self, item_path, item_type):
        """Usuwa wybrany plik lub folder z maszyny po potwierdzeniu."""
        item_path_obj = Path(item_path)
        try:
            if item_type == "file":
                confirm = messagebox.askyesno(
                    "Potwierdzenie usunięcia pliku",
                    f"Czy na pewno chcesz bezpowrotnie usunąć plik:\n\n{item_path_obj.name}?",
                    icon="warning",
                )
                if confirm:
                    os.remove(item_path_obj)
                    app_logger.info(f"USUNIĘTO PLIK: '{item_path_obj}'")
                    self._post_delete_cleanup(
                        f"Usunięto plik: {item_path_obj.name}"
                    )

            elif item_type == "dir":
                contents = list(item_path_obj.iterdir())
                is_empty = len(contents) == 0

                if is_empty:
                    confirm = messagebox.askyesno(
                        "Potwierdzenie usunięcia pustego folderu",
                        f"Katalog '{item_path_obj.name}' jest pusty.\nCzy chcesz go usunąć?",
                        icon="question",
                    )
                    if confirm:
                        item_path_obj.rmdir()
                        app_logger.info(
                            f"USUNIĘTO PUSTY FOLDER: '{item_path_obj}'"
                        )
                        self._post_delete_cleanup(
                            f"Usunięto pusty folder: {item_path_obj.name}"
                        )
                else:
                    confirm = messagebox.askyesno(
                        "Ostrzeżenie: Folder nie jest pusty!",
                        f"Katalog '{item_path_obj.name}' zawiera pliki lub podfoldery ({len(contents)} elem.).\n\n"
                        f"Czy na pewno chcesz usunąć ten folder wraz z CAŁĄ ZAWARTOŚCIĄ?",
                        icon="warning",
                    )
                    if confirm:
                        shutil.rmtree(item_path_obj)
                        app_logger.info(
                            f"USUNIĘTO FOLDER Z ZAWARTOŚCIĄ ({len(contents)} elem.): '{item_path_obj}'"
                        )
                        self._post_delete_cleanup(
                            f"Usunięto folder wraz z zawartością: {item_path_obj.name}"
                        )

        except Exception as e:
            app_logger.error(
                f"BŁĄD USUWANIA: Nie udało się usunąć '{item_path_obj}'. Powód: {str(e)}"
            )
            messagebox.showerror(
                "Błąd usuwania",
                f"Nie udało się usunąć wskazanego elementu:\n{str(e)}",
            )

    def _post_delete_cleanup(self, status_msg):
        """Odświeża widok lewego panelu po usunięciu elementu."""
        self.left_panel.refresh_view()
        self.left_panel._clear_selection()
        self.left_panel.status_label.configure(
            text=f"🗑️ {status_msg}", text_color="#FF5555"
        )

    def clean_empty_folders_in_current_directory(self):
        """Skanuje aktualny katalog i usuwa wszystkie puste podfoldery."""
        current_path = Path(self.left_panel.current_path)

        all_dirs = sorted(
            [p for p in current_path.rglob("*") if p.is_dir()],
            key=lambda p: len(p.parts),
            reverse=True,
        )

        empty_folders = []
        for folder in all_dirs:
            try:
                if not any(folder.iterdir()):
                    empty_folders.append(folder)
            except Exception:
                pass

        if not empty_folders:
            messagebox.showinfo(
                "Czyszczenie Pustych Folderów",
                "Nie znaleziono żadnych pustych folderów w tej lokalizacji.",
            )
            return

        folders_list_str = "\n".join(
            [f"• {f.name}" for f in empty_folders[:10]]
        )
        if len(empty_folders) > 10:
            folders_list_str += f"\n...oraz {len(empty_folders) - 10} więcej."

        confirm = messagebox.askyesno(
            "Potwierdzenie usunięcia",
            f"Znaleziono {len(empty_folders)} pustych folderów:\n\n{folders_list_str}\n\nCzy chcesz je usunąć?",
            icon="warning",
        )

        if not confirm:
            return

        deleted_count = 0
        for folder in empty_folders:
            try:
                folder.rmdir()
                deleted_count += 1
                app_logger.info(
                    f"USUNIĘTO PUSTY FOLDER (AUTOCLEAN): '{folder}'"
                )
            except Exception as e:
                app_logger.error(
                    f"BŁĄD CZYSZCZENIA FOLDERU: '{folder}'. Powód: {e}"
                )

        self.left_panel.refresh_view()

        messagebox.showinfo(
            "Sukces", f"🟢 Pomyślnie usunięto {deleted_count} pustych folderów."
        )


if __name__ == "__main__":
    app = NetworkFileManager()
    app.mainloop()