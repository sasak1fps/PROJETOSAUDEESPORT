from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


def calcular_idade(data_nascimento: date, hoje: Optional[date] = None) -> int:
    hoje = hoje or date.today()
    anos = hoje.year - data_nascimento.year
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        anos -= 1
    return anos


def limpar_digitos(valor: Optional[str]) -> str:
    if not valor:
        return ""
    return "".join(ch for ch in valor if ch.isdigit())


def parse_data(data_str: str) -> date:
    """Aceita 'YYYY-MM-DD' ou 'DD/MM/YYYY' e retorna date."""
    texto = data_str.strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError("Data de nascimento inválida. Use AAAA-MM-DD ou DD/MM/AAAA.")


def formatar_cpf(cpf_limpo: str) -> str:
    digitos = limpar_digitos(cpf_limpo)
    if len(digitos) != 11:
        return cpf_limpo
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def formatar_telefone(tel_limpo: str) -> str:
    digitos = limpar_digitos(tel_limpo)
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return tel_limpo


@dataclass
class ContatoEmergencia:
    nome: str
    parentesco: str
    telefone: str


@dataclass
class ResponsavelLegal:
    nome: str
    cpf: str
    telefone: str
    parentesco: str = "Responsável legal"


@dataclass
class FichaSaude:
    tipo_sanguineo: str
    problemas_cardiacos: bool
    detalhes_cardiacos: str = ""
    outras_doencas: str = ""
    alergias: str = ""
    medicamentos_continuos: str = ""
    restricoes_modalidade: str = ""
    atestado_medico_valido: bool = False


@dataclass
class Participante:
    nome: str
    data_nascimento: date
    rg: str
    cpf: str
    telefone: str
    emergencia: ContatoEmergencia
    saude: FichaSaude
    modalidades: List[str] = field(default_factory=list)
    responsavel: Optional[ResponsavelLegal] = None
    email: str = ""
    observacoes_gerais: str = ""

    def validar(self) -> List[str]:
        erros: List[str] = []
        idade = calcular_idade(self.data_nascimento)

        if not self.nome.strip():
            erros.append("Nome completo é obrigatório.")

        if self.data_nascimento > date.today():
            erros.append("Data de nascimento não pode estar no futuro.")
        elif idade < 12 or idade > 110:
            erros.append(f"Idade calculada ({idade} anos) fora da faixa esperada (12 a 110 anos).")

        if len(limpar_digitos(self.cpf)) != 11:
            erros.append("CPF deve conter 11 dígitos.")

        if not self.rg.strip():
            erros.append("RG é obrigatório.")

        if len(limpar_digitos(self.telefone)) < 10:
            erros.append("Telefone do participante inválido.")

        if not self.emergencia.nome.strip() or len(limpar_digitos(self.emergencia.telefone)) < 10:
            erros.append("Contato de emergência completo é obrigatório.")

        if idade < 18:
            if not self.responsavel or not self.responsavel.nome.strip():
                erros.append("Responsável legal é obrigatório para participantes menores de 18 anos.")
            elif len(limpar_digitos(self.responsavel.cpf)) != 11:
                erros.append("CPF do responsável legal deve conter 11 dígitos.")

        if self.saude.problemas_cardiacos and not self.saude.detalhes_cardiacos.strip():
            erros.append("Informe os detalhes do problema cardíaco.")

        if not self.modalidades:
            erros.append("Selecione ao menos uma modalidade.")

        return erros