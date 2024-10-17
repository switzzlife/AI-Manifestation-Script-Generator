from app import app, db
from models import User

def create_test_user():
    with app.app_context():
        # Check if the test user already exists
        existing_user = User.query.filter_by(username='testuser').first()
        if existing_user:
            print("Test user already exists.")
            return

        # Create a new test user
        test_user = User(username='testuser', email='testuser@example.com', profile_photo='default.jpg')
        test_user.set_password('testpassword')
        db.session.add(test_user)
        db.session.commit()
        print("Test user created successfully.")

if __name__ == "__main__":
    create_test_user()
