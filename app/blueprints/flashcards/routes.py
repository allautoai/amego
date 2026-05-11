from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired
from app.models import db, Deck, Flashcard

flashcards_bp = Blueprint('flashcards', __name__)

class FlashcardForm(FlaskForm):
    question = TextAreaField('Pregunta', validators=[DataRequired()])
    answer = TextAreaField('Respuesta', validators=[DataRequired()])
    submit = SubmitField('Guardar')

@flashcards_bp.route('/decks/<int:id>/flashcards/new', methods=['GET', 'POST'])
@login_required
def new_flashcard(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    count = Flashcard.query.filter_by(deck_id=deck.id).count()
    if count >= 100:
        flash('Has alcanzado el límite de 100 flashcards por mazo.', 'warning')
        return redirect(url_for('decks.view_deck', id=deck.id))
        
    form = FlashcardForm()
    if form.validate_on_submit():
        max_order = db.session.query(db.func.max(Flashcard.order_index)).filter_by(deck_id=deck.id).scalar() or 0
        flashcard = Flashcard(
            deck_id=deck.id,
            question=form.question.data,
            answer=form.answer.data,
            order_index=max_order + 1
        )
        db.session.add(flashcard)
        try:
            db.session.commit()
            flash('Flashcard añadida.', 'success')
            return redirect(url_for('decks.view_deck', id=deck.id))
        except Exception:
            db.session.rollback()
            flash('Error al añadir flashcard.', 'danger')
            
    return render_template('flashcards/form.html', form=form, title="Nueva Flashcard", deck=deck)

@flashcards_bp.route('/flashcards/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_flashcard(id):
    flashcard = Flashcard.query.get_or_404(id)
    deck = flashcard.deck
    if deck.user_id != current_user.id:
        abort(403)
        
    form = FlashcardForm(obj=flashcard)
    if form.validate_on_submit():
        flashcard.question = form.question.data
        flashcard.answer = form.answer.data
        try:
            db.session.commit()
            flash('Flashcard actualizada.', 'success')
            return redirect(url_for('decks.view_deck', id=deck.id))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar.', 'danger')
            
    return render_template('flashcards/form.html', form=form, title="Editar Flashcard", deck=deck)

@flashcards_bp.route('/flashcards/<int:id>/delete', methods=['POST'])
@login_required
def delete_flashcard(id):
    flashcard = Flashcard.query.get_or_404(id)
    deck = flashcard.deck
    if deck.user_id != current_user.id:
        abort(403)
        
    db.session.delete(flashcard)
    try:
        db.session.commit()
        flash('Flashcard eliminada.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar.', 'danger')
        
    return redirect(url_for('decks.view_deck', id=deck.id))
