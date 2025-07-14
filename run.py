import os

from dotenv import dotenv_values, load_dotenv

from app import create_app

load_dotenv()

# Initialize Flask app
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("ENV", "development") != "production"

    app.run(host="0.0.0.0", port=port, debug=debug)
