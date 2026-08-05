from pathlib import Path
import customtkinter as ctk

from panels.base_file_panel import BaseFilePanel
from panels.machine_scanner import MachineScanner


class MachinePanel(BaseFilePanel):

    def __init__(
        self,
        parent,
        machines_dict,
        on_search_in_db_callback=None,
        on_archive_callback=None,
    ):
        super().__init__(parent, title="LEWY PANEL")
        self.machines = machines_dict
        self.selected_machine = list(self.machines.keys())[0]

        # Callbacks do komunikacji z głównym oknem
        self.on_search_in_db_callback = on_search_in_db_callback
        self.on_archive_callback = on_archive_callback

        self.root_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_path

        self.scanner = MachineScanner()

        self._setup_machine_ui()
        self.refresh_view()

    def _setup_machine_ui(self):
        """Konfiguracja specyficznego UI lewego panelu."""
        self.buttons_frame = ctk.CTkFrame(self.header_frame)
        self.buttons_frame.pack(side="right", padx=2)

        for name in self.machines.keys():
            btn = ctk.CTkButton(
                self.buttons_frame,
                text=name,
                width=80,
                command=lambda m=name: self._select_machine(m),
            )
            btn.pack(side="left", padx=2, pady=2)

        # Przycisk 1: "Znajdź"
        self.btn_act1.configure(
            text="Znajdź",
            state="disabled",
            command=self._find_in_database,
        )

        # Przycisk 2: "Archiwizuj"
        self.btn_act2.configure(
            text="Archiwizuj",
            state="disabled",
            command=self._archive_file,
        )

        self.btn_act3.configure(text="Akcja M3")

    def _select_machine(self, machine_name):
        self.selected_machine = machine_name
        self.root_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_path
        self.search_entry.delete(0, "end")
        self.refresh_view()

    def _on_single_click(self, path, item_type, button_widget):
        """Sterowanie aktywacją przycisków w zależności od wybranego pliku."""
        super()._on_single_click(path, item_type, button_widget)

        # Aktywujemy przyciski tylko dla plików z rozszerzeniem .tom
        if item_type == "file" and path.suffix.lower() == ".tom":
            self.btn_act1.configure(state="normal")
            self.btn_act2.configure(state="normal")
        else:
            self.btn_act1.configure(state="disabled")
            self.btn_act2.configure(state="disabled")

    def _clear_selection(self):
        """Po czyszczeniu zaznaczenia blokujemy przyciski."""
        super()._clear_selection()
        if hasattr(self, "btn_act1"):
            self.btn_act1.configure(state="disabled")
            self.btn_act2.configure(state="disabled")

    def _find_in_database(self):
        if self.selected_item_path and self.selected_item_type == "file":
            file_name = self.selected_item_path.name
            if self.on_search_in_db_callback:
                self.on_search_in_db_callback(file_name)

    def _archive_file(self):
        """Wywołuje operację archiwizacji za pośrednictwem callbacku."""
        if self.selected_item_path and self.selected_item_type == "file":
            if self.on_archive_callback:
                self.on_archive_callback(
                    file_path=self.selected_item_path,
                    machine_name=self.selected_machine,
                )

    def refresh_view(self):
        display_path = self._get_display_path(self.selected_machine)
        self.path_label.configure(text=display_path)
        self.status_label.configure(
            text="⏳ Odczyt z katalogu...", text_color="gray"
        )

        query = self.search_entry.get().lower().strip()

        def on_loaded(items, err):
            if err:
                self.status_label.configure(
                    text=f"🔴 {self.selected_machine}: BRAK DOSTĘPU",
                    text_color="#FF5555",
                )
            else:
                self.status_label.configure(
                    text=f"🟢 {self.selected_machine}: ONLINE",
                    text_color="#55FF55",
                )
            self._draw_items(items, is_search=bool(query))

        self.scanner.load_directory_async(
            self.current_path,
            query,
            self.selected_machine,
            callback=lambda items, err: self.after(
                0, lambda: on_loaded(items, err)
            ),
        )