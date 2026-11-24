from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from database import DB_PATH, get_connection
from repositorio import (
    calcular_idade,
    formatar_cpf,
    formatar_telefone,
    limpar_digitos,
    parse_data,
)


def listar_modalidades(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, nome, categoria FROM modalidades ORDER BY nome ASC;"
        ).fetchall()
        return [dict(r) for r in rows]


def validar_cadastro(dados: Dict[str, Any]) -> List[str]:
    erros: List[str] = []

    nome = (dados.get("nome_completo") or "").strip()
    if not nome:
        erros.append("Nome completo é obrigatório.")

    data_nasc_raw = dados.get("data_nascimento")
    data_nasc: Optional[date] = None
    if isinstance(data_nasc_raw, date):
        data_nasc = data_nasc_raw
    elif isinstance(data_nasc_raw, str) and data_nasc_raw.strip():
        try:
            data_nasc = parse_data(data_nasc_raw)
        except ValueError as exc:
            erros.append(str(exc))
    else:
        erros.append("Data de nascimento é obrigatória.")

    idade: Optional[int] = None
    if data_nasc:
        if data_nasc > date.today():
            erros.append("Data de nascimento não pode estar no futuro.")
        else:
            idade = calcular_idade(data_nasc)
            if idade < 12 or idade > 110:
                erros.append(f"Idade ({idade} anos) fora da faixa do projeto (12 a 110 anos).")

    rg = (dados.get("rg") or "").strip()
    if not rg:
        erros.append("RG é obrigatório.")

    cpf_limpo = limpar_digitos(dados.get("cpf"))
    if len(cpf_limpo) != 11:
        erros.append("CPF deve conter 11 dígitos.")

    telefone_limpo = limpar_digitos(dados.get("telefone"))
    if len(telefone_limpo) < 10:
        erros.append("Telefone do participante inválido.")

    emergencia = dados.get("emergencia") or {}
    em_nome = (emergencia.get("nome_completo") or "").strip()
    em_parentesco = (emergencia.get("parentesco") or "").strip()
    em_tel = limpar_digitos(emergencia.get("telefone"))
    if not em_nome or not em_parentesco or len(em_tel) < 10:
        erros.append("Contato de emergência (nome, parentesco e telefone) é obrigatório.")

    if idade is not None and idade < 18:
        resp = dados.get("responsavel") or {}
        resp_nome = (resp.get("nome_completo") or "").strip()
        resp_cpf = limpar_digitos(resp.get("cpf"))
        resp_tel = limpar_digitos(resp.get("telefone"))
        if not resp_nome or len(resp_cpf) != 11 or len(resp_tel) < 10:
            erros.append(
                "Para menores de 18 anos, informe nome, CPF (11 dígitos) e telefone do responsável legal."
            )

    saude = dados.get("saude") or {}
    tipo_sang = (saude.get("tipo_sanguineo") or "").strip()
    if not tipo_sang:
        erros.append("Tipo sanguíneo é obrigatório (ou informe 'Não informado').")

    problemas_cardiacos = bool(saude.get("problemas_cardiacos", False))
    detalhes_cardiacos = (saude.get("detalhes_cardiacos") or "").strip()
    if problemas_cardiacos and not detalhes_cardiacos:
        erros.append("Informe os detalhes do problema cardíaco.")

    modalidades = dados.get("modalidades") or []
    if not modalidades:
        erros.append("Selecione ao menos uma modalidade.")

    return erros


