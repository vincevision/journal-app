import os
import json
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_file, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from pdf_generator import generate_trade_pdf
from ai_analysis import get_ai_analysis

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trades.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join('static', 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)


# ──────────────────────────────────────────────
# Database Models
# ──────────────────────────────────────────────

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Trade Classification
    pair = db.Column(db.String(20), nullable=False)  # e.g., EURUSD, BTCUSD
    trade_direction = db.Column(db.String(10), nullable=False)  # Long / Short
    trade_outcome = db.Column(db.String(20), nullable=False)  # Win / Loss / Missed / Breakeven
    trade_date = db.Column(db.String(20), nullable=False)
    session = db.Column(db.String(20))  # London / NY / Asian / Overlap

    # SMC Concepts Spotted
    htf_bias = db.Column(db.String(20))  # Bullish / Bearish
    htf_timeframe = db.Column(db.String(10))  # 4H / 1H / Daily / Weekly
    htf_structure = db.Column(db.String(50))  # BoS / CHoCH
    poi_type = db.Column(db.String(50))  # Supply Zone / Demand Zone / OB / FVG / Breaker
    poi_timeframe = db.Column(db.String(10))

    # LTF Confirmation
    ltf_timeframe = db.Column(db.String(10))  # 15M / 5M / 1M
    ltf_trigger = db.Column(db.String(100))  # CHoCH + OB / CHoCH + FVG / Direct OB tap
    liquidity_sweep = db.Column(db.Boolean, default=False)
    liquidity_type = db.Column(db.String(100))  # EQH/EQL / BSL / SSL / Trendline

    # Refined Entry
    refined_entry = db.Column(db.Boolean, default=False)
    refined_poi = db.Column(db.String(100))

    # Risk Management
    entry_price = db.Column(db.Float)
    sl_price = db.Column(db.Float)
    tp1_price = db.Column(db.Float)
    tp2_price = db.Column(db.Float)
    risk_reward = db.Column(db.Float)
    position_size = db.Column(db.Float)
    pnl = db.Column(db.Float)
    pnl_percent = db.Column(db.Float)

    # Notes
    pre_trade_notes = db.Column(db.Text)
    post_trade_notes = db.Column(db.Text)
    mistakes = db.Column(db.Text)
    lessons = db.Column(db.Text)
    emotion_before = db.Column(db.String(30))
    emotion_during = db.Column(db.String(30))
    emotion_after = db.Column(db.String(30))

    # AI Analysis
    ai_analysis = db.Column(db.Text)

    # Screenshots
    screenshots = db.relationship('Screenshot', backref='trade', lazy=True,
                                  cascade='all, delete-orphan')

    # PDF path
    pdf_path = db.Column(db.String(500))


class Screenshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trade.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    label = db.Column(db.String(100))  # HTF Context / LTF Entry / Result / etc.
    timeframe = db.Column(db.String(10))
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.route('/')
def dashboard():
    trades = Trade.query.order_by(Trade.created_at.desc()).all()
    stats = calculate_stats(trades)
    return render_template('dashboard.html', trades=trades, stats=stats)


def calculate_stats(trades):
    total = len(trades)
    wins = sum(1 for t in trades if t.trade_outcome == 'Win')
    losses = sum(1 for t in trades if t.trade_outcome == 'Loss')
    missed = sum(1 for t in trades if t.trade_outcome == 'Missed')
    breakeven = sum(1 for t in trades if t.trade_outcome == 'Breakeven')
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
    avg_rr = 0
    rr_trades = [t for t in trades if t.risk_reward is not None and t.trade_outcome == 'Win']
    if rr_trades:
        avg_rr = sum(t.risk_reward for t in rr_trades) / len(rr_trades)

    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'missed': missed,
        'breakeven': breakeven,
        'win_rate': round(win_rate, 1),
        'total_pnl': round(total_pnl, 2),
        'avg_rr': round(avg_rr, 2)
    }


