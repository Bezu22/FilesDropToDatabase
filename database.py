import os
import sqlite3


class DatabaseManager:

    def __init__(self, db_file="baza_zlecen.db"):
        """Inicjalizacja bazy danych SQLite."""
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        """Tworzy połączenie z bazą SQLite."""
        return sqlite3.connect(self.db_file)

    def init_db(self):
        """Tworzy tabelę dla folderów oraz nakłada indeksy."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_name TEXT NOT NULL,
                    folder_path TEXT NOT NULL UNIQUE,
                    parent_path TEXT NOT NULL,
                    tom_files TEXT DEFAULT ''
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_folder_name ON"
                " orders(folder_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_parent_path ON"
                " orders(parent_path)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_tom_files ON orders(tom_files)"
            )
            conn.commit()

    def index_directory(self, root_path):
        """Skanuje całe poddrzewo folderów od root_path i zapisuje w bazie danych."""
        root_str = str(root_path)
        if not os.path.exists(root_str):
            return False, "Ścieżka bazowa nie istnieje."

        orders_dict = {}

        try:
            for root, dirs, files in os.walk(root_str):
                parent_path = os.path.dirname(root)
                folder_name = os.path.basename(root)

                if root not in orders_dict:
                    orders_dict[root] = {
                        "name": folder_name,
                        "parent": parent_path,
                        "tom_files": [],
                    }

                for f in files:
                    if f.lower().endswith(".tom"):
                        orders_dict[root]["tom_files"].append(f)

        except Exception as e:
            return False, f"Błąd skanowania: {e}"

        records = []
        for path_str, folder_data in orders_dict.items():
            tom_files_str = ", ".join(folder_data["tom_files"])
            records.append(
                (
                    folder_data["name"],
                    path_str,
                    folder_data["parent"],
                    tom_files_str,
                )
            )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders")
            cursor.executemany(
                """
                INSERT OR REPLACE INTO orders (folder_name, folder_path, parent_path, tom_files)
                VALUES (?, ?, ?, ?)
            """,
                records,
            )
            conn.commit()

        return True, f"Zaindeksowano {len(records)} elementów."

    def get_children(self, parent_path):
        """Pobiera foldery oraz pliki .tom znajdujące się w podanej ścieżce."""
        results = []
        parent_str = str(parent_path)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Pobieramy podfoldery znajdujące się w obecnej ścieżce
            cursor.execute(
                """
                SELECT folder_name, folder_path, tom_files FROM orders
                WHERE parent_path = ?
                ORDER BY folder_name ASC
            """,
                (parent_str,),
            )
            subfolders = cursor.fetchall()
            for name, path_str, tom_str in subfolders:
                results.append(("dir", name, path_str, tom_str))

            # 2. Sprawdzamy, czy sam obecny folder zawiera pliki .tom
            cursor.execute(
                """
                SELECT tom_files FROM orders
                WHERE folder_path = ?
            """,
                (parent_str,),
            )
            current_folder_data = cursor.fetchone()

            if current_folder_data and current_folder_data[0]:
                tom_files_list = [
                    f.strip()
                    for f in current_folder_data[0].split(",")
                    if f.strip()
                ]
                for file_name in tom_files_list:
                    file_path = os.path.join(parent_str, file_name)
                    results.append(("file", file_name, file_path, ""))

        return results

    def search_orders(self, query, limit=100):
        """Szybkie szukanie folderów z plikami po słowie kluczowym."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            wildcard = f"%{query}%"
            cursor.execute(
                """
                SELECT folder_name, folder_path, tom_files FROM orders
                WHERE folder_name LIKE ? OR tom_files LIKE ?
                ORDER BY folder_name ASC
                LIMIT ?
            """,
                (wildcard, wildcard, limit),
            )
            raw_data = cursor.fetchall()

            # Formatujemy wyniki jako typ 'dir'
            return [
                ("dir", name, path_str, tom_str)
                for name, path_str, tom_str in raw_data
            ]