def cadastrar_participante(dados: Dict[str, Any], db_path: Path = DB_PATH) -> int:
    erros = validar_cadastro(dados)
    if erros:
        raise ValueError("Falha na validação:\n- " + "\n- ".join(erros))

    data_nasc = (
        dados["data_nascimento"]
        if isinstance(dados["data_nascimento"], date)
        else parse_data(dados["data_nascimento"])
    )
    cpf_limpo = limpar_digitos(dados["cpf"])
    telefone_limpo = limpar_digitos(dados["telefone"])

    emergencia = dados["emergencia"]
    responsavel = dados.get("responsavel") or {}
    saude = dados["saude"]
    modalidades = dados["modalidades"]

    with get_connection(db_path) as conn:
        existente = conn.execute(
            "SELECT id, nome_completo FROM participantes WHERE cpf = ?;",
            (cpf_limpo,),
        ).fetchone()
        if existente:
            raise ValueError(
                f"Já existe participante cadastrado com este CPF: {existente['nome_completo']} (ID {existente['id']})."
            )

        cursor = conn.execute(
            """
            INSERT INTO participantes (
                nome_completo, data_nascimento, rg, cpf, telefone, email, observacoes_gerais
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                dados["nome_completo"].strip(),
                data_nasc.isoformat(),
                dados["rg"].strip(),
                cpf_limpo,
                telefone_limpo,
                (dados.get("email") or "").strip() or None,
                (dados.get("observacoes_gerais") or "").strip() or None,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Não foi possível obter o ID do participante cadastrado.")
        participante_id = int(cursor.lastrowid)

        if (responsavel.get("nome_completo") or "").strip():
            conn.execute(
                """
                INSERT INTO responsaveis_legais (
                    participante_id, nome_completo, cpf, telefone, parentesco
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    participante_id,
                    responsavel["nome_completo"].strip(),
                    limpar_digitos(responsavel.get("cpf")),
                    limpar_digitos(responsavel.get("telefone")),
                    (responsavel.get("parentesco") or "Responsável legal").strip(),
                ),
            )

        conn.execute(
            """
            INSERT INTO fichas_saude (
                participante_id,
                tipo_sanguineo,
                problemas_cardiacos,
                detalhes_cardiacos,
                outras_doencas,
                alergias,
                medicamentos_continuos,
                restricoes_fisicas_ou_idosos,
                atestado_medico_valido
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                participante_id,
                saude["tipo_sanguineo"].strip(),
                1 if saude.get("problemas_cardiacos") else 0,
                (saude.get("detalhes_cardiacos") or "").strip() or None,
                (saude.get("outras_doencas") or "").strip() or None,
                (saude.get("alergias") or "").strip() or None,
                (saude.get("medicamentos_continuos") or "").strip() or None,
                (saude.get("restricoes_fisicas_ou_idosos") or "").strip() or None,
                1 if saude.get("atestado_medico_valido") else 0,
            ),
        )

        conn.execute(
            """
            INSERT INTO contatos_emergencia (
                participante_id, nome_completo, parentesco, telefone, prioridade
            ) VALUES (?, ?, ?, ?, 1);
            """,
            (
                participante_id,
                emergencia["nome_completo"].strip(),
                emergencia["parentesco"].strip(),
                limpar_digitos(emergencia["telefone"]),
            ),
        )

        for item in modalidades:
            if isinstance(item, dict):
                mod_nome = item["nome"].strip()
                dias_semana = (item.get("dias_semana") or "A definir").strip()
                horario = (item.get("horario") or "A definir").strip()
            else:
                mod_nome = str(item).strip()
                dias_semana = "A definir"
                horario = "A definir"

            mod_row = conn.execute(
                "SELECT id FROM modalidades WHERE LOWER(nome) = LOWER(?);",
                (mod_nome,),
            ).fetchone()
            if not mod_row:
                raise ValueError(f"Modalidade não encontrada no cadastro: '{mod_nome}'.")

            conn.execute(
                """
                INSERT INTO participante_modalidades (
                    participante_id, modalidade_id, dias_semana, horario, ativo
                ) VALUES (?, ?, ?, ?, 1);
                """,
                (participante_id, mod_row["id"], dias_semana, horario),
            )

        conn.commit()
        return participante_id


def consultar_recepcao(termo: str, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    termo_limpo = termo.strip()
    cpf_digitos = limpar_digitos(termo_limpo)

    sql = """
    SELECT
        p.id,
        p.nome_completo,
        p.data_nascimento,
        p.cpf,
        p.telefone,
        f.tipo_sanguineo,
        f.problemas_cardiacos,
        f.detalhes_cardiacos,
        f.outras_doencas,
        f.alergias,
        f.medicamentos_continuos,
        f.restricoes_fisicas_ou_idosos,
        c.nome_completo AS emergencia_nome,
        c.parentesco AS emergencia_parentesco,
        c.telefone AS emergencia_telefone
    FROM participantes p
    LEFT JOIN fichas_saude f ON f.participante_id = p.id
    LEFT JOIN contatos_emergencia c ON c.participante_id = p.id AND c.prioridade = 1
    WHERE p.ativo = 1
      AND (
          LOWER(p.nome_completo) LIKE LOWER(?)
          OR (? != '' AND p.cpf LIKE ?)
      )
    ORDER BY p.nome_completo ASC;
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            sql, (f"%{termo_limpo}%", cpf_digitos, f"%{cpf_digitos}%")
        ).fetchall()

        resultados: List[Dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            data_nasc = parse_data(item["data_nascimento"])
            item["idade"] = calcular_idade(data_nasc)
            item["cpf_formatado"] = formatar_cpf(item["cpf"])
            item["telefone_formatado"] = formatar_telefone(item["telefone"])
            item["emergencia_telefone_formatado"] = formatar_telefone(
                item["emergencia_telefone"] or ""
            )

            mods = conn.execute(
                """
                SELECT m.nome, pm.dias_semana, pm.horario
                FROM participante_modalidades pm
                JOIN modalidades m ON m.id = pm.modalidade_id
                WHERE pm.participante_id = ? AND pm.ativo = 1
                ORDER BY m.nome ASC, pm.dias_semana ASC, pm.horario ASC;
                """,
                (item["id"],),
            ).fetchall()
            item["modalidades"] = [dict(m) for m in mods]

    

        return resultados
def listar_inscritos_por_turma(
    modalidade_nome: Optional[str] = None,
    dias_semana: Optional[str] = None,
    horario: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """Lista participantes ativos inscritos por modalidade, dias e/ou horário."""
    filtros = ["p.ativo = 1", "pm.ativo = 1"]
    params: List[Any] = []

    if modalidade_nome and modalidade_nome.strip():
        filtros.append("LOWER(m.nome) = LOWER(?)")
        params.append(modalidade_nome.strip())

    if dias_semana and dias_semana.strip():
        filtros.append("LOWER(pm.dias_semana) = LOWER(?)")
        params.append(dias_semana.strip())

    if horario and horario.strip():
        filtros.append("LOWER(pm.horario) LIKE LOWER(?)")
        params.append(f"%{horario.strip()}%")

    where_sql = " AND ".join(filtros)

    sql = f"""
    SELECT
        p.id,
        p.nome_completo,
        p.data_nascimento,
        p.telefone,
        m.nome AS modalidade,
        pm.dias_semana,
        pm.horario,
        f.tipo_sanguineo,
        f.problemas_cardiacos,
        f.detalhes_cardiacos,
        f.restricoes_fisicas_ou_idosos,
        c.nome_completo AS emergencia_nome,
        c.telefone AS emergencia_telefone
    FROM participante_modalidades pm
    JOIN participantes p ON p.id = pm.participante_id
    JOIN modalidades m ON m.id = pm.modalidade_id
    LEFT JOIN fichas_saude f ON f.participante_id = p.id
    LEFT JOIN contatos_emergencia c ON c.participante_id = p.id AND c.prioridade = 1
    WHERE {where_sql}
    ORDER BY m.nome ASC, pm.dias_semana ASC, pm.horario ASC, p.nome_completo ASC;
    """

    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        inscritos: List[Dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            data_nasc = parse_data(item["data_nascimento"])
            item["idade"] = calcular_idade(data_nasc)
            item["telefone_formatado"] = formatar_telefone(item["telefone"])
            item["emergencia_telefone_formatado"] = formatar_telefone(
                item["emergencia_telefone"] or ""
            )
            inscritos.append(item)
        return inscritos
