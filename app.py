import json
import os
import uuid
from dbm import error
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import re

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from psycopg2.extras import RealDictCursor
from database import get_connection

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return decorated_function



# --- CONFIGURAÇÕES DE UPLOAD ---
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Garante que a pasta static/uploads exista ao iniciar a aplicação
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# -------------------------------

# Teste API
@app.route('/api', methods=['GET'])
def home():
    return jsonify({"message": "API de catalogo de filmes"}), 200


# Ping
@app.route('/ping', methods=['GET'])
def ping():
    conn = get_connection()
    conn.close()
    return jsonify({"message": "pong! API Rodando!", "db": str(conn)}), 200


# Listar todos os filmes
@app.route('/filmes', methods=['GET'])
@login_required
def listar_filmes():
    sql = "SELECT * FROM filmes"
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql)
        filmes = cursor.fetchall()
        print('filmes: --------------------------', filmes)
        conn.close()
        return render_template("index.html", filmes=filmes)
    except Exception as ex:
        print('erro: ', str(ex))
        return jsonify({"message": "erro ao listar filmes"}), 500


@app.route("/novo", methods=["GET", "POST"])
@login_required
def novo_filme():
    sql = "INSERT INTO filmes (titulo, genero, ano, url_capa) VALUES (%s, %s, %s, %s)"
    try:
        if request.method == "POST":
            titulo = request.form.get("titulo")
            genero = request.form.get("genero")
            ano = request.form.get("ano")

            if not titulo or not genero:
                return jsonify({"message": "Os campos Título e Gênero são obrigatórios"}), 400

            # 1. Recebe o arquivo através da requisição
            file = request.files.get("url_capa")
            caminho_db = None

            # Verifica se o arquivo existe e se tem a extensão permitida (jpeg, jpg, png)
            if file and file.filename != '' and allowed_file(file.filename):
                extensao = file.filename.rsplit('.', 1)[1].lower()

                # 3. Renomeia o arquivo para uma hash única
                novo_nome = f"{uuid.uuid4().hex}.{extensao}"

                # 2. Salva o arquivo na pasta 'uploads' dentro de 'static'
                caminho_arquivo = os.path.join(UPLOAD_FOLDER, novo_nome)
                file.save(caminho_arquivo)

                # 5. Salva o caminho do arquivo para o banco de dados
                caminho_db = f"uploads/{novo_nome}"

            params = [titulo, genero, ano, caminho_db]

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            conn.close()
            return redirect(url_for("listar_filmes"))

        return render_template("novo_filme.html")
    except Exception as ex:
        print('erro detalhado: ', str(ex))
        return jsonify({"message": "erro ao cadastrar filme", "detalhe": str(ex)}), 500


@app.route("/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_filme(id):
    try:
        conn = get_connection()
        if request.method == "POST":
            titulo = request.form.get("titulo")
            genero = request.form.get("genero")
            ano = request.form.get("ano")

            # Busca a capa atual no banco de dados para não perder a foto caso não seja enviada uma nova
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT url_capa FROM filmes WHERE id = %s", [id])
            filme_atual = cursor.fetchone()
            caminho_db = filme_atual['url_capa'] if filme_atual else None

            # Processa o novo arquivo se o usuário enviar
            file = request.files.get("url_capa")

            if file and file.filename != '' and allowed_file(file.filename):
                extensao = file.filename.rsplit('.', 1)[1].lower()
                novo_nome = f"{uuid.uuid4().hex}.{extensao}"
                caminho_arquivo = os.path.join(UPLOAD_FOLDER, novo_nome)
                file.save(caminho_arquivo)
                caminho_db = f"uploads/{novo_nome}"

            sql_update = "UPDATE filmes SET titulo = %s, genero = %s, ano = %s, url_capa = %s WHERE id = %s"
            params = [titulo, genero, ano, caminho_db, id]

            cursor = conn.cursor()
            cursor.execute(sql_update, params)
            conn.commit()
            conn.close()
            return redirect(url_for("listar_filmes"))

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = "SELECT * FROM filmes WHERE id = %s"
        params = [id]
        cursor.execute(sql, params)
        filme = cursor.fetchone()
        conn.close()

        if filme is None:
            return redirect(url_for("listar_filmes"))
        return render_template("editar_filme.html", filme=filme)
    except Exception as ex:
        print('erro: ', str(ex))
        return jsonify({"message": "erro ao editar filme"}), 500


@app.route("/deletar/<int:id>", methods=["POST"])
@login_required
def deletar_filme(id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM filmes WHERE id = %s"
        params = [id]
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return redirect(url_for("listar_filmes"))
    except Exception as ex:
        print('erro: ', str(ex))
        return jsonify({"message": "erro ao deletar filme"}), 500


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_informado = request.form.get("email")
        senha_informada = request.form.get("password")

        # --- LOGIN PADRÃO (HARDCODED) ---
        # Verificação manual para o seu usuário fixo
        if email_informado == "riana.aldias@gmail.com" and senha_informada == "1234":
            session["user"] = email_informado
            session["user_nome"] = "Riana (Admin)"
            return redirect(url_for("listar_filmes"))
        # -------------------------------

        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = "SELECT * FROM usuarios WHERE email = %s"
            cursor.execute(sql, [email_informado])
            usuario = cursor.fetchone()
            conn.close()

            if not usuario:
                return render_template("login.html", erro="E-mail não encontrado!")

            # Verificação para os demais usuários (que usam hash)
            if check_password_hash(usuario['senha'], senha_informada):
                session["user"] = usuario['email']
                session["user_nome"] = usuario['nome']
                return redirect(url_for("listar_filmes"))
            else:
                return render_template("login.html", erro="Senha incorreta!")

        except Exception as ex:
            return render_template("login.html", erro="Erro ao processar login.")

    return render_template("login.html", erro=None)


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("password")

        # Validações de senha (8 caracteres e especial)
        if len(senha) < 8 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
            return render_template("cadastro.html", erro="Senha inválida! Mínimo 8 caracteres e um caractere especial.")

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # CRIPTOGRAFIA ANTES DE SALVAR
            senha_hash = generate_password_hash(senha)

            sql = "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"
            cursor.execute(sql, (nome, email, senha_hash))
            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except Exception as ex:
            # Se cair aqui, é provável que o e-mail já exista ou a tabela esteja errada
            print(f"Erro no banco: {ex}")
            return render_template("cadastro.html",
                                   erro="Este e-mail já está cadastrado ou ocorreu um erro no servidor.")

    return render_template("cadastro.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)