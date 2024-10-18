from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, NumberRange
from flask_wtf.file import FileField, FileRequired, FileAllowed
from models import User

# ... (keep other form classes)

class ScriptGenerationForm(FlaskForm):
    goal = StringField('Manifestation Goal', validators=[DataRequired()])
    focus = SelectField('Focus Area', choices=[('health', 'Health'), ('wealth', 'Wealth'), ('relationships', 'Relationships'), ('career', 'Career')], validators=[DataRequired()])
    duration = SelectField('Script Duration', choices=[('5', '5 minutes'), ('10', '10 minutes'), ('15', '15 minutes')], validators=[DataRequired()])
    tone = SelectField('Script Tone', choices=[('positive', 'Positive'), ('energetic', 'Energetic'), ('calm', 'Calm'), ('confident', 'Confident')], validators=[DataRequired()])
    visualization = SelectField('Visualization Type', choices=[('guided', 'Guided Imagery'), ('future_self', 'Future Self'), ('vision_board', 'Mental Vision Board')], validators=[DataRequired()])
    affirmation_style = SelectField('Affirmation Style', choices=[('present', 'Present Tense'), ('future', 'Future Tense'), ('gratitude', 'Gratitude-based')], validators=[DataRequired()])
    custom_prompt = TextAreaField('Custom Prompt (Optional)', validators=[Length(max=500)])
    generate_audio = BooleanField('Generate Audio')
    submit = SubmitField('Generate Script')

# ... (keep other form classes)
