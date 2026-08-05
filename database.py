import os
import sqlite3
from pathlib import Path


class DatabaseManager:
    """Zarządza lokalną bazą SQLite służącą do szybkiego indeksowania i wyszukiwania folderów/plików."""

    def __init__(self, db_path="file_index.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Inicjalizuje strukturę tabeli oraz dba o obecność kolumny mtime."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    is_dir INTEGER NOT NULL,
                    parent_path TEXT NOT NULL
                )
            """)

            cursor.execute("PRAGMA table_info(files)")
            columns = [column[1] for column in cursor.fetchall()]

            if "mtime" not in columns:
                cursor.execute(
                    "ALTER TABLE files ADD COLUMN mtime REAL DEFAULT 0"
                )

            conn.commit()

    def index_directory(self, root_path):
        """Skanuje katalog i zapisuje ścieżki z czasem modyfikacji."""
        root_path = Path(root_path)
        if not root_path.exists():
            return False, "Ścieżka nie istnieje"

        records = []
        for dirpath, dirnames, filenames in os.walk(root_path):
            current_dir = Path(dirpath)

            for d in dirnames:
                p = current_dir / d
                try:
                    mtime = p.stat().st_mtime
                except Exception:
                    mtime = 0
                records.append((d, str(p), 1, mtime, str(current_dir)))

            for f in filenames:
                p = current_dir / f
                try:
                    mtime = p.stat().st_mtime
                except Exception:
                    mtime = 0
                records.append((f, str(p), 0, mtime, str(current_dir)))

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files")
            cursor.executemany(
                """
                INSERT OR REPLACE INTO files (name, path, is_dir, mtime, parent_path)
                VALUES (?, ?, ?, ?, ?)
            """,
                records,
            )
            conn.commit()

        return True, "Zaindeksowano pomyślnie"

    def search_orders(self, query, limit=100):
        """
        Wyszukuje FOLDERY powiązane z szukaną frazą.
        Sortujewyniki OD NAJNOWSZEGO (mtime DESC).
        Zwraca krotkę: (typ, nazwa, ścieżka, mtime).
        """
        if not query:
            return []

        search_pattern = f"%{query.lower()}%"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # UNION łączy pasujące foldery oraz foldery rodzicielskie pasujących plików
            # ORDER BY mtime DESC wymusza najnowsze elementy na samej górze
            cursor.execute(
                """
                SELECT name, path, mtime FROM files 
                WHERE is_dir = 1 AND LOWER(name) LIKE ?
                
                UNION
                
                SELECT f_parent.name, f_parent.path, f_parent.mtime 
                FROM files f_child
                JOIN files f_parent ON f_child.parent_path = f_parent.path
                WHERE f_child.is_dir = 0 AND LOWER(f_child.name) LIKE ? AND f_parent.is_dir = 1
                
                ORDER BY mtime DESC
                LIMIT ?
            """,
                (search_pattern, search_pattern, limit),
            )

            rows = cursor.fetchall()

        # Zwracamy zestaw danych rozszerzony o mtime: ("dir", nazwa, ścieżka, mtime)
        return [("dir", row[0], row[1], row[2]) for row in rows]

    def get_children(self, parent_path):
        """Pobiera zawartość folderu wraz z czasem modyfikacji."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT is_dir, name, path, mtime FROM files 
                WHERE parent_path = ?
                ORDER BY is_dir DESC, name ASC
            """,
                (str(parent_path),),
            )
            rows = cursor.fetchall()

        return [
            ("dir" if row[0] == 1 else "file", row[1], row[2], row[3])
            for row in rows
        ]

    def add_single_path(self, full_path, is_dir=False):
        """Zapisuje pojedynczy plik/folder w bazie po archiwizacji."""
        p = Path(full_path)
        if not p.exists():
            return
        try:
            mtime = p.stat().st_mtime
        except Exception:
            mtime = 0
        parent = str(p.parent)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO files (name, path, is_dir, mtime, parent_path)
                VALUES (?, ?, ?, ?, ?)
            """,
                (p.name, str(p), 1 if is_dir else 0, mtime, parent),
            )
            conn.commit()