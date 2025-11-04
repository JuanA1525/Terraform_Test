import os
import math
import random
from datetime import datetime
from typing import List, Optional

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional as Opt

# --------------------------------------
# Configuración básica de la App
# --------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///fifa.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --------------------------------------
# Modelos
# --------------------------------------
class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    logo_url = db.Column(db.String(512))

    players = db.relationship("Player", backref="team", lazy=True, cascade="all,delete")

    def __repr__(self):
        return f"<Team {self.name}>"


class Player(db.Model):
    __tablename__ = "players"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    gamertag = db.Column(db.String(80))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))


class TournamentTeam(db.Model):
    __tablename__ = "tournament_teams"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    __table_args__ = (db.UniqueConstraint("tournament_id", "team_id", name="uq_tt"),)

    team = db.relationship("Team")


class Tournament(db.Model):
    __tablename__ = "tournaments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    game = db.Column(db.String(80), default="FIFA 24")
    size = db.Column(db.Integer, default=8)  # 4, 8, 16 ... potencia de 2
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teams = db.relationship(
        "TournamentTeam", backref="tournament", lazy=True, cascade="all,delete"
    )
    matches = db.relationship(
        "Match", backref="tournament", lazy=True, cascade="all,delete"
    )

    def __repr__(self):
        return f"<Tournament {self.name} ({self.size})>"


class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"))
    round = db.Column(db.Integer, nullable=False)  # 1 = primera ronda
    match_number = db.Column(db.Integer, nullable=False)  # dentro de la ronda

    team1_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    team2_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    score1 = db.Column(db.Integer)
    score2 = db.Column(db.Integer)

    winner_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))

    # Para enlazar avance de ronda: este partido alimenta al next_match en el slot 1 o 2
    next_match_id = db.Column(db.Integer, db.ForeignKey("matches.id"))
    next_match_slot = db.Column(db.Integer)  # 1 o 2

    team1 = db.relationship("Team", foreign_keys=[team1_id])
    team2 = db.relationship("Team", foreign_keys=[team2_id])
    winner_team = db.relationship("Team", foreign_keys=[winner_team_id])


# --------------------------------------
# Formularios
# --------------------------------------
class TournamentForm(FlaskForm):
    name = StringField("Nombre del torneo", validators=[DataRequired(), Length(max=160)])
    game = StringField("Juego", default="FIFA 24", validators=[Length(max=80)])
    size = SelectField(
        "Tamaño del torneo",
        choices=[("4", "4 equipos"), ("8", "8 equipos"), ("16", "16 equipos")],
        default="8",
    )
    submit = SubmitField("Crear torneo")


class TeamForm(FlaskForm):
    name = StringField("Nombre del equipo", validators=[DataRequired(), Length(max=120)])
    logo_url = StringField("Logo (URL)", validators=[Opt(), Length(max=512)])
    submit = SubmitField("Agregar equipo")


class MatchResultForm(FlaskForm):
    score1 = IntegerField("Goles Equipo 1", validators=[DataRequired(), NumberRange(min=0, max=99)])
    score2 = IntegerField("Goles Equipo 2", validators=[DataRequired(), NumberRange(min=0, max=99)])
    submit = SubmitField("Guardar resultado")


# --------------------------------------
# Utilidades de bracket
# --------------------------------------
def _ceil_log2(x: int) -> int:
    return math.ceil(math.log2(max(1, x)))


