from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hola Mundo 2 desde Flask en EC2! <br> ¡Despliegue exitoso! - Intento 3"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
