import sqlite3
import sys
from pathlib import Path


def obter_pasta_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


DB_PATH = obter_pasta_base() / "projeto_saude_esporte.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT NOT NULL,
    data_nascimento TEXT NOT NULL, -- formato ISO: YYYY-MM-DD
    rg TEXT NOT NULL,
    cpf TEXT NOT NULL UNIQUE,
    telefone TEXT NOT NULL,
    email TEXT,
    observacoes_gerais TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS responsaveis_legais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participante_id INTEGER NOT NULL,
    nome_completo TEXT NOT NULL,
    cpf TEXT NOT NULL,
    telefone TEXT NOT NULL,
    parentesco TEXT,
    FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fichas_saude (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participante_id INTEGER NOT NULL UNIQUE,
    tipo_sanguineo TEXT NOT NULL,
    problemas_cardiacos INTEGER NOT NULL DEFAULT 0,
    detalhes_cardiacos TEXT,
    outras_doencas TEXT,
    alergias TEXT,
    medicamentos_continuos TEXT,
    restricoes_fisicas_ou_idosos TEXT,
    atestado_medico_valido INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contatos_emergencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participante_id INTEGER NOT NULL,
    nome_completo TEXT NOT NULL,
    parentesco TEXT NOT NULL,
    telefone TEXT NOT NULL,
    prioridade INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS modalidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    categoria TEXT
);

CREATE TABLE IF NOT EXISTS participante_modalidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participante_id INTEGER NOT NULL,
    modalidade_id INTEGER NOT NULL,
    dias_semana TEXT NOT NULL DEFAULT 'A definir', -- ex.: "Seg/Qua/Sex", "Ter/Qui", "Sábado"
    horario TEXT NOT NULL DEFAULT 'A definir',     -- ex.: "13h", "14h"
    ativo INTEGER NOT NULL DEFAULT 1,
    UNIQUE (participante_id, modalidade_id, dias_semana, horario),
    FOREIGN KEY (participante_id) REFERENCES participantes(id) ON DELETE CASCADE,
    FOREIGN KEY (modalidade_id) REFERENCES modalidades(id) ON DELETE CASCADE
);
"""

MODALIDADES_INICIAIS = [
    ("Vôlei", "coletivo"),
    ("Pilates", "mobilidade"),
    ("Natação", "aquatica"),
    ("Hidroginástica", "aquatica"),
    ("Musculação", "forca"),
    ("Dança", "mobilidade"),
    ("Alongamento", "mobilidade"),
    ("Boxe", "luta"),
    ("Lutas", "luta"),
]


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def inicializar_banco(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            "INSERT OR IGNORE INTO modalidades (nome, categoria) VALUES (?, ?);",
            MODALIDADES_INICIAIS,
        )
        conn.commit()


if __name__ == "__main__":
    inicializar_banco()
    print("Banco SQLite inicializado com sucesso.")