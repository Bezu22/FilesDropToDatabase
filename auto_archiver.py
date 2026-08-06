from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
import shutil
import tkinter.messagebox as messagebox

from logger import app_logger


def calculate_sha256(file_path: Path) -> str:
    """Oblicza sumę kontrolną SHA-256 pliku w porcjach 4 KB."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class AutoArchiver:
    """Moduł odpowiedzialny za bezpieczną automatyczną archiwizację plików z maszyn."""

    def __init__(self, app_instance):
        self.app = app_instance

    def verify_file_integrity(self, source_path, dest_path):
        """Sprawdza rozmiar i sumę kontrolną SHA-256 obu plików."""
        source_p = Path(source_path)
        dest_p = Path(dest_path)

        if not dest_p.exists():
            return False, "Plik docelowy nie istnieje w ścieżce archiwum."

        if source_p.stat().st_size != dest_p.stat().st_size:
            return False, "Niezgodność rozmiaru plików!"

        if calculate_sha256(source_p) != calculate_sha256(dest_p):
            return False, "Suma kontrolna SHA-256 jest niezgodna!"

        return True, "Plik zweryfikowany pomyślnie."

    def is_file_from_today_or_yesterday(self, file_path: Path) -> bool:
        """Sprawdza, czy plik był zmodyfikowany dzisiaj lub wczoraj."""
        mtime = os.path.getmtime(file_path)
        file_date = datetime.fromtimestamp(mtime).date()
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        return file_date in (today, yesterday)

    def run_auto_archive(self):
        """Główna funkcja wykonująca automatyczną archiwizację."""
        current_path = Path(self.app.left_panel.current_path)
        machine_name = getattr(
            self.app.left_panel, "selected_machine", "MASZYNA"
        )
        root_db_path = Path(self.app.right_panel.root_path).resolve()

        tom_files = list(current_path.rglob("*.tom"))

        if not tom_files:
            messagebox.showinfo(
                "Auto-Archiwizacja",
                "Nie znaleziono żadnych plików .tom w tym katalogu.",
            )
            return

        confirm = messagebox.askyesno(
            "Auto-Archiwizacja",
            f"Znaleziono {len(tom_files)} plików .tom.\n\nCzy chcesz uruchomić bezpieczną automatyczną archiwizację?",
        )
        if not confirm:
            return

        archived_count = 0
        skipped_count = 0

        for file_path in tom_files:
            file_name = file_path.name

            # 🟢 1. SPRAWDZENIE DATY: Pomijamy świeże pliki (dzisiaj / wczoraj) cicho bez logowania
            if self.is_file_from_today_or_yesterday(file_path):
                skipped_count += 1
                continue

            # Wyszukiwanie w bazie SQLite
            results = self.app.right_panel.db.search_orders(file_name.lower())

            matching_folders = set()
            for item in results:
                raw_path = Path(item[2])
                full_path = (
                    (root_db_path / raw_path).resolve()
                    if not raw_path.is_absolute()
                    else raw_path.resolve()
                )
                folder = full_path if item[0] == "dir" else full_path.parent
                matching_folders.add(folder)

            if len(matching_folders) == 1:
                base_target_dir = list(matching_folders)[0]
                try:
                    mtime = os.path.getmtime(file_path)
                    file_date = datetime.fromtimestamp(mtime)
                    date_str = file_date.strftime("%d_%m_%y %H_%M")

                    execution_folder_name = (
                        f"WYKONANIE {machine_name} {date_str}"
                    )
                    final_target_dir = base_target_dir / execution_folder_name
                    destination_file_path = final_target_dir / file_name

                    # Pomijamy bez logowania, jeśli plik w archiwum już istnieje
                    if destination_file_path.exists():
                        skipped_count += 1
                        continue

                    final_target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, destination_file_path)

                    is_valid, msg = self.verify_file_integrity(
                        file_path, destination_file_path
                    )

                    if is_valid:
                        # 🟢 2. OBSŁUGA ZABLOKOWANEGO PLIKU
                        try:
                            os.remove(file_path)
                        except PermissionError:
                            app_logger.error(
                                f"BŁĄD: Plik '{file_name}' jest otwarty w innym programie na maszynie. Wycofywanie archiwizacji!"
                            )
                            if destination_file_path.exists():
                                os.remove(destination_file_path)
                            skipped_count += 1
                            continue

                        self.app.right_panel.db.add_single_path(
                            final_target_dir, is_dir=True
                        )
                        self.app.right_panel.db.add_single_path(
                            destination_file_path, is_dir=False
                        )

                        # 🟢 3. LOGUJEMY TYLKO UDANĄ ARCHIWIZACJĘ
                        app_logger.info(
                            f"AUTO-ARCHIWIZACJA SUKCES: '{file_name}' -> '{final_target_dir.name}'"
                        )
                        archived_count += 1

                        # Otwieranie folderu zostało usunięte
                    else:
                        app_logger.error(
                            f"AUTO-ARCHIWIZACJA BŁĄD WERYFIKACJI: '{file_name}'. Powód: {msg}"
                        )
                        skipped_count += 1

                except Exception as e:
                    app_logger.error(
                        f"AUTO-ARCHIWIZACJA BŁĄD: '{file_name}'. Powód: {e}"
                    )
                    skipped_count += 1
            else:
                skipped_count += 1

        self.app.right_panel.refresh_view()
        self.app.left_panel.refresh_view()

        messagebox.showinfo(
            "Raport Auto-Archiwizacji",
            f"Zakończono proces!\n\n"
            f"🟢 Zarchiwizowano pomyślnie: {archived_count}\n"
            f"⚠️ Pominięto: {skipped_count}",
        )

    def run_simulation(self):
        """Symulacja automatycznej archiwizacji (bez zmian na dysku)."""
        current_path = Path(self.app.left_panel.current_path)
        tom_files = list(current_path.rglob("*.tom"))

        if not tom_files:
            messagebox.showinfo(
                "Test Auto-Archiwizacji",
                "Nie znaleziono żadnych plików .tom w tym katalogu.",
            )
            return

        will_archive = []
        will_skip = []

        for file_path in tom_files:
            file_name = file_path.name
            if self.is_file_from_today_or_yesterday(file_path):
                will_skip.append(f"• {file_name} (Plik z dzisiaj/wczoraj)")
                continue

            results = self.app.right_panel.db.search_orders(file_name.lower())

            matching_folders = set()
            for item in results:
                item_path = Path(item[2])
                folder = item_path if item[0] == "dir" else item_path.parent
                matching_folders.add(folder)

            if len(matching_folders) == 1:
                target_dir = list(matching_folders)[0]
                will_archive.append(f"• {file_name} -> {target_dir.name}")
            else:
                reason = (
                    "Brak folderu w bazie"
                    if len(matching_folders) == 0
                    else f"Dwuznaczność ({len(matching_folders)} folderów)"
                )
                will_skip.append(f"• {file_name} ({reason})")

        report_text = (
            f"🧪 WYNIK SYMULACJI (Żaden plik nie został zmieniony):\n\n"
        )
        report_text += f"🟢 Zostałyby zarchiwizowane ({len(will_archive)}):\n"
        report_text += (
            "\n".join(will_archive[:10]) if will_archive else "  (Brak)"
        )
        if len(will_archive) > 10:
            report_text += f"\n  ...oraz {len(will_archive) - 10} więcej."

        report_text += f"\n\n⚠️ Zostałyby pominięte ({len(will_skip)}):\n"
        report_text += "\n".join(will_skip[:10]) if will_skip else "  (Brak)"
        if len(will_skip) > 10:
            report_text += f"\n  ...oraz {len(will_skip) - 10} więcej."

        messagebox.showinfo("Raport Symulacji", report_text)