from flask import Blueprint

routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/hello')
def hello():
    return "¡Hola desde la ruta de ejemplo!"
