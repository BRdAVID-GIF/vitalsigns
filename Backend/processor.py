import paho.mqtt.client as mqtt
from paho.mqtt import client as mqtt_client
import mysql.connector
import json
import time
import os

# --- CONFIGURACIÓN DE CONEXIÓN DB (desde variables de entorno) ---

DB_HOST = os.environ.get("DB_HOST", "vitales_db")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "admin")
DB_NAME = os.environ.get("DB_NAME", "hospital_db")
DB_PORT = int(os.environ.get("DB_PORT", 3306))

MQTT_BROKER = os.environ.get("MQTT_BROKER", "emqx")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "esp32/temperatura")


def get_db_connection():
    """Intenta conectar a la base de datos hasta que tenga éxito."""
    while True:
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
            )
            print(" Conectado a MySQL exitosamente!")
            return conn
        except mysql.connector.Error as err:
            print(f" Error de conexión DB: {err}. Reintentando en 3 segundos...")
            time.sleep(3)


# Conexión global
db = get_db_connection()


# --- LÓGICA MQTT ---

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(" Conectado al broker MQTT!")
        client.subscribe(MQTT_TOPIC)
        print(f"📡 Suscrito a '{MQTT_TOPIC}'")
    else:
        print(f" Falló conexión al broker, código: {reason_code}")


def on_message(client, userdata, msg):
    global db
    try:
        if not db.is_connected():
            print("⚠ Conexión perdida con DB. Reconectando...")
            db = get_db_connection()

        data = json.loads(msg.payload.decode())
        temp_amb = data.get('temperatura_ambiente', 0.0)
        temp_corp = data.get('temperatura_corporal', 0.0)

        with db.cursor() as cursor:
            query = "INSERT INTO lecturas (temp_ambiente, temp_corporal) VALUES (%s, %s)"
            cursor.execute(query, (temp_amb, temp_corp))
            db.commit()
            print(f" Datos guardados: temp_amb={temp_amb}, temp_corp={temp_corp}")

    except mysql.connector.Error as db_err:
        print(f"⚠ Error de base de datos: {db_err}")
        db.rollback()
    except json.JSONDecodeError as je:
        print(f" JSON inválido recibido: {je}")
    except Exception as e:
        print(f" Error inesperado: {e}")


# --- INICIALIZACIÓN DEL CLIENTE MQTT ---

client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message


def start_mqtt():
    while True:
        try:
            print(f" Conectando al broker '{MQTT_BROKER}:{MQTT_PORT}'...")
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            print(f" Error de conexión al broker: {e}. Reintentando en 5 segundos...")
            try:
                client.disconnect()
            except:
                pass
            time.sleep(5)


if __name__ == "__main__":
    start_mqtt()
