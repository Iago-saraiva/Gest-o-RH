from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os
import pandas as pd
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()  # Only for local development

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')  # Required for session management

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://gestao_user:hwH68FbFPpWziorrjckR1baP2smq62Bx@dpg-d11hm9ogjchc7381knh0-a.oregon-postgres.render.com:5432/gestao_pessoas_96pj'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    anonimo = db.Column(db.Boolean, default=False)

class Avaliacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'auto' or 'gestor'
    nome = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(100))
    respostas = db.Column(db.JSON)  # Stores all responses as JSON
    data = db.Column(db.DateTime, default=datetime.utcnow)

class Talento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(50), nullable=False)
    cargo_atual = db.Column(db.String(100))
    habilidades = db.Column(db.Text)
    interesses = db.Column(db.Text)
    aspiracoes = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)

# Sample data
departments = {
    'TI': {
        'cargos': [
            {
                'nome': 'Desenvolvedor Python', 
                'atividades': 'Desenvolvimento de aplicações web, manutenção de sistemas',
                'competencias': 'Python, Flask, Django, HTML/CSS',
                'lideranca': 'João Silva - joao.silva@empresa.com'
            },
            {
                'nome': 'Analista de Dados',
                'atividades': 'Análise de dados, criação de relatórios',
                'competencias': 'Python, Pandas, SQL, Power BI',
                'lideranca': 'Maria Souza - maria.souza@empresa.com'
            }
        ]
    },
    'RH': {
        'cargos': [
            {
                'nome': 'Analista de RH',
                'atividades': 'Recrutamento, treinamento, avaliação de desempenho',
                'competencias': 'Comunicação, gestão de pessoas, conhecimento em leis trabalhistas',
                'lideranca': 'Carlos Oliveira - carlos.oliveira@empresa.com'
            }
        ]
    }
}

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Main routes
@app.route('/')
def home():
    return render_template('home.html')

# 1. Performance Evaluation
@app.route('/avaliacao-desempenho')
def avaliacao_desempenho():
    avaliacoes = Avaliacao.query.order_by(Avaliacao.data.desc()).all()
    return render_template('avaliacao.html', avaliacao=avaliacoes)

@app.route('/formulario-autoavaliacao')
def formulario_autoavaliacao():
    return render_template('form_autoavaliacao.html')

@app.route('/formulario-avaliacao-gestor')
def formulario_avaliacao_gestor():
    return render_template('form_gestor.html')

