import os
import re
import threading


class MachineScanner:

    @staticmethod
    def natural_sort_key(s):
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(s))
        ]

    def load_directory_async(
        self, current_path, query, selected_machine, callback
    ):
        def worker():
            items = []
            err = None
            try:
                if not current_path.exists():
                    err = f"Brak dostępu do maszyny {selected_machine}."
                else:
                    with os.scandir(current_path) as entries:
                        for entry in entries:
                            name_lower = entry.name.lower()
                            if query and query not in name_lower:
                                continue
                            if entry.is_dir():
                                items.append(("dir", entry.name, entry.path))
                            elif (
                                entry.is_file() and name_lower.endswith(".tom")
                            ):
                                items.append(("file", entry.name, entry.path))

                    items.sort(key=lambda x: self.natural_sort_key(x[1]))
            except Exception as e:
                err = str(e)

            callback(items, err)

        threading.Thread(target=worker, daemon=True).start()