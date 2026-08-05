import os
import re
import threading
from pathlib import Path
import customtkinter as ctk


class MachinePanel(ctk.CTkFrame):

    def __init__(self, parent, machines_dict):
        super().__init__(parent)
        self.machines = machines_dict
        self.selected_machine = list(self.machines.keys())[0]
        self.root_machine_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_machine_path

        # Śledzenie zaznaczenia
        self.selected_item_path = None
        self.selected_item_type = None
        self.selected_button = None

        self._click_timer = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. Przyciski wyboru maszyn
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

        # 2. Wyświetlanie aktualnej ścieżki (Skróconej)
        self.path_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            anchor="w",
        )
        self.path_label.grid(row=1, column=0, padx=5, pady=(0, 2), sticky="ew")

        # 3. Wyszukiwarka
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh())

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="Szukaj w maszynie...",
            textvariable=self.search_var,
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

        # 5. Przyciski akcji
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(
            row=5, column=0, padx=5, pady=(0, 5), sticky="ew"
        )
        self.actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_act1 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja M1",
            command=lambda: self._exec_action(1),
        )
        self.btn_act1.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        self.btn_act2 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja M2",
            command=lambda: self._exec_action(2),
        )
        self.btn_act2.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

        self.btn_act3 = ctk.CTkButton(
            self.actions_frame,
            text="Akcja M3",
            command=lambda: self._exec_action(3),
        )
        self.btn_act3.grid(row=0, column=2, padx=2, pady=2, sticky="ew")

        self.refresh()

    def _get_display_path(self):
        """Formatuje pełny adres na przyjazny skrót: NAZWA_MASZYNY / podścieżka."""
        try:
            rel = self.current_path.relative_to(self.root_machine_path)
            # Podmienia ukośniki systemowe Windows \ na uniwersalne /
            rel_str = str(rel).replace("\\", "/")
            return f"{self.selected_machine} / {rel_str}"
        except ValueError:
            return f"{self.selected_machine} / ."

    @staticmethod
    def natural_sort_key(s):
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", str(s))
        ]

    def _select_machine(self, machine_name):
        self.selected_machine = machine_name
        self.root_machine_path = Path(self.machines[self.selected_machine])
        self.current_path = self.root_machine_path
        self.search_var.set("")
        self._clear_selection()
        self.refresh()

    def refresh(self):
        query = self.search_var.get().lower().strip()

        # Wyświetlamy ładny, skrócony adres
        self.path_label.configure(text=self._get_display_path())
        self.status_label.configure(
            text="⏳ Odczyt z katalogu...", text_color="gray"
        )

        def load():
            items = []
            err = None
            try:
                if not self.current_path.exists():
                    err = f"Brak dostępu do maszyny {self.selected_machine}."
                else:
                    with os.scandir(self.current_path) as entries:
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

            self.after(0, lambda: self._apply_results(items, err))

        threading.Thread(target=load, daemon=True).start()

    def _apply_results(self, items, err):
        for widget in self.items_list_frame.winfo_children():
            widget.destroy()

        self._clear_selection()

        if err:
            self.status_label.configure(
                text=f"🔴 {self.selected_machine}: BRAK DOSTĘPU",
                text_color="#FF5555",
            )
            lbl = ctk.CTkLabel(
                self.items_list_frame, text=f"⚠️ {err}", text_color="#FF5555"
            )
            lbl.pack(padx=5, pady=5)
            return

        self.status_label.configure(
            text=f"🟢 {self.selected_machine}: ONLINE", text_color="#55FF55"
        )

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

        for item_type, name, path_str in items:
            full_path = Path(path_str)
            icon = "📁" if item_type == "dir" else "📄"
            color = "gray90" if item_type == "dir" else "#FFD700"

            btn = ctk.CTkButton(
                self.items_list_frame,
                text=f"{icon} {name}",
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
            f"[MASZYNA] Zaznaczono: {self.selected_item_type.upper()} ->"
            f" {self.selected_item_path}"
        )

    def _on_double_click(self, path, item_type):
        if item_type == "dir":
            self.current_path = path
            self.search_var.set("")
            self.refresh()

    def _clear_selection(self):
        self.selected_item_path = None
        self.selected_item_type = None
        self.selected_button = None

    def _go_up(self):
        if self.current_path != self.root_machine_path:
            self.current_path = self.current_path.parent
            self.search_var.set("")
            self.refresh()

    def _exec_action(self, action_num):
        if not self.selected_item_path:
            print(f"[MASZYNA] Akcja M{action_num}: Nic nie jest zaznaczone!")
        else:
            print(
                f"[MASZYNA] Akcja M{action_num} na zaznaczonym elemencie:"
                f" {self.selected_item_type} -> {self.selected_item_path}"
            )