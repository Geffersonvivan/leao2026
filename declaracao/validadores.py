"""
Validadores reutilizáveis para a declaração.
"""
import re


def validar_cpf(cpf: str) -> bool:
    """
    Valida CPF pelo algoritmo oficial da Receita Federal.
    Aceita com ou sem formatação (pontos e traço).
    """
    digits = re.sub(r"\D", "", cpf)

    if len(digits) != 11:
        return False

    # Rejeita sequências triviais (111.111.111-11, etc.)
    if len(set(digits)) == 1:
        return False

    def calcular_digito(parcial: str, pesos: range) -> int:
        total = sum(int(d) * p for d, p in zip(parcial, pesos))
        resto = total % 11
        return 0 if resto < 2 else 11 - resto

    d1 = calcular_digito(digits[:9], range(10, 1, -1))
    d2 = calcular_digito(digits[:10], range(11, 1, -1))

    return digits[9] == str(d1) and digits[10] == str(d2)


def formatar_cpf(cpf: str) -> str:
    """Formata 11 dígitos para 000.000.000-00."""
    digits = re.sub(r"\D", "", cpf)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return cpf
