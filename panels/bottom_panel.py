import customtkinter as ctk


class BottomPanel(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, height=50)

        self.info_label = ctk.CTkLabel(
            self, text="Gotowy. Wybierz pliki do wykonania akcji."
        )
        self.info_label.pack(side="left", padx=15, pady=10)