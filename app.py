import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

app = Flask(__name__)
app.config.from_object('config.Config')

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

with app.app_context():
    import models
    db.create_all()

from routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
