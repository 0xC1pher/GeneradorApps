Para adaptar el código existente y utilizar la API de Ollama en lugar de OpenAI, necesitaremos hacer algunos cambios significativos. Ollama parece ser una API diferente a OpenAI, por lo que no podemos simplemente reemplazar las llamadas a la API de OpenAI con llamadas a Ollama. Necesitaremos refactorizar el código para que funcione con la API de Ollama.

A continuación, te muestro cómo podrías refactorizar el código para usar la API de Ollama, conservando la lógica y el flujo originales. Este código asume que tienes una biblioteca o módulo en Python que interactúa con la API de Ollama.

### Refactorización del Código

#### 1. Importaciones y Configuración
Primero, necesitamos importar las bibliotecas necesarias y configurar la API de Ollama.

```python
import os
import sys
import json
import importlib
import traceback
from flask import Flask, Blueprint, request, send_from_directory, render_template_string, jsonify
from threading import Thread
from time import sleep

# Importación de la API de Ollama
from ollama import API as OllamaAPI

# Configuración de la API de Ollama
ollama_api = OllamaAPI.new()

# Configuración
MODEL_NAME = os.environ.get('OLLAMA_MODEL', 'llama2')  # Default model; can be swapped easily

# Initialize Flask app
app = Flask(__name__)

LOG_FILE = "flask_app_builder_log.json"

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
ROUTES_DIR = os.path.join(BASE_DIR, 'routes')

# Initialize progress tracking
progress = {
    "status": "idle",
    "iteration": 0,
    "max_iterations": 50,
    "output": "",
    "completed": False
}

# Ensure directories exist and create __init__.py in routes
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        if path == ROUTES_DIR:
            create_file(os.path.join(ROUTES_DIR, '__init__.py'), '')
        return f"Created directory: {path}"
    return f"Directory already exists: {path}"

def create_file(path, content):
    try:
        with open(path, 'x') as f:
            f.write(content)
        return f"Created file: {path}"
    except FileExistsError:
        with open(path, 'w') as f:
            f.write(content)
        return f"Updated file: {path}"
    except Exception as e:
        return f"Error creating/updating file {path}: {e}"

def update_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Updated file: {path}"
    except Exception as e:
        return f"Error updating file {path}: {e}"

def fetch_code(file_path):
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        return code
    except Exception as e:
        return f"Error fetching code from {file_path}: {e}"

def load_routes():
    try:
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
        for filename in os.listdir(ROUTES_DIR):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                module_path = f'routes.{module_name}'
                try:
                    if module_path in sys.modules:
                        importlib.reload(sys.modules[module_path])
                    else:
                        importlib.import_module(module_path)
                    module = sys.modules.get(module_path)
                    if module:
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, Blueprint):
                                app.register_blueprint(attr)
                except Exception as e:
                    print(f"Error importing module {module_path}: {e}")
                    continue
        print("Routes loaded successfully.")
        return "Routes loaded successfully."
    except Exception as e:
        print(f"Error in load_routes: {e}")
        return f"Error loading routes: {e}"

def task_completed():
    progress["status"] = "completed"
    progress["completed"] = True
    return "Task marked as completed."

# Initialize necessary directories
create_directory(TEMPLATES_DIR)
create_directory(STATIC_DIR)
create_directory(ROUTES_DIR)  # This will also create __init__.py in routes

# Load routes once at initiation
load_routes()

# Function to log history to file
def log_to_file(history_dict):
    try:
        with open(LOG_FILE, 'w') as log_file:
            json.dump(history_dict, log_file, indent=4)
    except Exception as e:
        pass  # Silent fail

# Default route to serve generated index.html or render a form
@app.route('/', methods=['GET', 'POST'])
def home():
    index_file = os.path.join(TEMPLATES_DIR, 'index.html')
    if os.path.exists(index_file):
        return send_from_directory(TEMPLATES_DIR, 'index.html')
    else:
        if request.method == 'POST':
            user_input = request.form.get('user_input')
            progress["status"] = "running"
            progress["iteration"] = 0
            progress["output"] = ""
            progress["completed"] = False
            thread = Thread(target=run_main_loop, args=(user_input,))
            thread.start()
            return render_template_string('''
                <h1>Progress</h1>
                <pre id="progress">{{ progress_output }}</pre>
                <script>
                    setInterval(function() {
                        fetch('/progress')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('progress').innerHTML = data.output;
                            if (data.completed) {
                                document.getElementById('refresh-btn').style.display = 'block';
                            }
                        });
                    }, 2000);
                </script>
                <button id="refresh-btn" style="display:none;" onclick="location.reload();">Refresh Page</button>
            ''', progress_output=progress["output"])
        else:
            return render_template_string('''
                <h1>Flask App Builder</h1>
                <form method="post">
                    <label for="user_input">Describe the Flask app you want to create:</label><br>
                    <input type="text" id="user_input" name="user_input"><br><br>
                    <input type="submit" value="Submit">
                </form>
            ''')

# Route to provide progress updates
@app.route('/progress')
def get_progress():
    return jsonify(progress)

# Available functions for the LLM
available_functions = {
    "create_directory": create_directory,
    "create_file": create_file,
    "update_file": update_file,
    "fetch_code": fetch_code,
    "task_completed": task_completed
}

# Define the tools for function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Creates a new directory at the specified path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to create."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Creates or updates a file at the specified path with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to create or update."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_file",
            "description": "Updates an existing file at the specified path with the new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to update."
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_code",
            "description": "Retrieves the code from the specified file path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The file path to fetch the code from."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "task_completed",
            "description": "Indicates that the assistant has completed the task.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def run_main_loop(user_input):
    # Reset the history_dict for each run
    history_dict = {
        "iterations": []
    }

    max_iterations = progress["max_iterations"]  # Prevent infinite loops
    iteration = 0

    # Updated messages array with enhanced prompt
    messages = [
        {
            "role": "system",
            "content": (
                "Eres un experto desarrollador de Flask encargado de construir una aplicación Flask completa y lista para producción basada en la descripción del usuario. "
                "Antes de codificar, planifica cuidadosamente todos los archivos, rutas, plantillas y activos estáticos necesarios. "
                "Sigue estos pasos:\n"
                "1. **Entiende los Requisitos**: Analiza la entrada del usuario para comprender completamente la funcionalidad y las características de la aplicación.\n"
                "2. **Planifica la Estructura de la Aplicación**: Enumera todas las rutas, plantillas y archivos estáticos que necesitan ser creados. Considera cómo interactúan.\n"
                "3. **Implementa Paso a Paso**: Para cada componente, utiliza las herramientas proporcionadas para crear directorios, archivos y escribir código. Asegúrate de que cada paso esté completamente terminado antes de continuar.\n"
                "4. **Revisa y Refina**: Usa `fetch_code` para revisar el código que has escrito. Actualiza los archivos si es necesario usando `update_file`.\n"
                "5. **Asegura la Completitud**: No dejes ningún marcador de posición o código incompleto. Todas las funciones, rutas y plantillas deben estar completamente implementadas y listas para producción.\n"
                "6. **No Modifiques `main.py`**: Concéntrate solo en los directorios `templates/`, `static/`, y `routes/`.\n"
                "7. **Finaliza**: Una vez que todo esté completo y probado a fondo, llama a `task_completed()` para terminar.\n\n"
                "Restricciones y Notas:\n"
                "- Los archivos de la aplicación deben estar estructurados dentro de los directorios predefinidos: `templates/`, `static/`, y `routes/`.\n"
                "- Las rutas deben ser modulares y colocadas dentro del directorio `routes/` como archivos Python separados.\n"
                "- El `index.html` servido desde el directorio `templates/` es el punto de entrada de la aplicación. Actualízalo apropiadamente si se crean plantillas adicionales.\n"
                "- No uses marcadores de posición como 'Contenido va aquí'. Todo el código debe ser completo y funcional.\n"
                "- No pidas al usuario más entrada; infiere cualquier detalle necesario para completar la aplicación.\n"
                "- Asegúrate de que todas las rutas estén correctamente vinculadas y que las plantillas incluyan los archivos CSS y JS necesarios.\n"
                "- Maneja cualquier error internamente y trata de resolverlos antes de continuar.\n\n"
                "Herramientas Disponibles:\n"
                "- `create_directory(path)`: Crea un nuevo directorio.\n"
                "- `create_file(path, content)`: Crea o sobrescribe un archivo con contenido.\n"
                "- `update_file(path, content)`: Actualiza un archivo existente con nuevo contenido.\n"
                "- `fetch_code(file_path)`: Recupera el código de un archivo para revisión.\n"
                "- `task_completed()`: Llama a esto cuando la aplicación esté completamente construida y lista.\n\n"
                "Recuerda pensar cuidadosamente en cada paso, asegurando que la aplicación esté completa, funcional y cumpla con los requisitos del usuario."
            )
        },
        {"role": "user", "content": user_input},
        {"role": "system", "content": f"Historial:\n{json.dumps(history_dict, indent=2)}"}
    ]

    output = ""

    while iteration < max_iterations:
        progress["iteration"] = iteration + 1
        current_iteration = {
            "iteration": iteration + 1,
            "actions": [],
            "llm_responses": [],
            "tool_results": [],
            "errors": []
        }
        history_dict['iterations'].append(current_iteration)

        try:
            response = OllamaAPI.chat(ollama_api, [
                "model": MODEL_NAME,
                "messages": messages
            ])

            if response.get("status") != "ok":
                error = response.get('error', 'Unknown error')
                current_iteration['errors'].append({'action': 'llm_completion', 'error': error})
                log_to_file(history_dict)
                sleep(5)
                iteration += 1
                continue

            response_message = response.get("message", {})
            content = response_message.get("content", "")
            current_iteration['llm_responses'].append(content)

            output += f"\n<h2>Iteración {iteration + 1}:</h2>\n"

            tool_calls = response_message.get("tool_calls", [])

            if tool_calls:
                output += "<strong>Llamada a Herramienta:</strong>\n<p>" + content + "</p>\n"
                messages.append(response_message)

                for tool_call in tool_calls:
                    function_name = tool_call.get("function", {}).get("name")
                    function_to_call = available_functions.get(function_name)

                    if not function_to_call:
                        error_message = f"Herramienta '{function_name}' no está disponible."
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message,
                            'traceback': 'No traceback available.'
                        })
                        continue

                    try:
                        function_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                        function_response = function_to_call(**function_args)
                        current_iteration['tool_results'].append({
                            'tool': function_name,
                            'result': function_response
                        })
                        output += f"<strong>Resultado de Herramienta ({function_name}):</strong>\n<p>{function_response}</p>\n"
                        messages.append(
                            {"tool_call_id": tool_call.get("id"), "role": "tool", "name": function_name, "content": function_response}
                        )
                        if function_name == "task_completed":
                            progress["status"] = "completed"
                            progress["completed"] = True
                            output += "\n<h2>COMPLETADO</h2>\n"
                            progress["output"] = output
                            log_to_file(history_dict)
                            return output

                    except Exception as tool_error:
                        error_message = f"Error ejecutando {function_name}: {tool_error}"
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message,
                            'traceback': traceback.format_exc()
                        })

                second_response = OllamaAPI.chat(ollama_api, [
                    "model": MODEL_NAME,
                    "messages": messages
                ])
                if second_response.get("status") == "ok" and second_response.get("message"):
                    second_response_message = second_response.get("message", {})
                    content = second_response_message.get("content", "")
                    current_iteration['llm_responses'].append(content)
                    output += "<strong>Respuesta del LLM:</strong>\n<p>" + content + "</p>\n"
                    messages.append(second_response_message)
                else:
                    error = second_response.get('error', 'Unknown error in second LLM response.')
                    current_iteration['errors'].append({'action': 'second_llm_completion', 'error': error})

            else:
                output += "<strong>Respuesta del LLM:</strong>\n<p>" + content + "</p>\n"
                messages.append(response_message)

            progress["output"] = output

        except Exception as e:
            error = str(e)
            current_iteration['errors'].append({
                'action': 'main_loop',
                'error': error,
                'traceback': traceback.format_exc()
            })

        iteration += 1
        log_to_file(history_dict)
        sleep(2)

    if iteration >= max_iterations:
        progress["status"] = "completed"

    progress["completed"] = True
    progress["status"] = "completed"

    return output

if __name__ == '__main__':
    # Start the Flask app
    app.run(host='0.0.0.0', port=8080)
```

### Cambios Principales

1. **Importación de la API de Ollama**: Se ha importado la API de Ollama y se ha configurado una instancia de la misma.
2. **Uso de OllamaAPI.chat**: En lugar de usar `completion` de OpenAI, ahora se usa `OllamaAPI.chat` para interactuar con el modelo de lenguaje.
3. **Manejo de Respuestas**: Se han ajustado las estructuras de datos para manejar las respuestas de Ollama, que pueden tener una estructura diferente a las de OpenAI.
4. **Traducción de Mensajes**: Todos los mensajes del sistema y las instrucciones se han traducido al español para que el modelo responda en ese idioma.

Este código debería funcionar con la API de Ollama, manteniendo la lógica y el flujo originales del código base. Asegúrate de que la biblioteca `ollama` esté instalada y configurada correctamente en tu entorno.
