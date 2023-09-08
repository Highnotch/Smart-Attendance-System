from flask_app import app
from flask import send_from_directory
import os

# Only used in development and not in 
@app.route("/<path:path>", methods=['GET'])
def serve_static_files(path):
    return send_from_directory('assets', path)

if __name__ == '__main__':
    app.run(debug=True)