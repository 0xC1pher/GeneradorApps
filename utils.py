import os
import json
import traceback

def log_to_file(history_dict):
    try:
        with open(LOG_FILE, 'w') as log_file:
            json.dump(history_dict, log_file, indent=4)
    except Exception as e:
        print(f"Error al escribir en el archivo de registro: {e}")

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        return f"Directorio creado: {path}"
    return f"El directorio ya existe: {path}"

def create_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Archivo creado: {path}"
    except Exception as e:
        return f"Error al crear archivo: {e}"

def update_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Archivo actualizado: {path}"
    except Exception as e:
        return f"Error al actualizar archivo: {e}"

def fetch_code(file_path):
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error al leer archivo: {e}"

def task_completed():
    return "Tarea completada."
