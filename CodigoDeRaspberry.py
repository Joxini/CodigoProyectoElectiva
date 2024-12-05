import cv2
import numpy as np
import RPi.GPIO as GPIO
import requests
from flask import Flask, render_template, Response
import time

# Inicializar la cámara
videoCam = cv2.VideoCapture(0)

# Configurar Flask
app = Flask(__name__)

# Configurar GPIO para los servos
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pines para los servos
SERVO_1_PIN = 12
SERVO_2_PIN = 13

GPIO.setup(SERVO_1_PIN, GPIO.OUT)
GPIO.setup(SERVO_2_PIN, GPIO.OUT)

servo1 = GPIO.PWM(SERVO_1_PIN, 50)  # Frecuencia de 50Hz
servo2 = GPIO.PWM(SERVO_2_PIN, 50)  # Frecuencia de 50Hz

servo1.start(0)
servo2.start(0)

# Función para mover el servo a un ángulo específico
def mover_servo(servo, angulo):
    duty = 2 + (angulo / 18)  # Calcular ciclo de trabajo basado en ángulo
    servo.ChangeDutyCycle(duty)
    time.sleep(0.5)  # Esperar para asegurar que el movimiento sea completo
    servo.ChangeDutyCycle(0)  # Apagar el servo para evitar sobrecalentamiento

# Inicializar servos en posición inicial (arriba)
def reset_servos():
    mover_servo(servo1, 0)
    mover_servo(servo2, 0)

# Función para detectar el color más prominente
def detectar_color(frame):
    altura, ancho, _ = frame.shape
    recorte = frame[altura // 3: 2 * altura // 3, ancho // 4: 3 * ancho // 4]
    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)

    rangos_colores = {
        "Rojo": ([0, 120, 70], [10, 255, 255]),
        "Amarillo": ([25, 150, 150], [35, 255, 255]),
        "Azul": ([90, 50, 50], [130, 255, 255])
    }

    for color, (lower, upper) in rangos_colores.items():
        lower_np = np.array(lower, np.uint8)
        upper_np = np.array(upper, np.uint8)
        mascara = cv2.inRange(hsv, lower_np, upper_np)
        if cv2.countNonZero(mascara) > 500:  # Ajustar umbral para detección precisa
            return color
    return "No detectado"

# Generador de video
def procesar_video():
    ultimo_color = None
    tiempo_inicio_movimiento = 0
    estado_servo1 = "Arriba"
    estado_servo2 = "Arriba"

    while True:
        ret, frame = videoCam.read()
        if not ret:
            print("Error al capturar la cámara")
            break

        color_detectado = detectar_color(frame)

        if color_detectado != ultimo_color:
            # Acciones según el color detectado
            if color_detectado == "Rojo":
                mover_servo(servo1, 90)  # Bajar servo 1
                estado_servo1 = "Bajado"
                tiempo_inicio_movimiento = time.time()

            elif color_detectado == "Azul":
                mover_servo(servo2, 90)  # Bajar servo 2
                estado_servo2 = "Bajado"
                tiempo_inicio_movimiento = time.time()

            elif color_detectado == "Amarillo":
                reset_servos()  # Ambos arriba
                estado_servo1 = "Arriba"
                estado_servo2 = "Arriba"

            ultimo_color = color_detectado

        # Verificar si han pasado 15 segundos para devolver los servos arriba
        if estado_servo1 == "Bajado" and time.time() - tiempo_inicio_movimiento > 10:
            mover_servo(servo1, 0)
            estado_servo1 = "Arriba"

        if estado_servo2 == "Bajado" and time.time() - tiempo_inicio_movimiento > 10:
            mover_servo(servo2, 0)
            estado_servo2 = "Arriba"

        # Mostrar texto en el frame
        color_texto = (0, 255, 255) if color_detectado == "Amarillo" else (0, 0, 255) if color_detectado == "Rojo" else (255, 0, 0) if color_detectado == "Azul" else (255, 255, 255)
        cv2.putText(frame, f"Color: {color_detectado}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color_texto, 2, cv2.LINE_AA)

        ret, buffer = cv2.imencode('.jpeg', frame)
        if not ret:
            continue
        frame = buffer.tobytes()

        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def camara():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(procesar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        reset_servos()  # Colocar servos en posición inicial antes de comenzar
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        reset_servos()  # Regresar servos a la posición inicial al salir
        servo1.stop()
        servo2.stop()
        GPIO.cleanup()
        videoCam.release()
        cv2.destroyAllWindows()
