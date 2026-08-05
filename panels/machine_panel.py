from pathlib import Path
import customtkinter as ctk

from panels.base_file_panel import BaseFilePanel
from panels.machine_scanner import MachineScanner


class MachinePanel(BaseFilePanel):
    """Panel lewy: Zarządza widokiem folderów i plików .tom wybranych maszyn."""

    def __init__(self, parent, machines_dict):
        # Tytuł 'LEWY PANEL' przekazujemy do klasy bazowej BaseFilePanel
        super().__init__(parent, title="LEWY PANEL")

        self.machines = machines_dict
        self.selected_machine = list(self.machines.keys())[0]

        # Ustawiamy ścieżki w zmiennych dziedziczonych z BaseFilePanel
        self.root_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_path

        # Inicjalizacja skanera plików
        self.scanner = MachineScanner()

        # Budowa specyficznego interfejsu i odświeżenie widoku
        self._setup_machine_ui()
        self.refresh_view()

    def _setup_machine_ui(self):
        """Dodaje przyciski wyboru maszyn do góry panela oraz ustawia opisy akcji."""
        self.buttons_frame = ctk.CTkFrame(self.header_frame)
        self.buttons_frame.pack(side="right", padx=2)

        # Tworzenie przycisków dla każdej maszyny zdefiniowanej w config.py
        for name in self.machines.keys():
            btn = ctk.CTkButton(
                self.buttons_frame,
                text=name,
                width=80,
                command=lambda m=name: self._select_machine(m),
            )
            btn.pack(side="left", padx=2, pady=2)

        # Dostosowanie tekstów przycisków akcji na dole
        self.btn_act1.configure(text="Akcja M1")
        self.btn_act2.configure(text="Akcja M2")
        self.btn_act3.configure(text="Akcja M3")

    def _select_machine(self, machine_name):
        """Zmienia wybraną maszynę i resetuje pozycję na folder główny."""
        self.selected_machine = machine_name
        self.root_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_path
        self.search_entry.delete(0, "end")
        self.refresh_view()

    def refresh_view(self):
        """Metoda nadpisana z BaseFilePanel: Ładuje zawartość folderu z maszyny."""
        display_path = self._get_display_path(self.selected_machine)
        self.path_label.configure(text=display_path)
        self.status_label.configure(
            text="⏳ Odczyt z katalogu...", text_color="gray"
        )

        query = self.search_entry.get().lower().strip()

        # Funkcja wywoływana po zakończeniu skanowania w tle
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
            # Używamy metody _draw_items z klasy bazowej
            self._draw_items(items, is_search=bool(query))

        # Asynchroniczne załadowanie katalogu
        self.scanner.load_directory_async(
            self.current_path,
            query,
            self.selected_machine,
            callback=lambda items, err: self.after(
                0, lambda: on_loaded(items, err)
            ),
        )