def generate_bracket(tournament: Tournament):
    """Genera un bracket de eliminación simple y crea los partidos enlazados.
    Asume que el torneo tiene exactamente `size` equipos inscritos.
    """
    # Limpiar partidos previos si existen
    for m in list(tournament.matches):
        db.session.delete(m)

    # Obtener equipos
    teams = [tt.team for tt in tournament.teams]
    if len(teams) != tournament.size:
        raise ValueError("Número de equipos no coincide con el tamaño del torneo")

    # Mezclar para aleatorizar llaves
    random.shuffle(teams)

    # Crear primera ronda
    total_rounds = _ceil_log2(tournament.size)
    matches_by_round: List[List[Match]] = []

    # Ronda 1
    round_matches = []
    for i in range(0, tournament.size, 2):
        m = Match(
            tournament=tournament,
            round=1,
            match_number=(i // 2) + 1,
            team1=teams[i],
            team2=teams[i + 1],
        )
        db.session.add(m)
        round_matches.append(m)
    matches_by_round.append(round_matches)

    # Rondas siguientes (solo estructura, sin equipos todavía)
    prev_round_count = len(round_matches)
    for r in range(2, total_rounds + 1):
        this_round = []
        for j in range(prev_round_count // 2):
            m = Match(tournament=tournament, round=r, match_number=j + 1)
            db.session.add(m)
            this_round.append(m)
        matches_by_round.append(this_round)
        prev_round_count = len(this_round)

    db.session.flush()  # Asegura IDs para enlazar

    # Enlazar partidos con su siguiente
    for r in range(total_rounds - 1):
        src_round = matches_by_round[r]
        dst_round = matches_by_round[r + 1]
        for k, src in enumerate(src_round):
            dst_index = k // 2
            slot = 1 if k % 2 == 0 else 2
            src.next_match_id = dst_round[dst_index].id
            src.next_match_slot = slot

    db.session.commit()


def propagate_winner(match: Match):
    """Calcula ganador y lo propaga al siguiente partido (si aplica)."""
    if match.score1 is None or match.score2 is None:
        return
    if match.team1_id is None or match.team2_id is None:
        return

    if match.score1 > match.score2:
        winner = match.team1
    elif match.score2 > match.score1:
        winner = match.team2
    else:
        # Empate: decidir por penales aleatorio para simplificar (o pedir desempate)
        winner = random.choice([match.team1, match.team2])

    match.winner_team = winner

    if match.next_match_id:
        next_match = Match.query.get(match.next_match_id)
        if next_match:
            if match.next_match_slot == 1:
                next_match.team1 = winner
            else:
                next_match.team2 = winner
            db.session.add(next_match)
    db.session.add(match)
    db.session.commit()


def tournament_bracket_data(t: Tournament):
    """Retorna estructura de rounds y matches para pintar bracket en frontend."""
    rounds = {}
    for m in t.matches:
        rounds.setdefault(m.round, []).append(m)
    # Ordenar por número de ronda y partido
    ordered = []
    for r in sorted(rounds.keys()):
        ordered.append(sorted(rounds[r], key=lambda m: m.match_number))

    def m_json(m: Match):
        return {
            "id": m.id,
            "round": m.round,
            "match_number": m.match_number,
            "team1": m.team1.name if m.team1 else None,
            "team2": m.team2.name if m.team2 else None,
            "score1": m.score1,
            "score2": m.score2,
            "winner": m.winner_team.name if m.winner_team else None,
        }

    return [[m_json(m) for m in row] for row in ordered]


# --------------------------------------
# Rutas
# --------------------------------------
@app.route("/")
def index():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template("index.html", tournaments=tournaments)


@app.route("/tournaments/new", methods=["GET", "POST"])
def tournaments_new():
    form = TournamentForm()
    if form.validate_on_submit():
        t = Tournament(
            name=form.name.data.strip(),
            game=form.game.data.strip() or "FIFA 24",
            size=int(form.size.data),
        )
        db.session.add(t)
        db.session.commit()
        flash("Torneo creado. Ahora agrega equipos.", "success")
        return redirect(url_for("tournament_teams", tournament_id=t.id))
    return render_template("tournaments_new.html", form=form)


@app.route("/tournaments/<int:tournament_id>")
def tournament_detail(tournament_id):
    t = Tournament.query.get_or_404(tournament_id)
    # ¿Hay ganador?
    champion: Optional[Team] = None
    if t.matches:
        last_round = max(m.round for m in t.matches)
        finals = [m for m in t.matches if m.round == last_round]
        if finals and finals[0].winner_team:
            champion = finals[0].winner_team
    return render_template(
        "tournaments_detail.html",
        tournament=t,
        bracket=tournament_bracket_data(t),
        champion=champion,
    )


@app.route("/tournaments/<int:tournament_id>/teams", methods=["GET", "POST"])
def tournament_teams(tournament_id):
    t = Tournament.query.get_or_404(tournament_id)
    form = TeamForm()
    if form.validate_on_submit():
        # Crear o reutilizar team por nombre
        team = Team.query.filter_by(name=form.name.data.strip()).first()
        if not team:
            team = Team(name=form.name.data.strip(), logo_url=form.logo_url.data or None)
            db.session.add(team)
            db.session.flush()

        # Asociar al torneo si no está
        exists = TournamentTeam.query.filter_by(tournament_id=t.id, team_id=team.id).first()
        if exists:
            flash("Ese equipo ya está en el torneo.", "warning")
        else:
            tt = TournamentTeam(tournament_id=t.id, team_id=team.id)
            db.session.add(tt)
            db.session.commit()
            flash("Equipo agregado al torneo.", "success")
        return redirect(url_for("tournament_teams", tournament_id=t.id))

    teams = [tt.team for tt in t.teams]
    can_generate = len(teams) == t.size and not t.matches
    return render_template(
        "tournaments_teams.html", tournament=t, teams=teams, form=form, can_generate=can_generate
    )


@app.route("/tournaments/<int:tournament_id>/generate_bracket", methods=["POST"])
def tournament_generate_bracket(tournament_id):
    t = Tournament.query.get_or_404(tournament_id)
    try:
        generate_bracket(t)
        flash("Bracket generado correctamente. ¡Que ruede el balón!", "success")
    except Exception as e:
        flash(f"No se pudo generar el bracket: {e}", "danger")
    return redirect(url_for("tournament_detail", tournament_id=t.id))


@app.route("/matches/<int:match_id>/edit", methods=["GET", "POST"])
def match_edit(match_id):
    m = Match.query.get_or_404(match_id)
    form = MatchResultForm()
    if request.method == "GET":
        if m.score1 is not None:
            form.score1.data = m.score1
        if m.score2 is not None:
            form.score2.data = m.score2

    if form.validate_on_submit():
        m.score1 = form.score1.data
        m.score2 = form.score2.data
        db.session.add(m)
        db.session.commit()
        propagate_winner(m)
        flash("Resultado guardado.", "success")
        return redirect(url_for("tournament_detail", tournament_id=m.tournament_id))

    return render_template("match_edit.html", match=m, form=form)


@app.route("/tournaments/<int:tournament_id>/bracket.json")
def tournament_bracket_json(tournament_id):
    t = Tournament.query.get_or_404(tournament_id)
    return jsonify({"tournament": t.name, "rounds": tournament_bracket_data(t)})


@app.route("/admin/seed")
def admin_seed():
    key = request.args.get("key", "dev")
    if key != os.getenv("SEED_KEY", "dev"):
        return "Unauthorized", 401

    # Crear torneo demo si no existe
    t = Tournament.query.filter_by(name="Copa Ultimate Team").first()
    if not t:
        t = Tournament(name="Copa Ultimate Team", game="FIFA 24", size=8)
        db.session.add(t)
        db.session.commit()

    # Equipos demo
    demo_teams = [
        ("Real Ballers", "https://avatars.githubusercontent.com/u/9919?s=200&v=4"),
        ("Pixel United", "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/26bd.svg"),
        ("Code FC", None),
        ("Dev Ninjas", None),
        ("AI Legends", None),
        ("Turbo Tactics", None),
        ("Python Pythons", None),
        ("JS Strikers", None),
    ]
    for name, logo in demo_teams:
        team = Team.query.filter_by(name=name).first()
        if not team:
            team = Team(name=name, logo_url=logo)
            db.session.add(team)
            db.session.flush()
        # Inscribir si falta y hay cupo
        if not TournamentTeam.query.filter_by(tournament_id=t.id, team_id=team.id).first():
            if len([tt for tt in t.teams]) < t.size:
                db.session.add(TournamentTeam(tournament_id=t.id, team_id=team.id))
    db.session.commit()

    if len([tt for tt in t.teams]) == t.size and not t.matches:
        generate_bracket(t)

    return redirect(url_for("tournament_detail", tournament_id=t.id))


# --------------------------------------
# Inicialización de DB
# --------------------------------------
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
