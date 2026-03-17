import os
import shutil
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Manager Maszyn v2.5")
        
        # --- KONFIGURACJA TESTOWA ---
        self.machines = {
            "Maszyna 1": r'C:\Users\User\Documents\testy\Maszyna1',
            "Maszyna 2": r'C:\Users\User\Documents\testy\Maszyna2',
            "Maszyna 3": r'C:\Users\User\Documents\testy\Maszyna3',
            "Maszyna 4": r'C:\Users\User\Documents\testy\Maszyna4'
        }
        self.destination = r'C:\Users\User\Documents\testy\docelowy'
        # ----------------------------
        
        self.found_folders = []
        self.successfully_copied = [] 

        self.setup_ui()
        self.check_network_and_scan()

    def setup_ui(self):
        # 1. Sekcja statusu maszyn
        self.status_frame = tk.LabelFrame(self.root, text="Status połączenia z maszynami", fg="blue")
        self.status_frame.pack(padx=20, pady=10, fill=tk.X)
        
        self.status_label = tk.Label(self.status_frame, text="Inicjalizacja...", justify=tk.LEFT)
        self.status_label.pack(padx=10, pady=5)

        # 2. Lista z paskiem przewijania
        tk.Label(self.root, text="Lista folderów do przeniesienia:", font=('Arial', 10, 'bold')).pack(pady=5)
        
        list_container = tk.Frame(self.root)
        list_container.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(list_container, width=80, height=12, yscrollcommand=self.scrollbar.set, font=('Consolas', 10))
        
        self.scrollbar.config(command=self.listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 3. Przyciski edycji
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Zmień nazwę docelową", command=self.rename_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Odśwież listę", command=self.check_network_and_scan).pack(side=tk.LEFT, padx=5)

        # 4. Postęp
        self.progress_label = tk.Label(self.root, text="Gotowy do pracy")
        self.progress_label.pack(pady=(10, 0))
        
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=10, padx=20)

        # 5. Przyciski główne
        self.btn_copy = tk.Button(self.root, text="1. KOPIUJ DANE", 
                                  bg="#5bc0de", font=('Arial', 10, 'bold'),
                                  command=self.start_transfer)
        self.btn_copy.pack(pady=5, fill=tk.X, padx=100)

        self.btn_delete = tk.Button(self.root, text="2. USUŃ Z MASZYN (POTWIERDŹ SUKCES)", 
                                    bg="#d9534f", fg="white", font=('Arial', 10, 'bold'),
                                    state='disabled', command=self.confirm_and_delete)
        self.btn_delete.pack(pady=10, fill=tk.X, padx=100)

    def check_network_and_scan(self):
        self.found_folders = []
        self.successfully_copied = []
        self.btn_delete.config(state='disabled')
        all_names = []
        status_text = []
        
        for name, path in self.machines.items():
            if not os.path.exists(path):
                status_text.append(f"❌ {name}: NIEDOSTĘPNA")
                continue
            
            status_text.append(f"✅ {name}: OK")
            for folder_name in os.listdir(path):
                f_path = os.path.join(path, folder_name)
                if os.path.isdir(f_path):
                    conflict = folder_name in all_names
                    self.found_folders.append({
                        'name': folder_name, 'path': f_path, 
                        'machine': name, 'conflict': conflict
                    })
                    all_names.append(folder_name)

        self.status_label.config(text="\n".join(status_text))
        
        # Sortowanie numeryczne lub alfabetyczne
        try:
            self.found_folders.sort(key=lambda x: int(x['name']))
        except ValueError:
            self.found_folders.sort(key=lambda x: x['name'])
            
        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for idx, f in enumerate(self.found_folders):
            status = "[!] DUPLIKAT" if f['conflict'] else ""
            # Format: Maszyna | Numer
            line = f"{f['machine']:<15} | Numer: {f['name']:<10} {status}"
            self.listbox.insert(tk.END, line)
            if f['conflict']: self.listbox.itemconfig(idx, {'fg': 'red'})

    def rename_folder(self):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]
        new_name = simpledialog.askstring("Nazwa", "Podaj nową nazwę docelową:", initialvalue=self.found_folders[idx]['name'])
        if new_name:
            self.found_folders[idx]['name'] = new_name
            # Przelicz konflikty
            seen = []
            for f in self.found_folders:
                f['conflict'] = f['name'] in seen
                seen.append(f['name'])
            self.refresh_listbox()

    def start_transfer(self):
        if not self.found_folders: return

        # Sprawdzenie duplikatów
        if any(f['conflict'] for f in self.found_folders):
            if not messagebox.askyesno("Duplikaty", "Wykryto duplikaty numerów. Pliki zostaną scalone. Kontynuować?"):
                return

        # Sprawdzenie pustych folderów
        empty_folders = []
        total_files = 0
        for f in self.found_folders:
            files_in_folder = 0
            for _, _, files in os.walk(f['path']):
                files_in_folder += len(files)
            if files_in_folder == 0:
                empty_folders.append(f['name'])
            total_files += files_in_folder

        skip_empty = False
        if empty_folders:
            msg = f"Następujące foldery są puste:\n{', '.join(empty_folders)}\n\nCzy chcesz je POMINĄĆ? (Nie = zostaną utworzone puste foldery)"
            skip_empty = messagebox.askyesno("Puste foldery", msg)

        # Ustawienie paska postępu
        # Jeśli kopiujemy same puste foldery, dajemy 100 jako max
        self.progress['maximum'] = total_files if total_files > 0 else len(self.found_folders)
        current_step = 0
        self.successfully_copied = []

        for folder in self.found_folders:
            # Sprawdzanie czy folder jest pusty i czy go pomijamy
            is_empty = folder['name'] in empty_folders
            if is_empty and skip_empty:
                continue

            dest_path = os.path.join(self.destination, folder['name'])
            os.makedirs(dest_path, exist_ok=True)
            
            try:
                # Jeśli folder ma pliki, kopiujemy je
                if not is_empty:
                    for root_dir, dirs, files in os.walk(folder['path']):
                        rel_path = os.path.relpath(root_dir, folder['path'])
                        target_dir = os.path.join(dest_path, rel_path)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        for file in files:
                            self.progress_label.config(text=f"Kopiowanie: {file}")
                            shutil.copy2(os.path.join(root_dir, file), os.path.join(target_dir, file))
                            current_step += 1
                            self.progress['value'] = current_step
                            self.root.update_idletasks()
                else:
                    # Jeśli folder jest pusty, po prostu go odznaczamy jako skopiowany (utworzony wyżej)
                    if total_files == 0:
                        current_step += 1
                        self.progress['value'] = current_step
                        self.root.update_idletasks()

                self.successfully_copied.append(folder['path'])
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd: {e}")
                break

        self.progress_label.config(text="Proces zakończony!")
        if self.successfully_copied:
            self.btn_delete.config(state='normal')

    def confirm_and_delete(self):
        if messagebox.askyesno("Usuwanie", f"Usunąć {len(self.successfully_copied)} folderów źródłowych?"):
            for path in self.successfully_copied:
                try:
                    shutil.rmtree(path)
                except:
                    pass
            messagebox.showinfo("Sukces", "Oryginały zostały usunięte.")
            self.check_network_and_scan()

if __name__ == "__main__":
    app_root = tk.Tk()
    app_root.minsize(600, 500)
    app = App(app_root)
    app_root.mainloop()