@app.route('/submit-avaliacao', methods=['POST'])
def submit_avaliacao():
    if request.method == 'POST':
        try:
            # Convert form data to dict, excluding CSRF token if present
            respostas = {k: v for k, v in request.form.items() if k != 'csrf_token'}
            
            nova_avaliacao = Avaliacao(
                tipo=request.form.get('tipo', 'auto'),
                nome=request.form.get('nome', ''),
                cargo=request.form.get('cargo', ''),
                respostas=respostas,
                data=datetime.utcnow()
            )
            
            db.session.add(nova_avaliacao)
            db.session.commit()
            flash('Avaliação enviada com sucesso!', 'success')
            return redirect(url_for('avaliacao_desempenho'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao enviar avaliação: {str(e)}', 'danger')
            return redirect(url_for('formulario_autoavaliacao'))
    return redirect(url_for('avaliacao_desempenho'))

@app.route('/planilha-resultados')
def planilha_resultados():
    try:
        avaliacoes = Avaliacao.query.all()
        
        # Prepare data for Excel
        data = []
        for av in avaliacoes:
            row = {
                'Tipo': av.tipo,
                'Nome': av.nome,
                'Cargo': av.cargo,
                'Data': av.data.strftime('%d/%m/%Y %H:%M'),
            }
            # Add all responses from JSON
            if av.respostas and isinstance(av.respostas, dict):
                for key, value in av.respostas.items():
                    if key not in ['tipo', 'nome', 'cargo']:  # Skip already included fields
                        row[key] = value
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Save to Excel
        filename = 'resultados_avaliacao.xlsx'
        df.to_excel(filename, index=False, engine='openpyxl')
        
        return send_file(
            filename,
            as_attachment=True,
            download_name='resultados_avaliacao.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Erro ao gerar planilha: {str(e)}', 'danger')
        return redirect(url_for('avaliacao_desempenho'))

# 2. Feedback Culture
@app.route('/feedback')
def feedback():
    feedbacks = Feedback.query.order_by(Feedback.data.desc()).all()
    return render_template('feedback.html', feedbacks=feedbacks)

@app.route('/formulario-feedback', methods=['GET', 'POST'])
def formulario_feedback():
    if request.method == 'POST':
        try:
            novo_feedback = Feedback(
                tipo=request.form.get('tipo'),
                mensagem=request.form.get('mensagem', '').strip(),
                anonimo=request.form.get('anonimo', 'off') == 'on',
                data=datetime.utcnow()
            )
            
            if not novo_feedback.mensagem:
                flash('A mensagem de feedback não pode estar vazia', 'warning')
                return render_template('form_feedback.html')
                
            db.session.add(novo_feedback)
            db.session.commit()
            flash('Feedback enviado com sucesso!', 'success')
            return redirect(url_for('feedback'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao enviar feedback: {str(e)}', 'danger')
    
    return render_template('form_feedback.html')

@app.route('/plano-acao-feedback')
def plano_acao_feedback():
    feedbacks = Feedback.query.order_by(Feedback.data.desc()).all()
    
    # Initialize a simpler structure for counting feedback types
    feedback_counts = {}
    example_messages = {}
    
    for fb in feedbacks:
        if fb.tipo not in feedback_counts:
            feedback_counts[fb.tipo] = 0
            example_messages[fb.tipo] = []
        
        feedback_counts[fb.tipo] += 1
        
        # Keep max 3 example messages per type
        if len(example_messages[fb.tipo]) < 3:
            example_messages[fb.tipo].append(
                fb.mensagem[:100] + '...' if len(fb.mensagem) > 100 else fb.mensagem
            )
    
    # Calculate total feedbacks
    total_feedbacks = sum(feedback_counts.values())
    
    # Prepare data for template
    feedback_data = [
        {
            'tipo': tipo,
            'count': count,
            'examples': example_messages[tipo]
        }
        for tipo, count in feedback_counts.items()
    ]
    
    return render_template(
        'plano_acao.html',
        feedback_data=feedback_data,
        total_feedbacks=total_feedbacks
    )

# 3. Job Descriptions
@app.route('/descricao-cargos')
def descricao_cargos():
    return render_template('cargos.html', departments=departments)

@app.route('/setor/<dept>')
def setor_detail(dept):
    if dept not in departments:
        flash('Departamento não encontrado', 'warning')
        return redirect(url_for('descricao_cargos'))
    return render_template('setor_detail.html', dept=dept, info=departments[dept])

# 4. Talent Mapping
@app.route('/mapeamento-talentos')
def mapeamento_talentos():
    talentos = Talento.query.order_by(Talento.data.desc()).all()
    return render_template('talentos.html', talentos=talentos)

@app.route('/formulario-talento', methods=['GET', 'POST'])
def formulario_talento():
    if request.method == 'POST':
        try:
            novo_talento = Talento(
                nome=request.form.get('nome', '').strip(),
                area=request.form.get('area', '').strip(),
                cargo_atual=request.form.get('cargo_atual', '').strip(),
                habilidades=request.form.get('habilidades', '').strip(),
                interesses=request.form.get('interesses', '').strip(),
                aspiracoes=request.form.get('aspiracoes', '').strip(),
                data=datetime.utcnow()
            )
            
            if not novo_talento.nome or not novo_talento.area:
                flash('Nome e área são campos obrigatórios', 'warning')
                return render_template('form_talento.html')
                
            db.session.add(novo_talento)
            db.session.commit()
            flash('Informações de talento salvas com sucesso!', 'success')
            return redirect(url_for('mapeamento_talentos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar talento: {str(e)}', 'danger')
    
    return render_template('form_talento.html')

# 5. HR Agenda
@app.route('/agenda-rh')
def agenda_rh():
    hoje = datetime.utcnow()
    eventos = [
        {
            'tipo': 'Ciclo de Avaliação',
            'data': hoje + timedelta(days=15),
            'descricao': 'Avaliação de desempenho semestral',
            'responsavel': 'Equipe de RH'
        },
        {
            'tipo': 'Feedback',
            'data': hoje + timedelta(days=30),
            'descricao': 'Rodada de feedback com equipes',
            'responsavel': 'Líderes de equipe'
        },
        {
            'tipo': 'Escuta Ativa',
            'data': hoje + timedelta(days=45),
            'descricao': 'Sessões de escuta ativa por departamento',
            'responsavel': 'Equipe de RH'
        },
        {
            'tipo': 'Happy Hour',
            'data': hoje + timedelta(days=60),
            'descricao': 'Happy Hour de integração',
            'responsavel': 'Comitê de eventos'
        },
        {
            'tipo': 'Treinamento',
            'data': hoje + timedelta(days=75),
            'descricao': 'Treinamento em soft skills',
            'responsavel': 'Equipe de T&D'
        },
    ]
    
    eventos.sort(key=lambda x: x['data'])
    
    # Format dates for display
    for evento in eventos:
        evento['data_formatada'] = evento['data'].strftime('%d/%m/%Y')
    
    return render_template('agenda.html', eventos=eventos)

# Error handlers
@app.errorhandler(400)
def bad_request_error(error):
    return render_template('400.html'), 400

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')