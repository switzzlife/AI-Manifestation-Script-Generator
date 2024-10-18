import os
import requests
from flask import jsonify, render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user, login_user, logout_user
from app import app, db
from models import User, Script, Post, Comment
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm, AudioCustomizationForm
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from openai import OpenAI
from urllib.parse import urlparse

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')

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
        user = User(username=form.username.data, email=form.email.data, profile_photo='default.jpg')
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
    scripts = Script.query.filter_by(user_id=current_user.id).order_by(Script.created_at.desc()).all()
    form = ScriptGenerationForm()
    return render_template('profile.html', user=current_user, scripts=scripts, form=form)

@app.route('/record_voice', methods=['POST'])
@login_required
def record_voice():
    logging.info(f"Received voice recording request from user {current_user.id}")
    if 'audio' not in request.files:
        logging.error("No audio file provided in the request")
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    script_id = request.form.get('script_id')
    
    if audio_file.filename == '':
        logging.error("Empty filename provided for audio file")
        return jsonify({'error': 'No selected file'}), 400
    
    if audio_file and script_id:
        try:
            script = Script.query.get(script_id)
            if script and script.user_id == current_user.id:
                filename = secure_filename(f"user_voice_{current_user.id}_{script_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
                upload_folder = current_app.config['UPLOAD_FOLDER']
                
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                    logging.info(f"Created UPLOAD_FOLDER: {upload_folder}")
                
                audio_path = os.path.join(upload_folder, filename)
                audio_file.save(audio_path)
                logging.info(f"Saved audio file: {audio_path}")
                
                script.audio_file = filename
                db.session.commit()
                logging.info(f"Updated script {script_id} with new audio file: {filename}")
                
                return jsonify({'success': True, 'filename': filename}), 200
            else:
                logging.error(f"Invalid script or unauthorized access: script_id={script_id}, user_id={current_user.id}")
                return jsonify({'error': 'Invalid script or unauthorized access'}), 403
        except Exception as e:
            logging.error(f"Error saving audio file: {str(e)}")
            return jsonify({'error': f'Failed to save audio file: {str(e)}'}), 500
    
    logging.error("Invalid request: missing audio file or script_id")
    return jsonify({'error': 'Invalid request'}), 400

def send_webhook_request(prompt):
    webhook_url = os.environ.get("SCRIPT_GENERATION_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("SCRIPT_GENERATION_WEBHOOK_URL environment variable is not set")
    
    payload = {"prompt": prompt}
    response = requests.post(webhook_url, json=payload)
    
    if response.status_code == 200:
        try:
            json_response = response.json()
            if 'content' in json_response:
                return json_response['content']
            else:
                raise ValueError("Unexpected JSON structure in webhook response: 'content' key not found")
        except ValueError as e:
            raise Exception(f"Error parsing JSON from webhook response: {str(e)}")
    else:
        raise Exception(f"Webhook request failed with status code {response.status_code}")

@app.route('/generate_script', methods=['GET', 'POST'])
@login_required
def generate_script():
    form = ScriptGenerationForm()
    if form.validate_on_submit():
        prompt = f"Generate a {form.duration.data}-minute guided manifestation instruction for {form.goal.data}. Focus on {form.focus.data}. Use a {form.tone.data} tone, incorporate {form.visualization.data} visualization, and use {form.affirmation_style.data} affirmations. Make sure the result is conversation, add '...' between sentences where you think the reader should pause or talk slowly. Make sure the result is something that I can send directly to a TTS program and it will read it out loud for the user."
        
        try:
            script_content = send_webhook_request(prompt)
            if not script_content:
                raise ValueError("Empty script content received from webhook")
            
            script = Script(content=script_content, user_id=current_user.id)
            db.session.add(script)
            db.session.commit()
            
            return redirect(url_for('view_script', script_id=script.id))
        except Exception as e:
            flash(f"Error generating script: {str(e)}", "error")
            return redirect(url_for('generate_script'))
    return render_template('generate_script.html', title='Generate Script', form=form)

@app.route('/view_script/<int:script_id>', methods=['GET', 'POST'])
@login_required
def view_script(script_id):
    script = Script.query.get_or_404(script_id)
    if script.user_id != current_user.id:
        flash('You do not have permission to view this script.', 'error')
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        if 'generate_audio' in request.form:
            try:
                audio_filename = f"audio_{script.id}.mp3"
                audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
                
                user_voice_filename = request.form.get('user_voice_filename')
                if user_voice_filename:
                    user_voice_path = os.path.join(app.config['UPLOAD_FOLDER'], user_voice_filename)
                    audio_response = openai_client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=script.content,
                        voice_file=user_voice_path
                    )
                else:
                    audio_response = openai_client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=script.content
                    )
                
                with open(audio_path, "wb") as audio_file:
                    audio_file.write(audio_response.content)
                
                script.audio_file = audio_filename
                db.session.commit()
                
                flash('Audio generated successfully!', 'success')
            except Exception as e:
                flash(f"Error generating audio: {str(e)}", "error")
    
    return render_template('view_script.html', title='View Script', script=script)

