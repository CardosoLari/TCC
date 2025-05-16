
from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "segredo_super_secreto"

# DataFrame de usuários em memória
df_usuarios = pd.DataFrame(columns=[
    "login", "senha", "cidade", "estado", "regiao", "telefone", "carros"
])

# Carregar histórico de manutenções (se existir) ou criar vazio
if os.path.exists("historico_manutencao.xlsx"):
    df_manutenções = pd.read_excel("historico_manutencao.xlsx")
else:
    df_manutenções = pd.DataFrame(columns=[
        "Usuário", "Data", "Carro", "Notificar", "Tipo de Manutenção",
        "Próxima Manutenção", "Ação", "Peça", "Custo",
        "Técnico Responsável", "Descrição", "Anexo"
    ])

# Carregar os dados do Excel para um DataFrame
df = pd.read_excel("carro.xlsx")  # Substitua pelo nome do seu arquivo

# Converter para uma lista de dicionários
carros = df.to_dict(orient="records")

Dicas = pd.read_excel("Dicas.xlsx")  # Substitua pelo nome do seu arquivo

# Converter para uma lista de dicionários
df_Dicas = Dicas.to_dict(orient="records")

Reclamações = pd.read_excel("Relcamações.xlsx")  # Substitua pelo nome do seu arquivo

# Converter para uma lista de dicionários
df_Reclamações = Reclamações.to_dict(orient="records")

Checklist = pd.read_excel("Checklist.xlsx")  # Substitua pelo nome do seu arquivo

# Converter para uma lista de dicionários
df_Checklist = Checklist.to_dict(orient="records")

# Carregar os dados do Excel para um DataFrame
df_cronograma = pd.read_excel("CronogramaManutenção.xlsx")  # Substitua pelo nome do seu arquivo

# Converter para uma lista de dicionários
manutenção_cronograma = df_cronograma.to_dict(orient="records")

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/health")
def health_check():
    """Rota para health check do Azure"""
    return "OK", 200

@app.route("/robots933456.txt")
def robots_txt():
    """Rota para verificação do Azure"""
    return "OK", 200

@app.route('/portifólio')
def portifólio():
    return render_template('portifólio.html', carros=carros)

@app.route("/api/carros")
def get_carros():
    return jsonify(carros)

@app.route('/detalhes/<int:carro_id>')
def detalhes_carro(carro_id):
    carro = next((c for c in carros if c['Id'] == carro_id), None)
    if carro:
        session['carro_selecionado'] = carro['Title']
        session['carro_id'] = carro_id  # Armazenando o ID na sessão
        return render_template('EscolhaCarro.html', carro=carro)
    return "Carro não encontrado", 404

@app.route('/verificar_login/<destino>')
def verificar_login(destino):
    if "usuario" not in session:
        flash("Você precisa estar logado.")
        return redirect(url_for("login"))
    return redirect(url_for(destino))

