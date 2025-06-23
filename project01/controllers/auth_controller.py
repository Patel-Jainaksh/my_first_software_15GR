from werkzeug.security import check_password_hash
from models.user import User
from flask import Blueprint, request, redirect, render_template,  session, url_for

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password').strip()
        user = User.query.filter_by(username=username).first()
        if user:
            if user.password.strip() == password:  # Ensure no extra spaces

                session['username'] = user.username
                session['role'] = user.role.strip()

                # Redirect based on user role
                if user.role.strip() == 'admin':
                    return redirect(url_for('admin.index'))
                elif user.role == 'operator':
                    return redirect(url_for('operator.index'))
                else:
                    return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('admin.create_user'))    
        return redirect(url_for('auth.login'))
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
def index_slash():
    return redirect(url_for('auth.login'))
