import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Local: python run.py -> http://127.0.0.1:5000
    # Hosted platforms (Render, Railway, ...) set PORT and need 0.0.0.0.
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", host=host, port=port)
