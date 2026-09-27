from models import Operacao

def consolidado(operacoes):
    fechadas = [o for o in operacoes if o.status == "FECHADA"]
    abertas = [o for o in operacoes if o.status == "ABERTA"]

    resultado_fechado = sum(o.resultado or 0 for o in fechadas)
    resultado_aberto = sum(o.resultado or 0 for o in abertas)
    total = resultado_fechado + resultado_aberto

    vencedoras = [o for o in fechadas if (o.resultado or 0) > 0]
    perdedoras = [o for o in fechadas if (o.resultado or 0) < 0]

    capital_aberto = sum(
        o.preco_entrada * o.quantidade for o in abertas
    )

    taxa_acerto = (
        len(vencedoras) / len(fechadas) * 100
        if fechadas else 0
    )

    ganhos = sum(o.resultado for o in vencedoras)
    perdas = abs(sum(o.resultado for o in perdedoras))
    profit_factor = ganhos / perdas if perdas else None

    return {
        "resultado_fechado": round(resultado_fechado, 2),
        "resultado_aberto": round(resultado_aberto, 2),
        "resultado_total": round(total, 2),
        "capital_em_posicoes_abertas": round(capital_aberto, 2),
        "operacoes_abertas": len(abertas),
        "operacoes_fechadas": len(fechadas),
        "operacoes_ganhadoras": len(vencedoras),
        "operacoes_perdedoras": len(perdedoras),
        "taxa_acerto": round(taxa_acerto, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "maior_ganho": round(max((o.resultado for o in fechadas), default=0), 2),
        "maior_perda": round(min((o.resultado for o in fechadas), default=0), 2),
    }
