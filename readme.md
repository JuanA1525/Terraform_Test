## FIFA Brackets · Torneos de FIFA con Flask

Una app web en Flask para crear torneos de FIFA con llaves de eliminación, gestión de equipos y registro de resultados.

### Características
- Crea torneos (4, 8 o 16 equipos)
- Agrega equipos con logo
- Genera el bracket de forma automática
- Registra marcadores y propaga ganadores
- Vista del bracket por rondas
- Ruta de demo para poblar datos rápidamente
- Easter eggs: activa el Konami Code en cualquier página 😉

### Requisitos
- Python 3.10+

### Instalación local
```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Abre http://localhost:5000

### Semillas de datos (demo)
Visita: /admin/seed?key=dev para crear un torneo de ejemplo con 8 equipos y bracket listo.

### Infra (opcional)
El repo incluye Terraform y un workflow de GitHub Actions para crear una EC2 y desplegar automáticamente. La instancia clona el repo, instala dependencias y ejecuta `python3 app.py` escuchando en el puerto 5000.

### Notas
- Configura `SECRET_KEY` en entorno para CSRF en formularios.
- Base de datos por defecto: SQLite `fifa.db` en el directorio del proyecto.
- Para producción, se recomienda ejecutar con Gunicorn y un reverse proxy (Nginx) y usar systemd.
