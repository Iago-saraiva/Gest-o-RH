from flask import Flask, render_template, request, redirect, url_for, send_file
import os
import pandas as pd
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}

# Dados de exemplo
departments = {
    'TI': {
        'cargos': [
            {'nome': 'Desenvolvedor Python', 
             'atividades': 'Desenvolvimento de aplicações web, manutenção de sistemas',
             'competencias': 'Python, Flask, Django, HTML/CSS',
             'lideranca': 'João Silva - joao.silva@empresa.com'},
            {'nome': 'Analista de Dados',
             'atividades': 'Análise de dados, criação de relatórios',
             'competencias': 'Python, Pandas, SQL, Power BI',
             'lideranca': 'Maria Souza - maria.souza@empresa.com'}
        ]
    },
    'RH': {
        'cargos': [
            {'nome': 'Analista de RH',
             'atividades': 'Recrutamento, treinamento, avaliação de desempenho',
             'competencias': 'Comunicação, gestão de pessoas, conhecimento em leis trabalhistas',
             'lideranca': 'Carlos Oliveira - carlos.oliveira@empresa.com'}
        ]
    }
}

feedback_responses = []
performance_data = []
talent_data = []

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
            

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def home():
    return render_template('home.html')

# 1. Avaliação de Desempenho
@app.route('/avaliacao-desempenho')
def avaliacao_desempenho():
    return render_template('avaliacao.html')

@app.route('/formulario-autoavaliacao')
def formulario_autoavaliacao():
    return render_template('form_autoavaliacao.html')

@app.route('/formulario-avaliacao-gestor')
def formulario_avaliacao_gestor():
    return render_template('form_gestor.html')

@app.route('/submit-avaliacao', methods=['POST'])
def submit_avaliacao():
    data = request.form.to_dict()
    performance_data.append(data)
    return redirect(url_for('avaliacao_desempenho'))

@app.route('/planilha-resultados')
def planilha_resultados():
    # Criar DataFrame com os dados
    df = pd.DataFrame(performance_data)
    
    # Salvar temporariamente
    filename = 'resultados_avaliacao.xlsx'
    df.to_excel(filename, index=False)
    
    return send_file(filename, as_attachment=True)

# 2. Cultura de Feedback e Escuta Ativa
@app.route('/feedback')
def feedback():
    return render_template('feedback.html', responses=feedback_responses)

@app.route('/formulario-feedback', methods=['GET', 'POST'])
def formulario_feedback():
    if request.method == 'POST':
        response = {
            'tipo': request.form.get('tipo'),
            'mensagem': request.form.get('mensagem'),
            'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'anonimo': 'anonimo' in request.form
        }
        feedback_responses.append(response)
        return redirect(url_for('feedback'))
    return render_template('form_feedback.html')

@app.route('/plano-acao-feedback')
def plano_acao_feedback():
    # Agrupar feedbacks por tema (simplificado)
    temas = {}
    for fb in feedback_responses:
        tema = fb['mensagem'][:30] + '...' if len(fb['mensagem']) > 30 else fb['mensagem']
        if tema not in temas:
            temas[tema] = 0
        temas[tema] += 1
    
    return render_template('plano_acao.html', temas=temas)

# 3. Descrição de Atividades por Cargo
@app.route('/descricao-cargos')
def descricao_cargos():
    return render_template('cargos.html', departments=departments)

@app.route('/setor/<dept>')
def setor_detail(dept):
    if dept not in departments:
        return redirect(url_for('descricao_cargos'))
    return render_template('setor_detail.html', dept=dept, info=departments[dept])

# 4. Mapeamento de Talentos e Aspirações
@app.route('/mapeamento-talentos')
def mapeamento_talentos():
    return render_template('talentos.html', talentos=talent_data)

@app.route('/formulario-talento', methods=['GET', 'POST'])
def formulario_talento():
    if request.method == 'POST':
        data = request.form.to_dict()
        data['data'] = datetime.now().strftime('%d/%m/%Y')
        talent_data.append(data)
        return redirect(url_for('mapeamento_talentos'))
    return render_template('form_talento.html')

# 5. Agenda de Ações do RH
@app.route('/agenda-rh')
def agenda_rh():
    # Datas de exemplo para o semestre
    hoje = datetime.now()
    eventos = [
        {'tipo': 'Ciclo de Avaliação', 'data': hoje + timedelta(days=15), 'descricao': 'Avaliação de desempenho semestral'},
        {'tipo': 'Feedback', 'data': hoje + timedelta(days=30), 'descricao': 'Rodada de feedback com equipes'},
        {'tipo': 'Escuta Ativa', 'data': hoje + timedelta(days=45), 'descricao': 'Sessões de escuta ativa por departamento'},
        {'tipo': 'Happy Hour', 'data': hoje + timedelta(days=60), 'descricao': 'Happy Hour de integração'},
        {'tipo': 'Treinamento', 'data': hoje + timedelta(days=75), 'descricao': 'Treinamento em soft skills'},
    ]
    
    # Ordenar por data
    eventos.sort(key=lambda x: x['data'])
    
    return render_template('agenda.html', eventos=eventos)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