@app.route('/get_audio/<int:script_id>')
@login_required
def get_audio(script_id):
    script = Script.query.get_or_404(script_id)
    if script.user_id != current_user.id:
        flash('You do not have permission to access this audio.', 'error')
        return redirect(url_for('profile'))
    if script.audio_file:
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], script.audio_file)
        if os.path.exists(audio_path):
            return send_file(audio_path, as_attachment=True)
        else:
            flash('Audio file not found.', 'error')
            return redirect(url_for('view_script', script_id=script_id))
    else:
        flash('No audio file available for this script.', 'error')
        return redirect(url_for('view_script', script_id=script_id))

@app.route('/community', methods=['GET', 'POST'])
@login_required
def community():
    form = PostForm()
    comment_form = CommentForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('community'))
    
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('community.html', title='Community', form=form, comment_form=comment_form, posts=posts)

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'errors': form.errors}), 400

@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, user_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'errors': form.errors}), 400

@app.route('/my_audio_files')
@login_required
def my_audio_files():
    scripts_with_audio = Script.query.filter_by(user_id=current_user.id).filter(Script.audio_file.isnot(None)).order_by(Script.created_at.desc()).all()
    return render_template('my_audio_files.html', title='My Audio Files', scripts=scripts_with_audio)

@app.route('/manifestation_session', methods=['GET', 'POST'])
@login_required
def manifestation_session():
    app.logger.info(f"User {current_user.id} accessing manifestation_session")
    form = AudioCustomizationForm()
    scripts_with_audio = Script.query.filter_by(user_id=current_user.id).filter(Script.audio_file.isnot(None)).order_by(Script.created_at.desc()).all()
    
    form.script.choices = [(str(script.id), f"Script #{script.id}") for script in scripts_with_audio]
    
    if form.volume.data is None:
        form.volume.data = 0.5
    if form.background_volume.data is None:
        form.background_volume.data = 0.5
    if form.playback_speed.data is None:
        form.playback_speed.data = 1.0
    
    if form.validate_on_submit():
        script_id = int(form.script.data)
        script = Script.query.get(script_id)
        if script and script.user_id == current_user.id:
            script.background_music = form.background_music.data
            script.volume = form.volume.data
            script.background_volume = form.background_volume.data
            script.playback_speed = form.playback_speed.data
            db.session.commit()
            flash('Audio customization applied successfully!', 'success')
        else:
            flash('Invalid script selection.', 'error')
        return redirect(url_for('manifestation_session'))
    
    return render_template('manifestation_session.html', title='Manifestation Session', form=form, scripts=scripts_with_audio)

@app.route('/get_background_music/<filename>')
@login_required
def get_background_music(filename):
    audio_folder = os.path.join(current_app.static_folder, 'audio')
    file_path = os.path.join(audio_folder, filename)
    
    # Remove duplicate .mp3 extension if present
    if file_path.endswith('.mp3.mp3'):
        file_path = file_path[:-4]
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/delete_script/<int:script_id>', methods=['POST'])
@login_required
def delete_script(script_id):
    script = Script.query.get_or_404(script_id)
    if script.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        if script.audio_file:
            audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], script.audio_file)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        
        db.session.delete(script)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Script deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500