@app.route('/new-trade', methods=['GET', 'POST'])
def new_trade():
    if request.method == 'POST':
        trade = Trade(
            pair=request.form.get('pair', '').upper(),
            trade_direction=request.form.get('trade_direction'),
            trade_outcome=request.form.get('trade_outcome'),
            trade_date=request.form.get('trade_date'),
            session=request.form.get('session'),
            htf_bias=request.form.get('htf_bias'),
            htf_timeframe=request.form.get('htf_timeframe'),
            htf_structure=request.form.get('htf_structure'),
            poi_type=request.form.get('poi_type'),
            poi_timeframe=request.form.get('poi_timeframe'),
            ltf_timeframe=request.form.get('ltf_timeframe'),
            ltf_trigger=request.form.get('ltf_trigger'),
            liquidity_sweep=request.form.get('liquidity_sweep') == 'on',
            liquidity_type=request.form.get('liquidity_type'),
            refined_entry=request.form.get('refined_entry') == 'on',
            refined_poi=request.form.get('refined_poi'),
            entry_price=float(request.form.get('entry_price') or 0) or None,
            sl_price=float(request.form.get('sl_price') or 0) or None,
            tp1_price=float(request.form.get('tp1_price') or 0) or None,
            tp2_price=float(request.form.get('tp2_price') or 0) or None,
            risk_reward=float(request.form.get('risk_reward') or 0) or None,
            position_size=float(request.form.get('position_size') or 0) or None,
            pnl=float(request.form.get('pnl') or 0) or None,
            pnl_percent=float(request.form.get('pnl_percent') or 0) or None,
            pre_trade_notes=request.form.get('pre_trade_notes'),
            post_trade_notes=request.form.get('post_trade_notes'),
            mistakes=request.form.get('mistakes'),
            lessons=request.form.get('lessons'),
            emotion_before=request.form.get('emotion_before'),
            emotion_during=request.form.get('emotion_during'),
            emotion_after=request.form.get('emotion_after'),
        )

        db.session.add(trade)
        db.session.commit()

        # Handle file uploads
        files = request.files.getlist('screenshots')
        labels = request.form.getlist('screenshot_labels')
        timeframes = request.form.getlist('screenshot_timeframes')
        descriptions = request.form.getlist('screenshot_descriptions')

        trade_folder = os.path.join(app.config['UPLOAD_FOLDER'], trade.trade_id)
        os.makedirs(trade_folder, exist_ok=True)

        for i, file in enumerate(files):
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                safe_name = f"{i+1}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(trade_folder, safe_name)
                file.save(filepath)

                screenshot = Screenshot(
                    trade_id=trade.id,
                    filename=safe_name,
                    filepath=filepath,
                    label=labels[i] if i < len(labels) else '',
                    timeframe=timeframes[i] if i < len(timeframes) else '',
                    description=descriptions[i] if i < len(descriptions) else '',
                    sort_order=i
                )
                db.session.add(screenshot)

        db.session.commit()
        flash('Trade saved! Now generate the AI analysis and PDF.', 'success')
        return redirect(url_for('view_trade', trade_id=trade.trade_id))

    return render_template('new_trade.html')


@app.route('/trade/<trade_id>')
def view_trade(trade_id):
    trade = Trade.query.filter_by(trade_id=trade_id).first_or_404()
    return render_template('view_trade.html', trade=trade)


@app.route('/trade/<trade_id>/edit', methods=['GET', 'POST'])
def edit_trade(trade_id):
    trade = Trade.query.filter_by(trade_id=trade_id).first_or_404()

    if request.method == 'POST':
        trade.pair = request.form.get('pair', '').upper()
        trade.trade_direction = request.form.get('trade_direction')
        trade.trade_outcome = request.form.get('trade_outcome')
        trade.trade_date = request.form.get('trade_date')
        trade.session = request.form.get('session')
        trade.htf_bias = request.form.get('htf_bias')
        trade.htf_timeframe = request.form.get('htf_timeframe')
        trade.htf_structure = request.form.get('htf_structure')
        trade.poi_type = request.form.get('poi_type')
        trade.poi_timeframe = request.form.get('poi_timeframe')
        trade.ltf_timeframe = request.form.get('ltf_timeframe')
        trade.ltf_trigger = request.form.get('ltf_trigger')
        trade.liquidity_sweep = request.form.get('liquidity_sweep') == 'on'
        trade.liquidity_type = request.form.get('liquidity_type')
        trade.refined_entry = request.form.get('refined_entry') == 'on'
        trade.refined_poi = request.form.get('refined_poi')
        trade.entry_price = float(request.form.get('entry_price') or 0) or None
        trade.sl_price = float(request.form.get('sl_price') or 0) or None
        trade.tp1_price = float(request.form.get('tp1_price') or 0) or None
        trade.tp2_price = float(request.form.get('tp2_price') or 0) or None
        trade.risk_reward = float(request.form.get('risk_reward') or 0) or None
        trade.position_size = float(request.form.get('position_size') or 0) or None
        trade.pnl = float(request.form.get('pnl') or 0) or None
        trade.pnl_percent = float(request.form.get('pnl_percent') or 0) or None
        trade.pre_trade_notes = request.form.get('pre_trade_notes')
        trade.post_trade_notes = request.form.get('post_trade_notes')
        trade.mistakes = request.form.get('mistakes')
        trade.lessons = request.form.get('lessons')
        trade.emotion_before = request.form.get('emotion_before')
        trade.emotion_during = request.form.get('emotion_during')
        trade.emotion_after = request.form.get('emotion_after')

        # Handle new screenshots
        files = request.files.getlist('screenshots')
        labels = request.form.getlist('screenshot_labels')
        timeframes = request.form.getlist('screenshot_timeframes')
        descriptions = request.form.getlist('screenshot_descriptions')

        existing_count = len(trade.screenshots)
        trade_folder = os.path.join(app.config['UPLOAD_FOLDER'], trade.trade_id)
        os.makedirs(trade_folder, exist_ok=True)

        for i, file in enumerate(files):
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                safe_name = f"{existing_count + i + 1}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(trade_folder, safe_name)
                file.save(filepath)

                screenshot = Screenshot(
                    trade_id=trade.id,
                    filename=safe_name,
                    filepath=filepath,
                    label=labels[i] if i < len(labels) else '',
                    timeframe=timeframes[i] if i < len(timeframes) else '',
                    description=descriptions[i] if i < len(descriptions) else '',
                    sort_order=existing_count + i
                )
                db.session.add(screenshot)

        db.session.commit()
        flash('Trade updated successfully!', 'success')
        return redirect(url_for('view_trade', trade_id=trade.trade_id))

    return render_template('edit_trade.html', trade=trade)


