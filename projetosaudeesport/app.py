import sys
import threading
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash

from database import inicializar_banco
from cadastro import (
    cadastrar_participante,
    consultar_recepcao,
    listar_inscritos_por_turma,
    listar_modalidades,
)


def obter_pasta_recursos() -> Path:
    # Quando empacotado com --onefile, os arquivos embutidos ficam em sys._MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


BASE_RECURSOS = obter_pasta_recursos()

app = Flask(
    __name__,
    template_folder=str(BASE_RECURSOS / "templates"),
)
app.secret_key = "chave-local-projeto-saude-esporte"

inicializar_banco()


@app.route("/", methods=["GET"])
def index():
    termo = (request.args.get("busca") or "").strip()
    filtro_modalidade = (request.args.get("filtro_modalidade") or "").strip()
    filtro_dias = (request.args.get("filtro_dias") or "").strip()
    filtro_horario = (request.args.get("filtro_horario") or "").strip()

    modalidades = listar_modalidades()
    resultados = consultar_recepcao(termo) if termo else []

    ver_turma = bool(filtro_modalidade or filtro_dias or filtro_horario)
    inscritos_turma = (
        listar_inscritos_por_turma(
            modalidade_nome=filtro_modalidade or None,
            dias_semana=filtro_dias or None,
            horario=filtro_horario or None,
        )
        if ver_turma
        else []
    )

    return render_template(
        "index.html",
        modalidades=modalidades,
        resultados=resultados,
        termo=termo,
        inscritos_turma=inscritos_turma,
        ver_turma=ver_turma,
        filtro_modalidade=filtro_modalidade,
        filtro_dias=filtro_dias,
        filtro_horario=filtro_horario,
    )


@app.route("/cadastrar", methods=["POST"])
def rota_cadastrar():
    nomes_mod = request.form.getlist("modalidade[]")
    dias_mod = request.form.getlist("dias_semana[]")
    horarios_mod = request.form.getlist("horario[]")

    modalidades_selecionadas = []
    combinacoes_vistas = set()

    for mod, dias, hor in zip(nomes_mod, dias_mod, horarios_mod):
        mod_limpo = (mod or "").strip()
        dias_limpo = (dias or "Seg/Qua/Sex").strip()
        hor_limpo = (hor or "").strip()

        if not mod_limpo:
            continue

        chave = (mod_limpo.lower(), dias_limpo.lower(), hor_limpo.lower())
        if chave in combinacoes_vistas:
            continue
        combinacoes_vistas.add(chave)

        modalidades_selecionadas.append(
            {
                "nome": mod_limpo,
                "dias_semana": dias_limpo,
                "horario": hor_limpo or "A definir",
            }
        )

    dados = {
        "nome_completo": request.form.get("nome_completo", ""),
        "data_nascimento": request.form.get("data_nascimento", ""),
        "rg": request.form.get("rg", ""),
        "cpf": request.form.get("cpf", ""),
        "telefone": request.form.get("telefone", ""),
        "email": request.form.get("email", ""),
        "observacoes_gerais": request.form.get("observacoes_gerais", ""),
        "responsavel": {
            "nome_completo": request.form.get("resp_nome", ""),
            "cpf": request.form.get("resp_cpf", ""),
            "telefone": request.form.get("resp_telefone", ""),
            "parentesco": request.form.get("resp_parentesco", "Responsável legal"),
        },
        "emergencia": {
            "nome_completo": request.form.get("em_nome", ""),
            "parentesco": request.form.get("em_parentesco", ""),
            "telefone": request.form.get("em_telefone", ""),
        },
        "saude": {
            "tipo_sanguineo": request.form.get("tipo_sanguineo", "Não informado"),
            "problemas_cardiacos": request.form.get("problemas_cardiacos") == "on",
            "detalhes_cardiacos": request.form.get("detalhes_cardiacos", ""),
            "outras_doencas": request.form.get("outras_doencas", ""),
            "alergias": request.form.get("alergias", ""),
            "medicamentos_continuos": request.form.get("medicamentos_continuos", ""),
            "restricoes_fisicas_ou_idosos": request.form.get("restricoes_idosos", ""),
            "atestado_medico_valido": request.form.get("atestado_valido") == "on",
        },
        "modalidades": modalidades_selecionadas,
    }

    try:
        pid = cadastrar_participante(dados)
        flash(f"Participante cadastrado com sucesso! ID: {pid}", "sucesso")
    except ValueError as erro:
        flash(str(erro), "erro")

    return redirect(url_for("index"))

def abrir_navegador():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    # Evita abrir duas abas quando debug=True estiver desligado
    threading.Timer(1.2, abrir_navegador).start()
    app.run(host="127.0.0.1", port=5000, debug=False)