from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

# Configuración de Flask
app = Flask(__name__)

# Conexión a MongoDB

client = MongoClient("mongodb+srv://Prueba:imHdE05xN7pJXknd@proyectoelectiva.th9rp.mongodb.net/?retryWrites=true&w=majority&appName=ProyectoElectiva")
db = client["color_database"]
colores_collection = db["colores"]

@app.route('/guardar_color', methods=['POST'])
def guardar_color():
    """Guardar los colores detectados o actualizar su cantidad si ya existen"""
    colores = request.json  # Ahora esperamos una lista de colores
    if not isinstance(colores, list):
        return jsonify({"error": "Se espera una lista de colores"}), 400

    # Procesar cada color en la lista
    for color_data in colores:
        color = color_data.get('color')
        if not color:
            return jsonify({"error": "Cada color debe tener un campo 'color'"}), 400

        # Buscar el color en la base de datos
        color_doc = colores_collection.find_one({"color": color})

        if color_doc:
            # Si el color ya existe, actualizar su cantidad
            colores_collection.update_one(
                {"color": color},
                {"$inc": {"cantidad": 1}}  # Incrementar la cantidad por 1
            )
        else:
            # Si el color no existe, insertarlo con cantidad 1 y timestamp
            color_data['timestamp'] = datetime.now().isoformat()  # Agregar timestamp legible
            color_data['cantidad'] = 1
            colores_collection.insert_one(color_data)

    return jsonify({"message": "Colores procesados correctamente"}), 200

@app.route('/colores', methods=['GET'])
def obtener_colores():
    """Obtener todos los colores y sus cantidades"""
    colores = list(colores_collection.find({}, {"_id": 0}))

    # Convertir timestamp (en caso de ser epoch time) a formato legible
    for color in colores:
        if 'timestamp' in color and isinstance(color['timestamp'], (int, float)):
            color['timestamp'] = datetime.fromtimestamp(color['timestamp']).isoformat()

    return jsonify(colores)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
