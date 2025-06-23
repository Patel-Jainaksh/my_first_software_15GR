from models.user import User, db
from werkzeug.security import generate_password_hash  # For password hashing

class UserService:
    @staticmethod
    def create_user(data):
        # Validate data
        if not data:
            return {'error': 'No data provided'}, 400

        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'admin')

        if not username or not password:
            return {'error': 'Username and Password are required'}, 400

        # Check if the user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return {'error': 'User already exists'}, 409

        # Hash the password before saving
        # hashed_password = generate_password_hash(password)
        hashed_password=password
        # Create a new User instance
        new_user = User(
            username=username,
            password=hashed_password,
            role=role
        )

        # Add user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            return {
                'message': 'User created successfully',
                'user': {
                    'id': new_user.id,
                    'username': new_user.username,
                    'role': new_user.role
                }
            }, 201
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to create user: {str(e)}'}, 500