@app.route('/trade/<trade_id>/delete', methods=['POST'])
def delete_trade(trade_id):
    trade = Trade.query.filter_by(trade_id=trade_id).first_or_404()

    # Delete uploaded files
    trade_folder = os.path.join(app.config['UPLOAD_FOLDER'], trade.trade_id)
    if os.path.exists(trade_folder):
        import shutil
        shutil.rmtree(trade_folder)

    # Delete PDF if exists
    if trade.pdf_path and os.path.exists(trade.pdf_path):
        os.remove(trade.pdf_path)

    db.session.delete(trade)
    db.session.commit()
    flash('Trade deleted.', 'info')
    return redirect(url_for('dashboard'))


@app.route('/trade/<trade_id>/delete-screenshot/<int:screenshot_id>', methods=['POST'])
def delete_screenshot(trade_id, screenshot_id):
    screenshot = Screenshot.query.get_or_404(screenshot_id)
    if os.path.exists(screenshot.filepath):
        os.remove(screenshot.filepath)
    db.session.delete(screenshot)
    db.session.commit()
    flash('Screenshot removed.', 'info')
    return redirect(url_for('edit_trade', trade_id=trade_id))


@app.route('/trade/<trade_id>/analyze', methods=['POST'])
def analyze_trade(trade_id):
    trade = Trade.query.filter_by(trade_id=trade_id).first_or_404()

    groq_key = request.form.get('groq_api_key', '').strip()
    if not groq_key:
        groq_key = os.environ.get('GROQ_API_KEY', '')

    if not groq_key:
        flash('Please provide a Groq API key.', 'error')
        return redirect(url_for('view_trade', trade_id=trade_id))

    trade_data = {
        'pair': trade.pair,
        'direction': trade.trade_direction,
        'outcome': trade.trade_outcome,
        'date': trade.trade_date,
        'session': trade.session,
        'htf_bias': trade.htf_bias,
        'htf_timeframe': trade.htf_timeframe,
        'htf_structure': trade.htf_structure,
        'poi_type': trade.poi_type,
        'poi_timeframe': trade.poi_timeframe,
        'ltf_timeframe': trade.ltf_timeframe,
        'ltf_trigger': trade.ltf_trigger,
        'liquidity_sweep': trade.liquidity_sweep,
        'liquidity_type': trade.liquidity_type,
        'refined_entry': trade.refined_entry,
        'refined_poi': trade.refined_poi,
        'entry_price': trade.entry_price,
        'sl_price': trade.sl_price,
        'tp1_price': trade.tp1_price,
        'tp2_price': trade.tp2_price,
        'risk_reward': trade.risk_reward,
        'pnl': trade.pnl,
        'pre_trade_notes': trade.pre_trade_notes,
        'post_trade_notes': trade.post_trade_notes,
        'mistakes': trade.mistakes,
        'lessons': trade.lessons,
        'emotion_before': trade.emotion_before,
        'emotion_during': trade.emotion_during,
        'emotion_after': trade.emotion_after,
    }

    try:
        analysis = get_ai_analysis(trade_data, groq_key)
        trade.ai_analysis = analysis
        db.session.commit()
        flash('AI analysis generated successfully!', 'success')
    except Exception as e:
        flash(f'AI analysis failed: {str(e)}', 'error')

    return redirect(url_for('view_trade', trade_id=trade_id))


