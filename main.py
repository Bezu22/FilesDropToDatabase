import os
import shutil
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Manager Maszyn v2.2")
        
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
        # Sekcja statusu maszyn (zamiast popupu)
        self.status_frame = tk.LabelFrame(self.root, text="Status maszyn", fg="blue")
        self.status_frame.pack(padx=20, pady=5, fill=tk.X)
        
        self.status_label = tk.Label(self.status_frame, text="Inicjalizacja...", fg="green", justify=tk.LEFT)
        self.status_label.pack(padx=10, pady=5)

        # Nagłówek listy
        tk.Label(self.root, text="Foldery operatorów (posortowane):", font=('Arial', 10, 'bold')).pack(pady=5)

        # Widok listy
        self.listbox = tk.Listbox(self.root, width=80, height=12)
        self.listbox.pack(padx=20, pady=5)

        # Panel przycisków
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Zmień nazwę docelową", command=self.rename_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Odśwież (Skanuj ponownie)", command=self.check_network_and_scan).pack(side=tk.LEFT, padx=5)

        # Sekcja Postępu
        self.progress_label = tk.Label(self.root, text="Oczekiwanie na start...")
        self.progress_label.pack(pady=(10, 0))
        
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=10, padx=20)

        # Przyciski główne
        self.btn_copy = tk.Button(self.root, text="1. KOPIUJ DOSTĘPNE DANE", 
                                  bg="#5bc0de", font=('Arial', 10, 'bold'),
                                  command=self.start_copying)
        self.btn_copy.pack(pady=5, fill=tk.X, padx=100)

        self.btn_delete = tk.Button(self.root, text="2. POTWIERDŹ I USUŃ ORYGINAŁY", 
                                    bg="#d9534f", fg="white", font=('Arial', 10, 'bold'),
                                    state='disabled', command=self.confirm_and_delete)
        self.btn_delete.pack(pady=10, fill=tk.X, padx=100)

    def check_network_and_scan(self):
        """Skanuje i aktualizuje status w oknie."""
        self.found_folders = []
        self.successfully_copied = []
        self.btn_delete.config(state='disabled')
        
        all_names = []
        status_text = []
        
        for name, path in self.machines.items():
            if not os.path.exists(path):
                status_text.append(f"● {name}: NIEDOSTĘPNA")
                continue
            
            status_text.append(f"● {name}: OK")
            for folder_name in os.listdir(path):
                f_path = os.path.join(path, folder_name)
                if os.path.isdir(f_path):
                    conflict = folder_name in all_names
                    self.found_folders.append({
                        'name': folder_name, 'path': f_path, 
                        'machine': name, 'conflict': conflict
                    })
                    all_names.append(folder_name)

        # Aktualizacja etykiety statusu
        self.status_label.config(text="\n".join(status_text), fg="black")
        
        # --- SORTOWANIE PO NUMERACH ---
        # Próbujemy sortować numerycznie, jeśli się nie da (np. folder "A"), używamy alfabetu
        try:
            self.found_folders.sort(key=lambda x: int(x['name']))
        except ValueError:
            self.found_folders.sort(key=lambda x: x['name'])
            
        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for idx, f in enumerate(self.found_folders):
            status = "[!] DUPLIKAT" if f['conflict'] else ""
            line = f"[{f['name']}] - lokalizacja: {f['machine']} {status}"
            self.listbox.insert(tk.END, line)
            if f['conflict']: self.listbox.itemconfig(idx, {'fg': 'red'})

    def rename_folder(self):
        sel = self.listbox.curselection()
        if not sel: return
        idx = sel[0]
        new_name = simpledialog.askstring("Nazwa", f"Nowa nazwa dla {self.found_folders[idx]['name']}:", 
                                          initialvalue=self.found_folders[idx]['name'])
        if new_name:
            self.found_folders[idx]['name'] = new_name
            # Po zmianie nazwy odświeżamy sortowanie i konflikty
            names = []
            for f in self.found_folders:
                f['conflict'] = f['name'] in names
                names.append(f['name'])
            self.refresh_listbox()

    def start_copying(self):
        if not self.found_folders: return
        
        total_files = 0
        for f in self.found_folders:
            for root, dirs, files in os.walk(f['path']):
                total_files += len(files)
        
        if total_files == 0:
            messagebox.showinfo("Info", "Foldery są puste - nie ma czego kopiować.")
            return

        self.progress['maximum'] = total_files
        current_step = 0
        self.successfully_copied = []

        for folder in self.found_folders:
            dest_path = os.path.join(self.destination, folder['name'])
            os.makedirs(dest_path, exist_ok=True)
            
            try:
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
                
                self.successfully_copied.append(folder['path'])
            except Exception as e:
                messagebox.showerror("Błąd", f"Przerwano przy folderze {folder['name']}: {e}")
                break

        self.progress_label.config(text="Pliki skopiowane pomyślnie!")
        if self.successfully_copied:
            self.btn_delete.config(state='normal')

    def confirm_and_delete(self):
        if messagebox.askyesno("Ostrzeżenie", f"Czy na pewno chcesz usunąć {len(self.successfully_copied)} folderów źródłowych?"):
            deleted_count = 0
            for path in self.successfully_copied:
                try:
                    shutil.rmtree(path)
                    deleted_count += 1
                except:
                    pass
            messagebox.showinfo("Koniec pracy", f"Pomyślnie usunięto {deleted_count} folderów.")
            self.check_network_and_scan()

if __name__ == "__main__":
    app_root = tk.Tk()
    my_app = App(app_root)
    app_root.mainloop()