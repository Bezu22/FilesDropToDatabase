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
        self._click_timer = None

        self.selected_item_path = None
        self.selected_item_type = None
        self.selected_button = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # 1. Nagłówek
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

        # 2. Wyświetlanie aktualnej ścieżki (Skróconej)
        self.path_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            anchor="w",
        )
        self.path_label.grid(row=1, column=0, padx=5, pady=(0, 2), sticky="ew")

        # 3. Szukajka
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

        # 5. Przyciski akcji
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(
            row=6, column=0, padx=5, pady=(0, 5), sticky="ew"
        )
        self.actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_act1 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja B1",
            command=lambda: self._exec_action(1),
        )
        self.btn_act1.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        self.btn_act2 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja B2",
            command=lambda: self._exec_action(2),
        )
        self.btn_act2.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        self.btn_act3 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja B3",
            command=lambda: self._exec_action(3),
        )
        self.btn_act3.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        self.refresh_view()

    def _get_display_path(self):
        """Formatuje pełny adres bazy na przyjazny skrót: BAZA GŁÓWNA / podścieżka."""
        try:
            rel = self.current_path.relative_to(self.root_db_path)
            rel_str = str(rel).replace("\\", "/")
            return f"BAZA GŁÓWNA / {rel_str}"
        except ValueError:
            return "BAZA GŁÓWNA / ."

    def _on_search_key_pressed(self, event):
        if self._search_timer is not None:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(300, self.refresh_view)

    def open_in_explorer(self):
        path_str = str(self.current_path)
        if os.path.exists(path_str):
            subprocess.Popen(f'explorer "{path_str}"')

    def reindex_database(self):
        self.status_label.configure(
            text="⏳ Indeksowanie struktury w tle...", text_color="yellow"
        )
        self.btn_reindex.configure(state="disabled")

        def worker():
            success, msg = self.db.index_directory(self.root_db_path)

            def update_ui():
                self.btn_reindex.configure(state="normal")
                self.status_label.configure(
                    text=f"🟢 {msg}" if success else f"🔴 {msg}",
                    text_color="#55FF55" if success else "#FF5555",
                )
                self.refresh_view()

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def natural_sort_key(s):
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(s))
        ]

    def refresh_view(self):
        query = self.search_entry.get().lower().strip()

        # Wyświetlamy skróconą ścieżkę w etykiecie
        self.path_label.configure(text=self._get_display_path())

        if query:
            raw_items = self.db.search_orders(query, limit=100)
        else:
            raw_items = self.db.get_children(self.current_path)

        sorted_items = sorted(
            raw_items, key=lambda x: self.natural_sort_key(x[1])
        )
        self._draw_items(sorted_items, is_search=bool(query))

    def _draw_items(self, items, is_search=False):
        for widget in self.items_list_frame.winfo_children():
            widget.destroy()

        self._clear_selection()

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
            icon = "📁" if item_type == "dir" else "📄"
            color = "gray90" if item_type == "dir" else "#FFD700"

            display_text = (
                f"{icon} {item_name} ({tom_files_str})"
                if (item_type == "dir" and tom_files_str)
                else f"{icon} {item_name}"
            )

            btn = ctk.CTkButton(
                self.items_list_frame,
                text=display_text,
                anchor="w",
                fg_color="transparent",
                text_color=color,
                hover_color="#2A2D2E",
            )
            btn.bind(
                "<Button-1>",
                lambda event, p=full_path, t=item_type, b=btn: self._handle_click(
                    p, t, b
                ),
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _handle_click(self, path, item_type, button_widget):
        if self._click_timer is not None:
            self.after_cancel(self._click_timer)
            self._click_timer = None
            self._on_double_click(path, item_type)
        else:
            self._click_timer = self.after(
                250,
                lambda: self._on_single_click(path, item_type, button_widget),
            )

    def _on_single_click(self, path, item_type, button_widget):
        self._click_timer = None

        if self.selected_button and self.selected_button.winfo_exists():
            self.selected_button.configure(fg_color="transparent")

        self.selected_item_path = path
        self.selected_item_type = item_type
        self.selected_button = button_widget
        self.selected_button.configure(fg_color="#1f538d")

        print(
            f"[BAZA] Zaznaczono: {self.selected_item_type.upper()} ->"
            f" {self.selected_item_path}"
        )

    def _on_double_click(self, path, item_type):
        if item_type == "dir":
            self.search_entry.delete(0, "end")
            self.current_path = path
            self.refresh_view()

    def _clear_selection(self):
        self.selected_item_path = None
        self.selected_item_type = None
        self.selected_button = None

    def _go_up(self):
        if self.current_path != self.root_db_path:
            self.current_path = self.current_path.parent
            self.refresh_view()

    def _exec_action(self, action_num):
        if not self.selected_item_path:
            print(f"[BAZA] Akcja B{action_num}: Nic nie jest zaznaczone!")
        else:
            print(
                f"[BAZA] Akcja B{action_num} na zaznaczonym elemencie:"
                f" {self.selected_item_type} -> {self.selected_item_path}"
            )