import os
import shutil
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from datetime import datetime

CONFIG_FILE = "config.json"
LOG_FILE = "transfer_log.txt"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("File Transfer v0.3")
        
        self.load_config()
        
        self.found_folders = []
        self.successfully_copied = [] 
        self.log_entries = [] # Przechowuje dane do zapisu w logu

        self.setup_ui()
        self.check_network_and_scan()

    def load_config(self):
        """Ładuje ścieżki z pliku JSON lub tworzy domyślny."""
        default_config = {
            "machines": {
                "Maszyna 1": r'C:\Users\User\Documents\testy\Maszyna1',
                "Maszyna 2": r'C:\Users\User\Documents\testy\Maszyna2',
                "Maszyna 3": r'C:\Users\User\Documents\testy\Maszyna3',
                "Maszyna 4": r'C:\Users\User\Documents\testy\Maszyna4'
            },
            "destination": r'C:\Users\User\Documents\testy\docelowy'
        }

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.machines = config.get("machines", default_config["machines"])
                    self.destination = config.get("destination", default_config["destination"])
            except Exception as e:
                messagebox.showerror("Błąd Config", f"Błąd pliku config.json.\n{e}")
                self.machines = default_config["machines"]
                self.destination = default_config["destination"]
        else:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            self.machines = default_config["machines"]
            self.destination = default_config["destination"]

    def setup_ui(self):
        # 1. Status maszyn
        self.status_frame = tk.LabelFrame(self.root, text="Dostępność maszyn", fg="blue")
        self.status_frame.pack(padx=20, pady=10, fill=tk.X)
        self.status_label = tk.Label(self.status_frame, text="", justify=tk.LEFT, font=('Consolas', 9))
        self.status_label.pack(padx=10, pady=5)

        # 2. Lista z Multi-Select
        tk.Label(self.root, text="Zaznacz foldery (Ctrl/Shift):", font=('Arial', 9, 'bold')).pack(pady=5)
        
        list_container = tk.Frame(self.root)
        list_container.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(list_container, width=80, height=12, 
                                  yscrollcommand=self.scrollbar.set, 
                                  font=('Consolas', 10),
                                  selectmode=tk.EXTENDED) 
        
        self.scrollbar.config(command=self.listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 3. Przyciski edycji
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Zmień nazwę docelową", command=self.rename_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Odśwież listę", command=self.check_network_and_scan).pack(side=tk.LEFT, padx=5)

        # 4. Postęp
        self.progress_label = tk.Label(self.root, text="Gotowy")
        self.progress_label.pack(pady=(10, 0))
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=10, padx=20)

        # 5. Przyciski akcji
        self.btn_copy = tk.Button(self.root, text="1. KOPIUJ ZAZNACZONE", 
                                  bg="#5bc0de", font=('Arial', 10, 'bold'),
                                  command=self.start_transfer)
        self.btn_copy.pack(pady=5, fill=tk.X, padx=100)

        self.btn_delete = tk.Button(self.root, text="2. POTWIERDŹ SUKCES I USUŃ Z MASZYN", 
                                    bg="#d9534f", fg="white", font=('Arial', 10, 'bold'),
                                    state='disabled', command=self.confirm_and_delete)
        self.btn_delete.pack(pady=10, fill=tk.X, padx=100)

    def check_network_and_scan(self):
        self.found_folders = []
        self.successfully_copied = []
        self.log_entries = []
        self.btn_delete.config(state='disabled')
        self.progress['value'] = 0
        
        status_text = []
        all_found_names = []
        
        for name, path in self.machines.items():
            if not os.path.exists(path):
                status_text.append(f"[-] {name:<12}: NIEDOSTĘPNA")
                continue
            
            status_text.append(f"[+] {name:<12}: OK")
            for folder_name in os.listdir(path):
                f_path = os.path.join(path, folder_name)
                if os.path.isdir(f_path):
                    self.found_folders.append({
                        'name': folder_name, 'path': f_path, 
                        'machine': name, 'conflict': False
                    })
                    all_found_names.append(folder_name)

        for f in self.found_folders:
            if all_found_names.count(f['name']) > 1:
                f['conflict'] = True

        self.status_label.config(text="\n".join(status_text))
        try:
            self.found_folders.sort(key=lambda x: int(x['name']))
        except ValueError:
            self.found_folders.sort(key=lambda x: x['name'])
        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for idx, f in enumerate(self.found_folders):
            status = "[!] DUPLIKAT" if f['conflict'] else ""
            line = f"{f['machine']:<15} | Numer: {f['name']:<10} {status}"
            self.listbox.insert(tk.END, line)
            if f['conflict']: self.listbox.itemconfig(idx, {'fg': 'red'})

    def rename_folder(self):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]
        new_name = simpledialog.askstring("Nazwa", "Nowa nazwa:", initialvalue=self.found_folders[idx]['name'])
        if new_name:
            self.found_folders[idx]['name'] = new_name
            names = [f['name'] for f in self.found_folders]
            for f in self.found_folders:
                f['conflict'] = names.count(f['name']) > 1
            self.refresh_listbox()

    def save_to_log(self, machine, folder_num, status):
        """Zapisuje zdarzenie do pliku tekstowego."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] Maszyna: {machine:<12} | Folder: {folder_num:<10} | Status: {status}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)

    def start_transfer(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Wybór", "Zaznacz foldery!")
            return

        to_process = [self.found_folders[i] for i in selected_indices]
        
        # Sprawdzanie duplikatów
        sel_names = [f['name'] for f in to_process]
        if len(sel_names) != len(set(sel_names)):
            if not messagebox.askyesno("Duplikaty", "Wykryto te same numery. Scalić?"):
                return

        # Analiza pustych
        empty_folders = []
        total_files = 0
        for f in to_process:
            f_count = sum([len(files) for r, d, files in os.walk(f['path'])])
            if f_count == 0: empty_folders.append(f['name'])
            total_files += f_count

        skip_empty = False
        if empty_folders:
            choice = messagebox.askyesnocancel("Puste foldery", 
                f"Wykryto puste: {', '.join(empty_folders)}\n\nTAK-Pomiń, NIE-Kopiuj puste, ANULUJ-Przerwij")
            if choice is None: return
            skip_empty = choice

        self.progress['maximum'] = total_files if total_files > 0 else len(to_process)
        current_step = 0
        self.successfully_copied = []

        for folder in to_process:
            if folder['name'] in empty_folders and skip_empty: continue

            dest_path = os.path.join(self.destination, folder['name'])
            os.makedirs(dest_path, exist_ok=True)
            
            try:
                if folder['name'] not in empty_folders:
                    for root_dir, _, files in os.walk(folder['path']):
                        rel = os.path.relpath(root_dir, folder['path'])
                        target = os.path.join(dest_path, rel)
                        os.makedirs(target, exist_ok=True)
                        for file in files:
                            self.progress_label.config(text=f"Kopiowanie: {file}")
                            shutil.copy2(os.path.join(root_dir, file), os.path.join(target, file))
                            current_step += 1
                            self.progress['value'] = current_step
                            self.root.update_idletasks()
                else:
                    if total_files == 0:
                        current_step += 1
                        self.progress['value'] = current_step
                
                self.successfully_copied.append(folder['path'])
                # Rejestrujemy udane kopiowanie do logu
                self.log_entries.append((folder['machine'], folder['name'], "SKOPIOWANO"))
            except Exception as e:
                self.log_entries.append((folder['machine'], folder['name'], f"BŁĄD: {e}"))
                messagebox.showerror("Błąd", str(e))
                break

        self.progress_label.config(text="Transfer zakończony!")
        if self.successfully_copied:
            self.btn_delete.config(state='normal')

    def confirm_and_delete(self):
        if messagebox.askyesno("Usuwanie", f"Usunąć {len(self.successfully_copied)} folderów z maszyn?"):
            for path in self.successfully_copied:
                try: 
                    shutil.rmtree(path)
                    # Szukamy nazwy maszyny i folderu dla tego path, by zapisać usunięcie
                    for m_name, m_path in self.machines.items():
                        if path.startswith(m_path):
                            f_name = os.path.basename(path)
                            self.save_to_log(m_name, f_name, "PRZENIESIONO (Skopiowano i Usunięto)")
                except: pass
            messagebox.showinfo("Koniec", "Gotowe. Log został zaktualizowany.")
            self.check_network_and_scan()

if __name__ == "__main__":
    app_root = tk.Tk()
    app_root.minsize(650, 550)
    app = App(app_root)
    app_root.mainloop()