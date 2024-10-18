import os
import stripe
import logging
from flask import render_template, flash, redirect, url_for, request, jsonify, send_file, current_app
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse
from app import app, db
from models import User, Script, Post, Comment, Subscription
from forms import LoginForm, RegistrationForm, ScriptGenerationForm, PostForm, CommentForm, AudioCustomizationForm
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from chat_request import send_openai_request
import openai

stripe.api_key = app.config['STRIPE_SECRET_KEY']
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/record_voice', methods=['POST'])
@login_required
def record_voice():
    logging.info(f"Received voice recording request from user {current_user.id}")
    
    try:
        if 'audio' not in request.files:
            logging.error("No audio file provided in the request")
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']
        script_id = request.form.get('script_id')

        logging.info(f"Received audio file: {audio_file.filename}, script_id: {script_id}")

        if audio_file.filename == '':
            logging.error("Empty filename provided for audio file")
            return jsonify({'error': 'No selected file'}), 400

        if audio_file and script_id:
            script = Script.query.get(script_id)
            if script and script.user_id == current_user.id:
                filename = secure_filename(
                    f"user_voice_{current_user.id}_{script_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.webm"
                )
                upload_folder = current_app.config['UPLOAD_FOLDER']

                logging.info(f"UPLOAD_FOLDER path: {upload_folder}")

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
                logging.error(
                    f"Invalid script or unauthorized access: script_id={script_id}, user_id={current_user.id}"
                )
                return jsonify({'error': 'Invalid script or unauthorized access'}), 403
        else:
            logging.error("Invalid request: missing audio file or script_id")
            return jsonify({'error': 'Invalid request: missing audio file or script_id'}), 400

    except Exception as e:
        logging.exception(f"Error in record_voice: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500