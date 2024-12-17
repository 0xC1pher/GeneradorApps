from flask import Flask, request, jsonify, render_template_string
from threading import Thread
from time import sleep
from config import MODEL_NAME, LOG_FILE, MAX_ITERATIONS
from ollama_api import OllamaAPI
from utils import log_to_file, create_directory, create_file, update_file, fetch_code, task_completed

# Inicializar Flask
app = Flask(__name__)

# Configuración de progreso
progress = {
    "status": "idle",
    "iteration": 0,
    "max_iterations": MAX_ITERATIONS,
    "output": "",
    "completed": False
}

# Funciones disponibles para el LLM
available_functions = {
    "create_directory": create_directory,
    "create_file": create_file,
    "update_file": update_file,
    "fetch_code": fetch_code,
    "task_completed": task_completed
}

# Ruta principal
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_input = request.form.get('user_input')
        progress["status"] = "running"
        progress["iteration"] = 0
        progress["output"] = ""
        progress["completed"] = False
        thread = Thread(target=run_main_loop, args=(user_input,))
        thread.start()
        return render_template_string('''
            <h1>Progreso</h1>
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
            <button id="refresh-btn" style="display:none;" onclick="location.reload();">Refrescar Página</button>
        ''', progress_output=progress["output"])
    else:
        return render_template_string('''
            <h1>Flask App Builder</h1>
            <form method="post">
                <label for="user_input">Describe la aplicación Flask que deseas crear:</label><br>
                <input type="text" id="user_input" name="user_input"><br><br>
                <input type="submit" value="Enviar">
            </form>
        ''')

# Ruta para obtener el progreso
@app.route('/progress')
def get_progress():
    return jsonify(progress)

# Función principal del bucle de ejecución
def run_main_loop(user_input):
    history_dict = {"iterations": []}
    iteration = 0
    output = ""
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
        {"role": "system", "content": f"Historial:\n{history_dict}"}
    ]

    while iteration < MAX_ITERATIONS:
        current_iteration = {
            "iteration": iteration + 1,
            "actions": [],
            "llm_responses": [],
            "tool_results": [],
            "errors": []
        }
        history_dict['iterations'].append(current_iteration)

        try:
            response = OllamaAPI.chat(MODEL_NAME, messages)
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
            output += f"\n<h2>Iteración {iteration + 1}:</h2>\n<p>{content}</p>\n"

            tool_calls = response_message.get("tool_calls", [])
            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.get("function", {}).get("name")
                    function_to_call = available_functions.get(function_name)
                    if not function_to_call:
                        error_message = f"Herramienta '{function_name}' no está disponible."
                        current_iteration['errors'].append({
                            'action': f'tool_call_{function_name}',
                            'error': error_message
                        })
                        continue

                    try:
                        function_args = tool_call.get("function", {}).get("arguments", {})
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
                            'error': error_message
                        })

            else:
                messages.append(response_message)

            progress["output"] = output

        except Exception as e:
            error = str(e)
            current_iteration['errors'].append({
                'action': 'main_loop',
                'error': error
            })

        iteration += 1
        log_to_file(history_dict)
        sleep(2)

    progress["status"] = "completed"
    progress["completed"] = True
    progress["output"] = output + "\n<h2>Proceso Finalizado: Máximo de Iteraciones Alcanzado</h2>"
    log_to_file(history_dict)
    return output

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
