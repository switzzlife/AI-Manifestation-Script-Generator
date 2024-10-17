import os
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from app import app, db, login_manager
from models import User, Script, Post, Comment
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm
from chat_request import send_openai_request

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        if form.profile_photo.data:
            filename = secure_filename(form.profile_photo.data.filename)
            form.profile_photo.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_photo = filename
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/profile')
@login_required
def profile():
    scripts = current_user.scripts.order_by(Script.created_at.desc()).all()
    return render_template('profile.html', user=current_user, scripts=scripts)

@app.route('/generate_script', methods=['GET', 'POST'])
@login_required
def generate_script():
    form = ScriptGenerationForm()
    if form.validate_on_submit():
        prompt = f"Generate a manifestation script for {form.goal.data} with a focus on {form.focus.data} and a duration of {form.duration.data} minutes. The script should be inspiring, positive, and tailored to the user's specific goal. Include affirmations and visualizations related to the goal."
        try:
            script_content = send_openai_request(prompt)
            script = Script(content=script_content, author=current_user)
            db.session.add(script)
            db.session.commit()
            flash('Your manifestation script has been generated and saved!')
            return redirect(url_for('view_script', script_id=script.id))
        except Exception as e:
            flash(f'An error occurred while generating the script: {str(e)}')
            return redirect(url_for('generate_script'))
    return render_template('generate_script.html', form=form)

@app.route('/view_script/<int:script_id>')
@login_required
def view_script(script_id):
    script = Script.query.get_or_404(script_id)
    if script.author != current_user:
        flash('You do not have permission to view this script.')
        return redirect(url_for('profile'))
    return render_template('view_script.html', script=script)

@app.route('/community')
@login_required
def community():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    form = PostForm()
    comment_form = CommentForm()
    return render_template('community.html', posts=posts, form=form, comment_form=comment_form)

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!')
        return redirect(url_for('community'))
    return redirect(url_for('community'))

@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!')
        return redirect(url_for('community'))
    return redirect(url_for('community'))
