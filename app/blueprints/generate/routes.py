from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
import fitz  # PyMuPDF
from app.models import db, Deck, Flashcard, Quiz, QuizQuestion, QuizOption
from app.services.ai_service import generate_flashcards, generate_quiz

generate_bp = Blueprint('generate', __name__)

class GenerateTextForm(FlaskForm):
    text = TextAreaField('Texto', validators=[DataRequired(), Length(min=100, max=5000)])
    submit = SubmitField('Generar')

class UploadPDFForm(FlaskForm):
    pdf = FileField('Archivo PDF', validators=[
        DataRequired(),
        FileAllowed(['pdf'], 'Solo archivos PDF.')
    ])
    submit = SubmitField('Extraer Texto')

@generate_bp.route('/decks/<int:id>/generate', methods=['GET'])
@login_required
def generate_index(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    text_form = GenerateTextForm()
    pdf_form = UploadPDFForm()
    
    # Pre-fill text if it was extracted from PDF
    extracted_text = session.pop('extracted_text', '')
    if extracted_text:
        text_form.text.data = extracted_text
        
    return render_template('generate/index.html', deck=deck, text_form=text_form, pdf_form=pdf_form)

@generate_bp.route('/decks/<int:id>/generate/upload-pdf', methods=['POST'])
@login_required
def upload_pdf(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    form = UploadPDFForm()
    if form.validate_on_submit():
        file = form.pdf.data
        if file.content_length and file.content_length > 5 * 1024 * 1024:
            flash('El archivo es demasiado grande. Máximo 5MB.', 'danger')
            return redirect(url_for('generate.generate_index', id=deck.id))
            
        try:
            # Read pdf
            pdf_data = file.read()
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
                if len(text) >= 8000:
                    break
            text = text[:8000] # Ensure we don't exceed 8000 chars for safety
            
            session['extracted_text'] = text
            flash('Texto extraído exitosamente. Por favor, edítalo si es necesario (max 5000 caracteres) y genera.', 'success')
        except Exception as e:
            flash(f'Error al leer el PDF: {str(e)}', 'danger')
            
    return redirect(url_for('generate.generate_index', id=deck.id))

@generate_bp.route('/decks/<int:id>/generate/flashcards', methods=['POST'])
@login_required
def generate_flashcards_preview(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    form = GenerateTextForm()
    if form.validate_on_submit():
        text = form.text.data
        try:
            cards = generate_flashcards(text)
            session['preview_flashcards'] = cards
            return render_template('generate/preview_flashcards.html', deck=deck, cards=cards)
        except Exception as e:
            flash(str(e), 'danger')
            
    return redirect(url_for('generate.generate_index', id=deck.id))

@generate_bp.route('/decks/<int:id>/generate/flashcards/confirm', methods=['POST'])
@login_required
def generate_flashcards_confirm(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    cards = session.pop('preview_flashcards', [])
    if not cards:
        flash('No hay flashcards para confirmar o la sesión ha expirado.', 'warning')
        return redirect(url_for('generate.generate_index', id=deck.id))
        
    selected_indices = request.form.getlist('selected')
    
    current_count = Flashcard.query.filter_by(deck_id=deck.id).count()
    max_order = db.session.query(db.func.max(Flashcard.order_index)).filter_by(deck_id=deck.id).scalar() or 0
    
    added = 0
    for idx_str in selected_indices:
        if current_count >= 100:
            flash('Se alcanzó el límite de 100 flashcards por mazo. Se omitieron algunas.', 'warning')
            break
            
        try:
            idx = int(idx_str)
            card = cards[idx]
            max_order += 1
            f = Flashcard(
                deck_id=deck.id,
                question=card['question'],
                answer=card['answer'],
                source='ai_generated',
                order_index=max_order
            )
            db.session.add(f)
            current_count += 1
            added += 1
        except (ValueError, IndexError, KeyError):
            pass
            
    if added > 0:
        try:
            db.session.commit()
            flash(f'{added} flashcards generadas guardadas exitosamente.', 'success')
        except Exception:
            db.session.rollback()
            flash('Error al guardar las flashcards.', 'danger')
            
    return redirect(url_for('decks.view_deck', id=deck.id))

@generate_bp.route('/decks/<int:id>/generate/quiz', methods=['POST'])
@login_required
def generate_quiz_preview(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    form = GenerateTextForm()
    if form.validate_on_submit():
        text = form.text.data
        try:
            questions = generate_quiz(text)
            session['preview_quiz_questions'] = questions
            session['preview_quiz_source'] = text
            return render_template('generate/preview_quiz.html', deck=deck, questions=questions)
        except Exception as e:
            flash(str(e), 'danger')
            
    return redirect(url_for('generate.generate_index', id=deck.id))

@generate_bp.route('/decks/<int:id>/generate/quiz/confirm', methods=['POST'])
@login_required
def generate_quiz_confirm(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    questions = session.pop('preview_quiz_questions', [])
    source_text = session.pop('preview_quiz_source', '')
    title = request.form.get('title', 'Quiz Generado por IA')
    
    if not questions:
        flash('No hay preguntas para confirmar o la sesión ha expirado.', 'warning')
        return redirect(url_for('generate.generate_index', id=deck.id))
        
    quiz = Quiz(
        deck_id=deck.id,
        user_id=current_user.id,
        title=title,
        source_text=source_text
    )
    db.session.add(quiz)
    
    try:
        db.session.flush()
        for idx, q_data in enumerate(questions):
            q = QuizQuestion(
                quiz_id=quiz.id,
                question_text=q_data['question'],
                correct_option_index=q_data['correct_index'],
                order_index=idx
            )
            db.session.add(q)
            db.session.flush()
            for opt_idx, opt_text in enumerate(q_data['options']):
                opt = QuizOption(
                    question_id=q.id,
                    option_text=opt_text,
                    option_index=opt_idx
                )
                db.session.add(opt)
        db.session.commit()
        flash('Quiz generado guardado exitosamente.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al guardar el quiz.', 'danger')
        
    return redirect(url_for('decks.view_deck', id=deck.id))
