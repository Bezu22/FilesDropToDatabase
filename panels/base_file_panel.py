import re
from pathlib import Path
import customtkinter as ctk

from panels.click_handler import ClickHandler


class BaseFilePanel(ctk.CTkFrame):
    """Wspólna klasa bazowa interfejsu panelu plików z obsługą nawigacji i wyboru elementów."""

    def __init__(self, parent, title):
        super().__init__(parent)
        self.title = title

        # Ścieżki bazowe i bieżące
        self.root_path = None
        self.current_path = None

        # Zmienne śledzenia zaznaczenia
        self.selected_item_path = None
        self.selected_item_type = None
        self.selected_button = None

        # Zabezpieczenie przed przypadkowym kliknięciem przycisku [..] tuż po otwarciu folderu
        self._is_navigating = False

        # Moduł obsługi kliknięć
        self.click_handler = ClickHandler(self)

        # Inicjalizacja układu graficznego
        self._init_base_ui()

    def _init_base_ui(self):
        """Konfiguruje układ siatki (Grid) i tworzy podstawowe elementy interfejsu."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. Nagłówek
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(
            row=0, column=0, padx=5, pady=(5, 0), sticky="ew"
        )

        self.label = ctk.CTkLabel(
            self.header_frame, text=self.title, font=ctk.CTkFont(weight="bold")
        )
        self.label.pack(side="left")

        # 2. Etykieta ścieżki
        self.path_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            anchor="w",
        )
        self.path_label.grid(row=1, column=0, padx=5, pady=(0, 2), sticky="ew")

        # 3. Pole wyszukiwania
        self.search_entry = ctk.CTkEntry(
            self, placeholder_text="Szukaj w tym panelu..."
        )
        self.search_entry.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

        # Status
        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.status_label.grid(row=3, column=0, padx=5, pady=(0, 2), sticky="w")

        # 4. Lista elementów
        self.items_list_frame = ctk.CTkScrollableFrame(self)
        self.items_list_frame.grid(
            row=4, column=0, padx=5, pady=5, sticky="nsew"
        )
        self.items_list_frame.grid_columnconfigure(0, weight=1)

        # 5. Dolny pasek z przyciskami
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(
            row=5, column=0, padx=5, pady=(0, 5), sticky="ew"
        )
        self.actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_act1 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja 1",
            command=lambda: self._exec_action(1),
        )
        self.btn_act1.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        self.btn_act2 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja 2",
            command=lambda: self._exec_action(2),
        )
        self.btn_act2.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        self.btn_act3 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja 3",
            command=lambda: self._exec_action(3),
        )
        self.btn_act3.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

    @staticmethod
    def natural_sort_key(s):
        """Klucz sortowania naturalnego dla ciągów znaków (np. 'plik2' przed 'plik10')."""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(s))
        ]

    def _get_display_path(self, prefix_name):
        """Zwraca skróconą/względną ścieżkę do wyświetlenia w nagłówku."""
        try:
            if self.current_path and self.root_path:
                rel = self.current_path.relative_to(self.root_path)
                rel_str = str(rel).replace("\\", "/")
                return f"{prefix_name} / {rel_str}"
            return f"{prefix_name} / ."
        except Exception:
            return f"{prefix_name} / ."

    def _unlock_navigation(self):
        """Zdejmuje blokadę czasową po odczekaniu 250 milisekund."""
        self._is_navigating = False

    def _draw_items(self, items, is_search=False):
        """Rysuje przyciski folderów i plików w liście przewijanej oraz przewija widok na samą górę."""
        for widget in self.items_list_frame.winfo_children():
            widget.destroy()

        self._clear_selection()

        # Włączamy blokadę na krótki czas, aby uniknąć przypadkowego kliknięcia w nowe elementy
        self._is_navigating = True
        self.after(250, self._unlock_navigation)

        # Przycisk powrotu wyżej [..]
        if (
            not is_search
            and self.current_path
            and self.current_path != self.root_path
        ):
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
        else:
            for item_info in items:
                item_type = item_info[0]
                item_name = item_info[1]
                path_str = item_info[2]
                tom_files_str = item_info[3] if len(item_info) > 3 else ""

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
                    lambda event, p=full_path, t=item_type, b=btn: self.click_handler.handle_click(
                        p,
                        t,
                        b,
                        on_single=self._on_single_click,
                        on_double=self._on_double_click,
                    ),
                )
                btn.pack(fill="x", padx=2, pady=1)

        # AUTOMATYCZNE PRZEWIJANIE: Resetuje pozycję suwaka do samej góry (0.0)
        try:
            self.items_list_frame._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def _on_single_click(self, path, item_type, button_widget):
        """Obsługuje kliknięcie, zapisuje globalne zaznaczenie i aktualizuje odpowiednią kolumnę dolnego panelu."""
        if self.selected_button and self.selected_button.winfo_exists():
            self.selected_button.configure(fg_color="transparent")

        self.selected_item_path = path
        self.selected_item_type = item_type
        self.selected_button = button_widget
        self.selected_button.configure(fg_color="#1f538d")

        # Pobieramy korzeń aplikacji
        app = self.winfo_toplevel()

        # Bezpiecznie przypisujemy ścieżkę do głównej aplikacji
        setattr(app, "last_selected_path", path)

        # Bezpieczna aktualizacja właściwej kolumny dolnego panelu
        bottom_panel = getattr(app, "bottom_panel", None)

        if bottom_panel is not None:
            from panels.database_panel import DatabasePanel

            if isinstance(self, DatabasePanel):
                bottom_panel.update_right_info(path)
            else:
                bottom_panel.update_left_info(path)

    def _on_double_click(self, path, item_type):
        """Otwiera folder po podwójnym kliknięciu."""
        if item_type == "dir":
            self.search_entry.delete(0, "end")
            self.current_path = path
            self.refresh_view()

    def _clear_selection(self):
        """Resetuje aktualne zaznaczenie."""
        self.selected_item_path = None
        self.selected_item_type = None
        self.selected_button = None

    def _go_up(self):
        """Cofa się do folderu nadrzędnego (z blokadą czasową)."""
        if self._is_navigating:
            return

        if self.current_path and self.current_path != self.root_path:
            self.current_path = self.current_path.parent
            self.search_entry.delete(0, "end")
            self.refresh_view()

    def _exec_action(self, action_num):
        pass

    def refresh_view(self):
        pass