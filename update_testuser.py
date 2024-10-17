from app import app, db
from models import User

def update_testuser():
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        if user:
            user.is_paid = False
            user.scripts_generated = 0
            db.session.commit()
            print("Testuser updated: is_paid=False, scripts_generated=0")
        else:
            print("Testuser not found")

if __name__ == "__main__":
    update_testuser()
