import os
import re
import threading
from pathlib import Path
import customtkinter as ctk


class MachinePanel(ctk.CTkFrame):

    def __init__(self, parent, machines_dict):
        super().__init__(parent)
        self.machines = machines_dict

        # Nazwa aktualnie wybranej maszyny (np. "Maszyna 1")
        self.selected_machine = list(self.machines.keys())[0]

        # Ścieżka bazowa dla wybranej maszyny z config.py
        self.root_machine_path = Path(self.machines[self.selected_machine])

        # Ścieżka, w której aktualnie znajduje się użytkownik
        self.current_path = self.root_machine_path

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. Przyciski wyboru maszyn na górze
        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        for name in self.machines.keys():
            btn = ctk.CTkButton(
                self.buttons_frame,
                text=name,
                width=80,
                command=lambda m=name: self._select_machine(m),
            )
            btn.pack(side="left", padx=2, pady=2)

        # 2. Wyświetlanie aktualnej ścieżki
        self.path_label = ctk.CTkLabel(
            self,
            text=str(self.current_path),
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            anchor="w",
        )
        self.path_label.grid(row=1, column=0, padx=5, pady=(0, 2), sticky="ew")

        # 3. Dynamiczne szukajka (filtrowanie po nazwie w bieżącym katalogu)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh())

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="Szukaj w bieżącym folderze...",
            textvariable=self.search_var,
        )
        self.search_entry.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        # Status połączenia
        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.status_label.grid(row=3, column=0, padx=5, pady=(0, 2), sticky="w")

        # 4. Lista elementów (ScrollableFrame z przyciskami zamiast Textboxa)
        self.items_list_frame = ctk.CTkScrollableFrame(self)
        self.items_list_frame.grid(
            row=4, column=0, padx=5, pady=5, sticky="nsew"
        )
        self.items_list_frame.grid_columnconfigure(0, weight=1)

        # Pierwsze załadowanie zawartości
        self.refresh()

    @staticmethod
    def natural_sort_key(s):
        """Sortowanie naturalne (np. 1, 2, 10 zamiast 1, 10, 2)."""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(s))
        ]

    def _select_machine(self, machine_name):
        """Zmiana wybranej maszyny i powrót do jej folderu bazowego."""
        self.selected_machine = machine_name
        self.root_machine_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_machine_path
        self.search_var.set("")  # Wyczyszczenie wyszukiwarki
        self.refresh()

    def refresh(self):
        """Uruchamia odczyt zawartości folderu w osobnym wątku."""
        query = self.search_var.get().lower().strip()
        self.path_label.configure(text=str(self.current_path))
        self.status_label.configure(
            text="⏳ Odczyt z katalogu...", text_color="gray"
        )

        def load():
            items = []
            err = None
            try:
                if not self.current_path.exists():
                    err = f"Brak dostępu do folderu maszyny {self.selected_machine}."
                else:
                    # Używamy szybkiego os.scandir do pobrania zawartości
                    with os.scandir(self.current_path) as entries:
                        for entry in entries:
                            name_lower = entry.name.lower()

                            # Sprawdzamy filtry wyszukiwania (jeśli wpisano tekst)
                            if query and query not in name_lower:
                                continue

                            # 1. Zbieramy foldery
                            if entry.is_dir():
                                items.append(("dir", entry.name, entry.path))

                            # 2. Zbieramy WYŁĄCZNIE pliki .tom (reszta plików jest ignorowana)
                            elif (
                                entry.is_file() and name_lower.endswith(".tom")
                            ):
                                items.append(("file", entry.name, entry.path))

                    # Sortowanie elementów po nazwie
                    items.sort(key=lambda x: self.natural_sort_key(x[1]))

            except Exception as e:
                err = str(e)

            # Przekazanie wyników do wątku głównego interfejsu
            self.after(0, lambda: self._apply_results(items, err))

        threading.Thread(target=load, daemon=True).start()

    def _apply_results(self, items, err):
        """Wyświetla foldery oraz pliki .tom na liście."""
        # Czyszczenie starych elementów z widoku
        for widget in self.items_list_frame.winfo_children():
            widget.destroy()

        if err:
            self.status_label.configure(
                text=f"🔴 {self.selected_machine}: BRAK DOSTĘPU",
                text_color="#FF5555",
            )
            lbl = ctk.CTkLabel(
                self.items_list_frame,
                text=f"⚠️ {err}",
                text_color="#FF5555",
            )
            lbl.pack(padx=5, pady=5)
            return

        self.status_label.configure(
            text=f"🟢 {self.selected_machine}: ONLINE", text_color="#55FF55"
        )

        # Przycisk ".." pozwalający cofnąć się do katalogu nadrzędnego
        # Zabezpieczenie: Pokazuje się tylko jeśli nie jesteśmy w folderze głównym maszyny
        if self.current_path != self.root_machine_path:
            btn_up = ctk.CTkButton(
                self.items_list_frame,
                text="📁 [..]",
                anchor="w",
                fg_color="transparent",
                text_color="#55FFFF",
                hover_color="#2A2D2E",
                command=self._go_up,
            )
            btn_up.pack(fill="x", padx=2, pady=1)

        if not items:
            lbl = ctk.CTkLabel(
                self.items_list_frame,
                text="[Brak podfolderów lub plików .tom]",
                text_color="gray",
            )
            lbl.pack(anchor="w", padx=10, pady=10)
            return

        # Wyświetlanie podfolderów i plików .tom
        for item_type, name, path_str in items:
            full_path = Path(path_str)

            if item_type == "dir":
                icon = "📁"
                color = "gray90"
                cmd = lambda p=full_path: self._on_folder_click(p)
            else:
                icon = "📄"
                color = "#FFD700"  # Złoty kolor dla plików .tom
                cmd = lambda p=full_path: self._on_file_click(p)

            btn = ctk.CTkButton(
                self.items_list_frame,
                text=f"{icon} {name}",
                anchor="w",
                fg_color="transparent",
                text_color=color,
                hover_color="#2A2D2E",
                command=cmd,
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _go_up(self):
        """Przejście do katalogu nadrzędnego."""
        self.current_path = self.current_path.parent
        self.search_var.set("")
        self.refresh()

    def _on_folder_click(self, path):
        """Wejście w głąb klikniętego katalogu."""
        self.current_path = path
        self.search_var.set("")
        self.refresh()

    def _on_file_click(self, path):
        """Akcja po kliknięciu w plik .tom na maszynie."""
        print(f"Wybrano plik .tom na maszynie: {path}")