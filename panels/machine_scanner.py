import os
from pathlib import Path
import re
import threading
from logger import app_logger  # Wykorzystujemy nasz logger do audytu


class MachineScanner:

    @staticmethod
    def natural_sort_key(s):
        """Sortuje nazwy w sposób naturalny dla człowieka (np. Plik2 przed Plik10)."""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(s))
        ]

    def load_directory_async(
        self, current_path, query, selected_machine, callback
    ):
        """Uruchamia proces skanowania katalogu w osobnym wątku tła."""
        def worker():
            items = []
            err = None
            try:
                # Konwertujemy ścieżkę na obiekt Path dla pewności
                target_path = Path(current_path)

                if not target_path.exists():
                    err = f"Brak dostępu do maszyny {selected_machine} lub ścieżka nie istnieje."
                    app_logger.error(f"SKANOWANIE: {err} Ścieżka: '{target_path}'")
                else:
                    with os.scandir(target_path) as entries:
                        for entry in entries:
                            name_lower = entry.name.lower()
                            
                            # Filtrowanie wyszukiwania (jeśli wpisano frazę)
                            if query and query.strip().lower() not in name_lower:
                                continue

                            # Rejestrujemy foldery
                            if entry.is_dir():
                                items.append(("dir", entry.name, entry.path))
                            # Rejestrujemy WSZYSTKIE pliki (bez blokowania innych rozszerzeń niż .tom)
                            elif entry.is_file():
                                items.append(("file", entry.name, entry.path))

                    # Sortowanie naturalne po nazwie elementu (indeks 1 w krotce)
                    items.sort(key=lambda x: self.natural_sort_key(x[1]))

            except PermissionError as pe:
                err = f"Brak uprawnień do otwarcia katalogu na maszynie {selected_machine}."
                app_logger.error(f"BRAK DOSTĘPU: Maszyna '{selected_machine}', Ścieżka: '{current_path}'. Błąd: {pe}")
            except Exception as e:
                err = str(e)
                app_logger.error(f"BŁĄD SKANOWANIA: Maszyna '{selected_machine}', Ścieżka: '{current_path}'. Błąd: {e}")

            # Przekazujemy wynik do interfejsu
            callback(items, err)

        threading.Thread(target=worker, daemon=True).start()