@app.route("/login", methods=["GET", "POST"])
def login():
    global df_usuarios
    if request.method == "POST":
        login_user = request.form["login"]
        senha = request.form["senha"]
        usuario = df_usuarios[df_usuarios["login"] == login_user]
        print(df_usuarios)

        if not usuario.empty and check_password_hash(usuario.iloc[0]["senha"], senha):
            session["usuario"] = login_user
            
            return redirect(url_for("portifólio"))
        else:
            flash("Login ou senha inválidos.")
    return render_template("login.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    global df_usuarios
    if request.method == "POST":
        login = request.form["login"]
        senha = request.form["senha"]
        confirmar = request.form["confirmar"]
        cidade = request.form["cidade"]
        estado = request.form["estado"]
        regiao = request.form["regiao"]
        telefone = request.form["telefone"]

        # Verificar se as senhas coincidem
        if senha != confirmar:
            flash("Senhas não coincidem!")
            return redirect(url_for("cadastro"))

        # Verificar se o login já existe
        if login in df_usuarios["login"].values:
            flash("Login já existente.")
            return redirect(url_for("cadastro"))

        # Hash da senha
        senha_hash = generate_password_hash(senha)

        # Obter os carros selecionados
        carros_usuario = request.form.getlist("carros[]")

        # Adicionar novo usuário ao DataFrame
        novo_usuario = {
            "login": login,
            "senha": senha_hash,
            "cidade": cidade,
            "estado": estado,
            "regiao": regiao,
            "telefone": telefone,
            "carros": ", ".join(carros_usuario)  # Guardar como string separada por vírgulas
        }

        df_usuarios = pd.concat([df_usuarios, pd.DataFrame([novo_usuario])], ignore_index=True)

        # Salvar os dados em um arquivo (opcional: use CSV ou DB em produção)
        df_usuarios.to_excel("usuarios.xlsx", index=False)

        flash("Cadastro realizado com sucesso. Faça login!")
        return redirect(url_for("login"))

    return render_template("cadastro.html", carros=carros)

@app.route("/manutencao")
def registrar():
    if 'carro_selecionado' not in session:
        flash("Por favor, selecione um carro primeiro.")
        return redirect(url_for('portifólio'))

    carro_selecionado = session['carro_selecionado']
    carro_id = session.get('carro_id')  # Certifique-se de que isso está definido
    
    if carro_id is None:  # Verificação adicional
        flash("ID do carro não encontrado.")
        return redirect(url_for('portifólio'))

    atividades_filtradas = [
        item for item in manutenção_cronograma 
        if item["Veículo"].lower() == carro_selecionado.lower()
    ]
    
    if not atividades_filtradas:
        flash("Não há manutenções programadas para este veículo.")
        atividades_filtradas = []

    veiculos = [carro_selecionado]
    intervalos = sorted(set(item["Intervalo"] for item in atividades_filtradas))

    return render_template("manutencao_programada.html",
                         veiculos=veiculos,
                         intervalos=intervalos,
                         atividades=atividades_filtradas,
                         carro_selecionado=carro_selecionado,
                         carro_id=carro_id)  # Passando o carro_id para o template

from flask import send_file

@app.route("/historico")
def historico():
    if "usuario" not in session:
        flash("Você precisa estar logado.")
        return redirect(url_for("login"))

    if "carro_selecionado" not in session:
        flash("Por favor, selecione um carro primeiro.")
        return redirect(url_for("portifólio"))

    usuario = session["usuario"]
    carro_selecionado = session["carro_selecionado"]
    carro_id = session.get('carro_id')  # Adicionar esta linha

    # Filtrar por usuário E carro selecionado
    historico_usuario = df_manutenções[
        (df_manutenções["Usuário"] == usuario) & 
        (df_manutenções["Carro"] == carro_selecionado)
    ]
    
    historico_usuario = historico_usuario.sort_values(by="Data", ascending=False)

    return render_template("historico.html", 
                         historico=historico_usuario.to_dict(orient="records"),
                         carro_selecionado=carro_selecionado,
                         carro_id=carro_id)  # Adicionar esta linha
    
@app.route("/download_historico")
def download_historico():
    return send_file("historico_manutencao.xlsx", as_attachment=True)

@app.route("/proximas")
def proximas():
    if "usuario" not in session:
        flash("Você precisa estar logado.")
        return redirect(url_for("login"))

    if "carro_selecionado" not in session:
        flash("Por favor, selecione um carro primeiro.")
        return redirect(url_for("portifólio"))

    usuario = session["usuario"]
    carro_selecionado = session["carro_selecionado"]
    carro_id = session.get('carro_id')  

    df_futuras = df_manutenções[
        (df_manutenções["Usuário"] == usuario) &
        (df_manutenções["Notificar"] == "Sim") & 
        (df_manutenções["Carro"] == carro_selecionado)
    ].copy()
    print(f"Print df_futuras {df_futuras}")


    df_futuras = df_futuras.sort_values(by="Próxima Manutenção")
    
    return render_template("proximas_manutencoes.html", proximas=df_futuras.to_dict(orient="records"),
                         carro_selecionado=carro_selecionado,
                         carro_id=carro_id)

@app.route("/dicas")
def dicas():
    carro_id = session.get('carro_id') 
    titulos_dicas = list(set(d['Title'] for d in df_Dicas))
    return render_template("Dicas.html", titulos=titulos_dicas,carro_id=carro_id)

@app.route("/dicas/<titulo>")
def detalhe_dicas(titulo):
    dicas_filtradas = [d for d in df_Dicas if d["Title"] == titulo]
    return render_template("detalhe_dicas.html", titulo=titulo, dicas=dicas_filtradas)

@app.route("/checklist")
def checklist():
    emergencias_count = sum(1 for item in df_Checklist if item["Title"] == "Emergências")
    viagens_count = sum(1 for item in df_Checklist if item["Title"] == "Viagens")
    usados_count = sum(1 for item in df_Checklist if item["Title"] == "Compra de veículos usados")
    return render_template("checklist.html",
                           emergencias_count=emergencias_count,
                           viagens_count=viagens_count,
                           usados_count=usados_count)
    
@app.route("/checklist/<titulo>")
def checklist_detalhado(titulo):
    # Ícones personalizados por título
    icones = {
        "Emergências": "Emergencia].png",
        "Viagens": "Viagem.png",
        "Compra de veículos usados": "CompraVeículo.png"
    }

    checklist_items = [item["Checklist"] for item in df_Checklist if item["Title"] == titulo]
    return render_template("checklist_detalhado.html", titulo=titulo, checklist=checklist_items, icone=icones.get(titulo, "default.png"))


@app.route("/pesquisar")
def pesquisar():
    return render_template("pesquisar.html", resultados=df_Reclamações)

@app.route("/manutencao_especifica")
def manutencao_especifica():
    if 'carro_selecionado' not in session:
        flash("Por favor, selecione um carro primeiro.")
        return redirect(url_for('portifólio'))

    carro_selecionado = session['carro_selecionado']
    atividades = manutenção_cronograma
    carros = [carro_selecionado] 
    tipos = ["Preventiva", "Corretiva"]
    pecas = ["Pastilhas de freio", "Filtro de ar", "Óleo do motor"]

    return render_template("manutencao_especifica.html", carros=carros, tipos=tipos, pecas=pecas)

from datetime import datetime

@app.route("/registrar_manutencao", methods=["POST"])
def registrar_manutencao():
    global df_manutenções

    if "usuario" not in session:
        flash("Você precisa estar logado.")
        return redirect(url_for("login"))

    usuario = session["usuario"]
    data = request.form.get("data")
    modelo = request.form.get("modelo")
    km = request.form.get("km")
    proxima = calcular_proxima(data)
    tipo = "Preventiva"
    notificar = request.form.get("notificar")  # "on" se marcado

    acoes = request.form.getlist("check[]")
    custos = request.form.getlist("custo[]")
    print(f"Notificar: {notificar}")
    checklist_items = []
    for i, acao in enumerate(acoes):
        if acao.strip():
            custo = custos[i] if i < len(custos) else ""
            checklist_items.append({
                "Usuário": usuario,
                "Data": data,
                "Carro": modelo,
                "Notificar": "Sim" if notificar else "Não",
                "Tipo de Manutenção": tipo,
                "Próxima Manutenção": proxima,
                "Ação": acao,
                "Peça": custo,
                "Custo": custo,
                "Técnico Responsável": "",
                "Descrição": km,
                "Anexo": ""
            })

    if checklist_items:
        df_manutenções = pd.concat([df_manutenções, pd.DataFrame(checklist_items)], ignore_index=True)
        df_manutenções.to_excel("historico_manutencao.xlsx", index=False)
        flash("Manutenção registrada com sucesso!")
    else:
        flash("Nenhuma manutenção selecionada.")
    print(f"dataframe de manutenções{df_manutenções}")
    return redirect(url_for("registrar"))

@app.route("/registrar_manutencao_especifica", methods=["POST"])
def registrar_manutencao_especifica():
    global df_manutenções

    if "usuario" not in session:
        flash("Você precisa estar logado.")
        return redirect(url_for("login"))

    usuario = session["usuario"]
    data = request.form.get("data")
    carro = request.form.get("carro")
    tipo = request.form.get("tipo")
    equipamento = request.form.get("equipamento")
    tecnico = request.form.get("tecnico")
    peca = request.form.get("peca")
    proxima = request.form.get("proxima")
    custo = request.form.get("custo")
    descricao = request.form.get("descricao")
    notificar = request.form.get("notificar")
    print(f"Notificar{notificar}")

    item = {
        "Usuário": usuario,
        "Data": data,
        "Carro": carro,
        "Notificar": "Sim" if notificar else "Não",
        "Tipo de Manutenção": tipo,
        "Próxima Manutenção": proxima,
        "Ação": equipamento or "",
        "Peça": peca,
        "Custo": custo,
        "Técnico Responsável": tecnico,
        "Descrição": descricao,
        "Anexo": ""
    }

    df_manutenções = pd.concat([df_manutenções, pd.DataFrame([item])], ignore_index=True)
    df_manutenções.to_excel("historico_manutencao.xlsx", index=False)
    flash("Manutenção específica registrada com sucesso!")

    return redirect(url_for("manutencao_especifica"))

def calcular_proxima(data_str):
    try:
        data = datetime.strptime(data_str, "%Y-%m-%d")
        proxima = data.replace(year=data.year + 1)
        return proxima.strftime("%d/%m/%Y")
    except:
        return "--"

if __name__ == '__main__':
    app.run(debug=True)
