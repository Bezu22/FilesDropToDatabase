class ClickHandler:
    """Zarządza stoperem do rozróżniania pojedynczego i podwójnego kliknięcia."""

    def __init__(self, parent_widget):
        self.parent_widget = parent_widget  # Widget z metodą .after() do stoperów
        self._click_timer = None

    def handle_click(
        self, path, item_type, button_widget, on_single, on_double
    ):
        """Główna metoda wywoływana przy zdarzeniu <Button-1>.

        :param path: Ścieżka klikniętego elementu (Path)
        :param item_type: Typ elementu ('dir' lub 'file')
        :param button_widget: Referencja do klikniętego przycisku CTkButton
        :param on_single: Funkcja do wywołania przy pojedynczym kliknięciu
        :param on_double: Funkcja do wywołania przy podwójnym kliknięciu
        """
        if self._click_timer is not None:
            # Drugie kliknięcie w krótkim czasie (poniżej 250ms) -> Double Click!
            self.parent_widget.after_cancel(self._click_timer)
            self._click_timer = None
            on_double(path, item_type)
        else:
            # Pierwsze kliknięcie -> Czekamy 250ms na ewentualne drugie kliknięcie
            self._click_timer = self.parent_widget.after(
                250,
                lambda: self._execute_single_click(
                    path, item_type, button_widget, on_single
                ),
            )

    def _execute_single_click(self, path, item_type, button_widget, on_single):
        """Wykonuje akcję pojedynczego kliknięcia po upływie czasu opóźnienia."""
        self._click_timer = None
        on_single(path, item_type, button_widget)