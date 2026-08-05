import os
import re
import subprocess
import threading
from pathlib import Path
import customtkinter as ctk
from database import DatabaseManager


class DatabasePanel(ctk.CTkFrame):

    def __init__(self, parent, root_db_path):
        super().__init__(parent)
        self.root_db_path = Path(root_db_path)
        self.current_path = self.root_db_path

        self.db = DatabaseManager()
        self._search_timer = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # 1. Nagłówek i przyciski
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(
            row=0, column=0, padx=5, pady=(5, 0), sticky="ew"
        )

        self.label = ctk.CTkLabel(
            self.header_frame,
            text="BAZA GŁÓWNA",
            font=ctk.CTkFont(weight="bold"),
        )
        self.label.pack(side="left")

        self.btn_open_explorer = ctk.CTkButton(
            self.header_frame,
            text="📂 Explorer",
            width=100,
            command=self.open_in_explorer,
        )
        self.btn_open_explorer.pack(side="right", padx=2)

        self.btn_reindex = ctk.CTkButton(
            self.header_frame,
            text="⚡ Skanuj bazę",
            width=100,
            fg_color="#1f538d",
            command=self.reindex_database,
        )
        self.btn_reindex.pack(side="right", padx=2)

        # 2. Wyświetlanie aktualnej ścieżki
        self.path_label = ctk.CTkLabel(
            self,
            text=str(self.current_path),
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            anchor="w",
        )
        self.path_label.grid(row=1, column=0, padx=5, pady=(0, 2), sticky="ew")

        # 3. Pole wyszukiwania
        self.search_entry = ctk.CTkEntry(
            self, placeholder_text="Szukaj zlecenia lub pliku .tom w bazie..."
        )
        self.search_entry.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_key_pressed)

        # Status
        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.status_label.grid(row=3, column=0, padx=5, pady=(0, 2), sticky="w")

        # 4. Lista elementów
        self.items_list_frame = ctk.CTkScrollableFrame(self)
        self.items_list_frame.grid(
            row=5, column=0, padx=5, pady=5, sticky="nsew"
        )
        self.items_list_frame.grid_columnconfigure(0, weight=1)

        self.refresh_view()

    def _on_search_key_pressed(self, event):
        """Czeka 300ms od ostatniego klawisza przed wyszukiwaniem."""
        if self._search_timer is not None:
            self.after_cancel(self._search_timer)

        self._search_timer = self.after(300, self.refresh_view)

    def open_in_explorer(self):
        """Otwiera obecną ścieżkę w Eksploratorze Windows."""
        path_str = str(self.current_path)
        if os.path.exists(path_str):
            subprocess.Popen(f'explorer "{path_str}"')
        else:
            self.status_label.configure(
                text="⚠️ Ścieżka nie istnieje w systemie!", text_color="#FF9900"
            )

    def reindex_database(self):
        """Skanuje dysk w tle i buduje bazę danych SQLite."""
        self.status_label.configure(
            text="⏳ Indeksowanie struktury w tle...", text_color="yellow"
        )
        self.btn_reindex.configure(state="disabled")

        def worker():
            success, msg = self.db.index_directory(self.root_db_path)

            def update_ui():
                self.btn_reindex.configure(state="normal")
                if success:
                    self.status_label.configure(
                        text=f"🟢 {msg}", text_color="#55FF55"
                    )
                else:
                    self.status_label.configure(
                        text=f"🔴 {msg}", text_color="#FF5555"
                    )
                self.refresh_view()

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def natural_sort_key(s):
        """Sortowanie naturalne (np. 1, 2, 10 zamiast 1, 10, 2)."""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(s))
        ]

    def refresh_view(self):
        """Odświeża widok na podstawie bazy danych SQLite."""
        query = self.search_entry.get().lower().strip()
        self.path_label.configure(text=str(self.current_path))

        if query:
            raw_items = self.db.search_orders(query, limit=100)
        else:
            raw_items = self.db.get_children(self.current_path)

        # Sortowanie według nazwy (element index 1 to nazwa)
        sorted_items = sorted(
            raw_items, key=lambda x: self.natural_sort_key(x[1])
        )
        self._draw_items(sorted_items, is_search=bool(query))

    def _draw_items(self, items, is_search=False):
        """Renderuje przyciski folderów i plików .tom."""
        for widget in self.items_list_frame.winfo_children():
            widget.destroy()

        # Przycisk ".." do powrotu wyżej
        if not is_search and self.current_path != self.root_db_path:
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
                text="[Brak pasujących elementów]",
                text_color="gray",
            )
            lbl.pack(anchor="w", padx=10, pady=10)
            return

        for item_type, item_name, path_str, tom_files_str in items:
            full_path = Path(path_str)

            if item_type == "dir":
                icon = "📁"
                color = "gray90"
                display_text = (
                    f"{icon} {item_name} ({tom_files_str})"
                    if tom_files_str
                    else f"{icon} {item_name}"
                )
                cmd = lambda p=full_path: self._on_folder_click(p)
            else:
                icon = "📄"
                color = "#FFD700"  # Złoty kolor dla plików .tom
                display_text = f"{icon} {item_name}"
                cmd = lambda p=full_path: self._on_file_click(p)

            btn = ctk.CTkButton(
                self.items_list_frame,
                text=display_text,
                anchor="w",
                fg_color="transparent",
                text_color=color,
                hover_color="#2A2D2E",
                command=cmd,
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _go_up(self):
        """Cofanie do folderu nadrzędnego."""
        if self.current_path != self.root_db_path:
            self.current_path = self.current_path.parent
            self.refresh_view()

    def _on_folder_click(self, path):
        """Wejście do folderu."""
        self.search_entry.delete(0, "end")
        self.current_path = path
        self.refresh_view()

    def _on_file_click(self, path):
        """Obsługa kliknięcia pliku .tom."""
        print(f"Wybrano plik .tom: {path}")