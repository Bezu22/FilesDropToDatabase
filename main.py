import customtkinter as ctk
from config import MACHINES, MAIN_DB_PATH
from panels.bottom_panel import BottomPanel
from panels.database_panel import DatabasePanel
from panels.machine_panel import MachinePanel

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class NetworkFileManager(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Network File Manager")
        self.geometry("1100x700")

        # Układ siatki
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Tworzenie widoków z modułu panels
        self.left_panel = MachinePanel(self, MACHINES)
        self.left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.right_panel = DatabasePanel(self, MAIN_DB_PATH)
        self.right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.bottom_panel = BottomPanel(self)
        self.bottom_panel.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew"
        )


if __name__ == "__main__":
    app = NetworkFileManager()
    app.mainloop()