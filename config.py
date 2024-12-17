from dotenv import load_dotenv
import os

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Acceder a las variables
MODEL_NAME = os.getenv('OLLAMA_MODEL', 'llama2')
API_KEY = os.getenv('API_KEY')
MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', 50))
LOG_FILE = os.getenv('LOG_FILE', 'logs/app_log.json')
