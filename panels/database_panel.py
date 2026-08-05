import os
import subprocess
import threading
from pathlib import Path
import customtkinter as ctk

from database import DatabaseManager
from panels.base_file_panel import BaseFilePanel


class DatabasePanel(BaseFilePanel):
    """Panel prawy: Zarządza widokiem bazy głównej i szybkim wyszukiwaniem z SQLite."""

    def __init__(self, parent, root_db_path):
        super().__init__(parent, title="BAZA GŁÓWNA")

        self.root_path = Path(root_db_path)
        self.current_path = self.root_path

        # Menedżer SQLite
        self.db = DatabaseManager()
        self._search_timer = None

        # Budowa specyficznego interfejsu i odświeżenie widoku
        self._setup_db_ui()
        self.refresh_view()

    def _setup_db_ui(self):
        """Dodaje przyciski skanowania i otwierania w Eksploratorze do nagłówka."""
        self.btn_open_explorer = ctk.CTkButton(
            self.header_frame,
            text="📂 Explorer",
            width=90,
            command=self.open_in_explorer,
        )
        self.btn_open_explorer.pack(side="right", padx=2)

        self.btn_reindex = ctk.CTkButton(
            self.header_frame,
            text="⚡ Skanuj",
            width=80,
            fg_color="#1f538d",
            command=self.reindex_database,
        )
        self.btn_reindex.pack(side="right", padx=2)

        # Reagujemy na pisanie w polu wyszukiwania
        self.search_entry.bind("<KeyRelease>", self._on_search_key_pressed)

        # Dostosowanie napisów na dolnych przyciskach akcji
        self.btn_act1.configure(text="Akcja B1")
        self.btn_act2.configure(text="Akcja B2")
        self.btn_act3.configure(text="Akcja B3")

    def set_search_query(self, query_text):
        """Wpisuje podany tekst do pola wyszukiwarki i odświeża listę wyników."""
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, query_text)
        self.refresh_view()

    def _on_search_key_pressed(self, event):
        """Czeka 300ms po wpisaniu znaku przed przeszukaniem bazy."""
        if self._search_timer is not None:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(300, self.refresh_view)

    def open_in_explorer(self):
        """Otwiera obecnie przeglądany folder w Eksploratorze Windows."""
        path_str = str(self.current_path)
        if os.path.exists(path_str):
            subprocess.Popen(f'explorer "{path_str}"')

    def reindex_database(self):
        """Przeszukuje dysk i buduje na nowo plik bazy danych SQLite w tle."""
        self.status_label.configure(
            text="⏳ Indeksowanie struktury w tle...", text_color="yellow"
        )
        self.btn_reindex.configure(state="disabled")

        def worker():
            success, msg = self.db.index_directory(self.root_path)

            def update_ui():
                self.btn_reindex.configure(state="normal")
                self.status_label.configure(
                    text=f"🟢 {msg}" if success else f"🔴 {msg}",
                    text_color="#55FF55" if success else "#FF5555",
                )
                self.refresh_view()

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def refresh_view(self):
        """
        Pobiera dane z bazy SQLite i oczyszcza je ze zbędnych ciągów znaków:
        - Jeśli pole wyszukiwania zawiera tekst -> wyświetla wyniki wyszukiwania globalnego.
        - Jeśli pole jest puste -> wyświetla zawartość aktualnego folderu (self.current_path).
        """
        query = self.search_entry.get().lower().strip()
        self.path_label.configure(text=self._get_display_path("BAZA GŁÓWNA"))

        if query:
            # Szukanie pasujących folderów/plików w całej bazie danych
            raw_items = self.db.search_orders(query, limit=100)
        else:
            # Pobranie dzieci (zawartości) dla wybranego folderu self.current_path
            raw_items = self.db.get_children(self.current_path)

        # Oczyszczanie rekordu z dodatkowych informacji SQL
        # Zapewnia czystą nazwę bez dopisków w nawiasach
        cleaned_items = []
        for item in raw_items:
            item_type = item[0]
            item_name = item[1]
            path_str = item[2]
            cleaned_items.append((item_type, item_name, path_str, ""))

        # Sortowanie naturalne według czystej nazwy
        sorted_items = sorted(
            cleaned_items, key=lambda x: self.natural_sort_key(x[1])
        )

        # Rysowanie wyczyszczonej listy elementów
        self._draw_items(sorted_items, is_search=bool(query))