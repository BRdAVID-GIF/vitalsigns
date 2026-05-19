import paho.mqtt.client as mqtt
from paho.mqtt import client as mqtt_client
import mysql.connector
import json
import time

# --- CONFIGURACIÓN DE CONEXIÓN DB ---

def get_db_connection():
    """Intenta conectar a la base de datos hasta que tenga éxito."""
    while True:
        try:
            conn = mysql.connector.connect(
                host="mysql.ferrocarril.interno",
                user="root",
                password="pAtBbDuWBcjCxlGqGAsLLlBbIXzPBBIA",
                database="railway",
                port=3306
            )
            print("✅ Conectado a MySQL exitosamente!")
            return conn
        except mysql.connector.Error as err:
            print(f"❌ Error de conexión DB: {err}. Reintentando en 3 segundos...")
            time.sleep(3)

# Conexión global
db = get_db_connection()

# --- LÓGICA MQTT ---

def on_connect(client, userdata, flags, reason_code, properties):
    """Se ejecuta cuando conecta al broker. Aquí se suscribe de forma segura."""
    if reason_code == 0:
        print("✅ Conectado al broker MQTT!")
        client.subscribe("esp32/temperatura")
        print("📡 Suscrito a 'esp32/temperatura'")
    else:
        print(f"❌ Falló conexión al broker, código: {reason_code}")

def on_message(client, userdata, msg):
    """Procesa cada mensaje recibido con cursor fresco y reconexión segura."""
    global db

    try:
        # Reconexión si la DB cayó
        if not db.is_connected():
            print("⚠️ Conexión perdida con DB. Reconectando...")
            db = get_db_connection()

        data = json.loads(msg.payload.decode())

        temp_amb  = data.get('temperatura_ambiente', 0.0)
        temp_corp = data.get('temperatura_corporal', 0.0)

        # ✅ Cursor fresco por cada mensaje — evita "Unread result" errors
        with db.cursor() as cursor:
            query = "INSERT INTO lecturas (temp_ambiente, temp_corporal) VALUES (%s, %s)"
            cursor.execute(query, (temp_amb, temp_corp))
            db.commit()
            print(f"📥 Datos guardados: temp_amb={temp_amb}, temp_corp={temp_corp}")

    except mysql.connector.Error as db_err:
        print(f"⚠️ Error de base de datos: {db_err}")
        db.rollback()
    except json.JSONDecodeError as je:
        print(f"❗ JSON inválido recibido: {je}")
    except Exception as e:
        print(f"❗ Error inesperado: {e}")

# --- INICIALIZACIÓN DEL CLIENTE MQTT ---

client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect   # ✅ Suscripción dentro del callback seguro
client.on_message = on_message

def start_mqtt():
    """Inicia la conexión al broker con reintentos seguros."""
    while True:
        try:
            print("🔄 Conectando al broker 'emqx'...")
            client.connect("emqx", 1883, 60)
            client.loop_forever()

        except Exception as e:
            print(f"❌ Error de conexión al broker: {e}. Reintentando en 5 segundos...")
            # ✅ Desconectar limpiamente antes de reintentar
            try:
                client.disconnect()
            except:
                pass
            time.sleep(5)

if __name__ == "__main__":
    start_mqtt()