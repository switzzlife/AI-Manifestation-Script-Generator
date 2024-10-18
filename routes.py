import os
import logging
from flask import request, jsonify, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from datetime import datetime
from app import app, db
from models import Script

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
            # Check file size (limit to 10MB)
            if len(audio_file.read()) > 10 * 1024 * 1024:
                logging.error("File size exceeds the limit of 10MB")
                return jsonify({'error': 'File size exceeds the limit of 10MB'}), 400
            audio_file.seek(0)  # Reset file pointer after reading
            
            # Check file type
            allowed_extensions = {'wav', 'mp3', 'ogg'}
            if '.' not in audio_file.filename or \
               audio_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                logging.error(f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}")
                return jsonify({'error': f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"}), 400
            
            script = Script.query.get(script_id)
            if script and script.user_id == current_user.id:
                filename = secure_filename(f"user_voice_{current_user.id}_{script_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
                upload_folder = current_app.config['UPLOAD_FOLDER']
                
                # Ensure upload folder exists
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
