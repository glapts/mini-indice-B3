"""
gerar_backup.py
Compacta o algoritmo em formato .zip e sincroniza automaticamente com o Google Drive e Área de Trabalho.
"""
import os
import shutil
import zipfile
from datetime import datetime

base_dir = os.path.dirname(os.path.abspath(__file__))
backups_dir = os.path.join(base_dir, "backups")
os.makedirs(backups_dir, exist_ok=True)

today_dmy = datetime.now().strftime("%d-%m-%Y")
zip_filename = f"mini-indice-B3_backup_{today_dmy}.zip"
zip_path = os.path.join(backups_dir, zip_filename)

ignore_dirs = {"backups", "build", "dist", "__pycache__", ".git", "logs_antigos"}
ignore_exts = {".pyc", ".pyo"}

files_to_add = []
for root, dirs, files in os.walk(base_dir):
    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
    rel_root = os.path.relpath(root, base_dir)
    if any(part in ignore_dirs for part in rel_root.split(os.sep)):
        continue
    for f in files:
        if any(f.endswith(ext) for ext in ignore_exts):
            continue
        if rel_root.startswith("data") and (".log" in f):
            continue
        if f.endswith(".zip") or f.endswith(".tmp"):
            continue
        full_path = os.path.join(root, f)
        arcname = os.path.relpath(full_path, base_dir)
        files_to_add.append((full_path, arcname))

print(f"Compactando {len(files_to_add)} arquivos...")
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
    for full_path, arcname in files_to_add:
        zipf.write(full_path, arcname)

size_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"[OK] Backup gerado com sucesso: {zip_path} ({size_mb:.2f} MB)")

target_drives = [
    r"G:\Meu Drive",
    r"G:\Meu Drive\1. ALGO_B3-MINIs_VALE3",
    r"G:\My Drive",
    r"C:\Users\glaci\Google Drive",
    r"D:\Google Drive",
    r"C:\Users\glaci\OneDrive",
    r"C:\Users\glaci\OneDrive\Desktop"
]

for tgt in target_drives:
    if os.path.exists(tgt):
        dest_dated = os.path.join(tgt, zip_filename)
        dest_latest = os.path.join(tgt, f"ultimo_{today_dmy}.zip")
        shutil.copy2(zip_path, dest_dated)
        shutil.copy2(zip_path, dest_latest)
        print(f"[OK] Sincronizado para: {dest_dated}")

shutil.copy2(zip_path, os.path.join(backups_dir, f"ultimo_{today_dmy}.zip"))
print("\n[SUCESSO] Backup e sincronização com Google Drive concluídos!")