@app.route('/trade/<trade_id>/generate-pdf', methods=['POST'])
def generate_pdf(trade_id):
    trade = Trade.query.filter_by(trade_id=trade_id).first_or_404()

    # Determine output folder based on outcome
    outcome_map = {
        'Win': 'winning_trades',
        'Loss': 'losing_trades',
        'Missed': 'missed_trades',
        'Breakeven': 'winning_trades'
    }
    outcome_folder = outcome_map.get(trade.trade_outcome, 'winning_trades')
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], outcome_folder)
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{trade.pair}_{trade.trade_date}_{trade.trade_id[:8]}.pdf"
    pdf_path = os.path.join(output_dir, filename)

    screenshots_data = []
    for s in sorted(trade.screenshots, key=lambda x: x.sort_order):
        screenshots_data.append({
            'filepath': s.filepath,
            'label': s.label,
            'timeframe': s.timeframe,
            'description': s.description
        })

    trade_data = {
        'trade_id': trade.trade_id,
        'pair': trade.pair,
        'direction': trade.trade_direction,
        'outcome': trade.trade_outcome,
        'date': trade.trade_date,
        'session': trade.session,
        'htf_bias': trade.htf_bias,
        'htf_timeframe': trade.htf_timeframe,
        'htf_structure': trade.htf_structure,
        'poi_type': trade.poi_type,
        'poi_timeframe': trade.poi_timeframe,
        'ltf_timeframe': trade.ltf_timeframe,
        'ltf_trigger': trade.ltf_trigger,
        'liquidity_sweep': trade.liquidity_sweep,
        'liquidity_type': trade.liquidity_type,
        'refined_entry': trade.refined_entry,
        'refined_poi': trade.refined_poi,
        'entry_price': trade.entry_price,
        'sl_price': trade.sl_price,
        'tp1_price': trade.tp1_price,
        'tp2_price': trade.tp2_price,
        'risk_reward': trade.risk_reward,
        'position_size': trade.position_size,
        'pnl': trade.pnl,
        'pnl_percent': trade.pnl_percent,
        'pre_trade_notes': trade.pre_trade_notes,
        'post_trade_notes': trade.post_trade_notes,
        'mistakes': trade.mistakes,
        'lessons': trade.lessons,
        'emotion_before': trade.emotion_before,
        'emotion_during': trade.emotion_during,
        'emotion_after': trade.emotion_after,
        'ai_analysis': trade.ai_analysis,
        'screenshots': screenshots_data
    }

    try:
        generate_trade_pdf(trade_data, pdf_path)
        trade.pdf_path = pdf_path
        db.session.commit()
        flash(f'PDF generated and saved to {outcome_folder}/', 'success')
    except Exception as e:
        flash(f'PDF generation failed: {str(e)}', 'error')

    return redirect(url_for('view_trade', trade_id=trade_id))


@app.route('/trade/<trade_id>/download-pdf')
def download_pdf(trade_id):
    trade = Trade.query.filter_by(trade_id=trade_id).first_or_404()
    if trade.pdf_path and os.path.exists(trade.pdf_path):
        return send_file(trade.pdf_path, as_attachment=True)
    flash('PDF not found. Generate it first.', 'error')
    return redirect(url_for('view_trade', trade_id=trade_id))


@app.route('/trades/<category>')
def trades_by_category(category):
    category_map = {
        'winning': 'Win',
        'losing': 'Loss',
        'missed': 'Missed',
        'breakeven': 'Breakeven'
    }
    outcome = category_map.get(category)
    if not outcome:
        flash('Invalid category.', 'error')
        return redirect(url_for('dashboard'))

    trades = Trade.query.filter_by(trade_outcome=outcome).order_by(
        Trade.created_at.desc()).all()
    return render_template('category.html', trades=trades,
                           category=category.title(), outcome=outcome)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    config_path = 'config.json'
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)

    if request.method == 'POST':
        config['groq_api_key'] = request.form.get('groq_api_key', '')
        config['default_session'] = request.form.get('default_session', '')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        if config['groq_api_key']:
            os.environ['GROQ_API_KEY'] = config['groq_api_key']
        flash('Settings saved!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', config=config)


# ──────────────────────────────────────────────
# Init
# ──────────────────────────────────────────────

with app.app_context():
    db.create_all()

# Load saved API key on startup
config_path = 'config.json'
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
        if config.get('groq_api_key'):
            os.environ['GROQ_API_KEY'] = config['groq_api_key']

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)