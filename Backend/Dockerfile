# Usamos una versión ligera de Python
FROM python:3.11-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero el archivo de librerías para aprovechar la caché de Docker
COPY requirements.txt .

# Instalamos las librerías necesarias (paho-mqtt y mysql-connector)
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del backend (el archivo processor.py)
COPY . .

# Comando para ejecutar el procesador de datos
CMD ["python", "processor.py"]