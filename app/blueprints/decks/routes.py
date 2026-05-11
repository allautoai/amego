from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from datetime import datetime, timezone, timedelta
from app.models import db, Subject, Deck

decks_bp = Blueprint('decks', __name__)

class DeckForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Descripción')
    submit = SubmitField('Guardar')

    def __init__(self, subject_id, original_name=None, *args, **kwargs):
        super(DeckForm, self).__init__(*args, **kwargs)
        self.subject_id = subject_id
        self.original_name = original_name

    def validate_name(self, name):
        if self.original_name and name.data.lower() == self.original_name.lower():
            return
        deck = Deck.query.filter(Deck.subject_id == self.subject_id, Deck.name.ilike(name.data)).first()
        if deck:
            raise ValidationError('Ya tienes un mazo con este nombre en esta asignatura.')

class MoveDeckForm(FlaskForm):
    subject_id = SelectField('Nueva Asignatura', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Mover')

@decks_bp.route('/subjects/<int:id>/decks/new', methods=['GET', 'POST'])
@login_required
def new_deck(id):
    subject = Subject.query.get_or_404(id)
    if subject.user_id != current_user.id:
        abort(403)
        
    count = Deck.query.filter_by(subject_id=subject.id).count()
    if count >= 30:
        flash('Has alcanzado el límite máximo de 30 mazos por asignatura.', 'warning')
        return redirect(url_for('subjects.view_subject', id=subject.id))
        
    form = DeckForm(subject_id=subject.id)
    if form.validate_on_submit():
        deck = Deck(
            subject_id=subject.id,
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(deck)
        try:
            db.session.commit()
            flash('Mazo creado exitosamente.', 'success')
            return redirect(url_for('decks.view_deck', id=deck.id))
        except Exception:
            db.session.rollback()
            flash('Error al crear el mazo.', 'danger')
            
    return render_template('decks/form.html', form=form, title="Nuevo Mazo", subject=subject)

@decks_bp.route('/decks/<int:id>')
@login_required
def view_deck(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seven_days_ago = now - timedelta(days=7)
    needs_review = deck.last_studied_at is None or deck.last_studied_at < seven_days_ago
    
    # We also pass subjects for the move modal
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    move_form = MoveDeckForm()
    move_form.subject_id.choices = [(s.id, s.name) for s in subjects if s.id != deck.subject_id]
    
    return render_template('decks/view.html', deck=deck, needs_review=needs_review, move_form=move_form)

@decks_bp.route('/decks/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_deck(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    form = DeckForm(subject_id=deck.subject_id, original_name=deck.name, obj=deck)
    if form.validate_on_submit():
        deck.name = form.name.data
        deck.description = form.description.data
        try:
            db.session.commit()
            flash('Mazo actualizado.', 'success')
            return redirect(url_for('decks.view_deck', id=deck.id))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar.', 'danger')
            
    return render_template('decks/form.html', form=form, title="Editar Mazo")

@decks_bp.route('/decks/<int:id>/move', methods=['POST'])
@login_required
def move_deck(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    new_subject_id = request.form.get('subject_id', type=int)
    if new_subject_id:
        new_subject = Subject.query.get_or_404(new_subject_id)
        if new_subject.user_id != current_user.id:
            abort(403)
            
        count = Deck.query.filter_by(subject_id=new_subject.id).count()
        if count >= 30:
            flash('La asignatura destino ya tiene 30 mazos.', 'warning')
        else:
            collision = Deck.query.filter(Deck.subject_id == new_subject.id, Deck.name.ilike(deck.name)).first()
            if collision:
                flash('Ya existe un mazo con ese nombre en la asignatura destino.', 'danger')
            else:
                deck.subject_id = new_subject.id
                try:
                    db.session.commit()
                    flash('Mazo movido exitosamente.', 'success')
                except Exception:
                    db.session.rollback()
                    flash('Error al mover el mazo.', 'danger')
                    
    return redirect(url_for('decks.view_deck', id=deck.id))

@decks_bp.route('/decks/<int:id>/delete', methods=['POST'])
@login_required
def delete_deck(id):
    deck = Deck.query.get_or_404(id)
    if deck.user_id != current_user.id:
        abort(403)
        
    subject_id = deck.subject_id
    db.session.delete(deck)
    try:
        db.session.commit()
        flash('Mazo eliminado.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar.', 'danger')
        
    return redirect(url_for('subjects.view_subject', id=subject_id))
