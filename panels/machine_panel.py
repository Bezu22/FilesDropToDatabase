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
        on_delete_callback=None,
        on_auto_archive_callback=None,
        on_sim_archive_callback=None,
        on_clean_empty_callback=None,  # Nowy callback do czyszczenia pustych folderów
    ):
        super().__init__(parent, title="LEWY PANEL")
        self.machines = machines_dict
        self.selected_machine = list(self.machines.keys())[0]

        # Przypisanie callbacków
        self.on_search_in_db_callback = on_search_in_db_callback
        self.on_archive_callback = on_archive_callback
        self.on_delete_callback = on_delete_callback
        self.on_auto_archive_callback = on_auto_archive_callback
        self.on_sim_archive_callback = on_sim_archive_callback
        self.on_clean_empty_callback = on_clean_empty_callback

        self.root_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_path

        self.scanner = MachineScanner()

        self._setup_machine_ui()
        self.refresh_view()

    def _setup_machine_ui(self):
        """Konfiguracja układu przycisków w nagłówku oraz w dolnym pasku akcji."""
        # 1. Przełączniki maszyn w górnym nagłówku
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

        # 2. Reorganizacja dolnej ramki akcji (2 wiersze, 3 kolumny)
        self.actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # --- RZĄD 1: Akcje manualne ---
        self.btn_act1.configure(
            text="Znajdź", state="disabled", command=self._find_in_database
        )
        self.btn_act1.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        self.btn_act2.configure(
            text="Archiwizuj", state="disabled", command=self._archive_file
        )
        self.btn_act2.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        self.btn_act3.configure(
            text="Usuń", state="disabled", command=self._delete_item
        )
        self.btn_act3.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        # --- RZĄD 2: Akcje automatyczne ---
        self.btn_sim_archive = ctk.CTkButton(
            self.actions_frame,
            text="🧪 Test Auto",
            fg_color="#1E90FF",
            hover_color="#1C86EE",
            command=self._trigger_sim_archive,
        )
        self.btn_sim_archive.grid(row=1, column=0, padx=2, pady=2, sticky="ew")

        self.btn_auto_archive = ctk.CTkButton(
            self.actions_frame,
            text="⚡ Auto-Archiwizacja",
            fg_color="#DA70D6",
            hover_color="#BA55D3",
            command=self._trigger_auto_archive,
        )
        self.btn_auto_archive.grid(row=1, column=1, padx=2, pady=2, sticky="ew")

        self.btn_clean_empty = ctk.CTkButton(
            self.actions_frame,
            text="🧹 Czyszczenie Pustych",
            fg_color="#2E8B57",
            hover_color="#3CB371",
            command=self._trigger_clean_empty,
        )
        self.btn_clean_empty.grid(row=1, column=2, padx=2, pady=2, sticky="ew")

    def _trigger_auto_archive(self):
        if self.on_auto_archive_callback:
            self.on_auto_archive_callback()

    def _trigger_sim_archive(self):
        if self.on_sim_archive_callback:
            self.on_sim_archive_callback()

    def _trigger_clean_empty(self):
        if self.on_clean_empty_callback:
            self.on_clean_empty_callback()

    def _select_machine(self, machine_name):
        self.selected_machine = machine_name
        self.root_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_path
        self.search_entry.delete(0, "end")
        self.refresh_view()

    def _on_single_click(self, path, item_type, button_widget):
        super()._on_single_click(path, item_type, button_widget)
        self.btn_act3.configure(state="normal")

        if item_type == "file" and path.suffix.lower() == ".tom":
            self.btn_act1.configure(state="normal")
            self.btn_act2.configure(state="normal")
        else:
            self.btn_act1.configure(state="disabled")
            self.btn_act2.configure(state="disabled")

    def _clear_selection(self):
        super()._clear_selection()
        if hasattr(self, "btn_act1"):
            self.btn_act1.configure(state="disabled")
            self.btn_act2.configure(state="disabled")
            self.btn_act3.configure(state="disabled")

    def _find_in_database(self):
        if self.selected_item_path and self.selected_item_type == "file":
            if self.on_search_in_db_callback:
                self.on_search_in_db_callback(self.selected_item_path.name)

    def _archive_file(self):
        if self.selected_item_path and self.selected_item_type == "file":
            if self.on_archive_callback:
                self.on_archive_callback(
                    file_path=self.selected_item_path,
                    machine_name=self.selected_machine,
                )

    def _delete_item(self):
        if self.selected_item_path and self.on_delete_callback:
            self.on_delete_callback(
                item_path=self.selected_item_path,
                item_type=self.selected_item_type,
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