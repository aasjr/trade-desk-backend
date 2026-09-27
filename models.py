from datetime import datetime
from database import db

class Operacao(db.Model):
    __tablename__ = "operacoes"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)
    tipo = db.Column(db.String(4), nullable=False)  # BUY / SELL
    quantidade = db.Column(db.Float, nullable=False)
    preco_entrada = db.Column(db.Float, nullable=False)
    preco_atual = db.Column(db.Float)
    data_abertura = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_fechamento = db.Column(db.DateTime)
    preco_saida = db.Column(db.Float)
    status = db.Column(db.String(10), nullable=False, default="ABERTA")
    corretagem = db.Column(db.Float, default=0.0)
    taxas = db.Column(db.Float, default=0.0)
    resultado = db.Column(db.Float, default=0.0)
    resultado_percentual = db.Column(db.Float, default=0.0)
    observacao = db.Column(db.Text)

    def calcular_resultado(self, preco=None):
        p = preco if preco is not None else self.preco_atual
        if p is None:
            return 0.0
        bruto = (p - self.preco_entrada) * self.quantidade
        if self.tipo == "SELL":
            bruto = -bruto
        custos = (self.corretagem or 0) + (self.taxas or 0)
        self.resultado = bruto - custos
        base = self.preco_entrada * self.quantidade
        self.resultado_percentual = (self.resultado / base * 100) if base else 0.0
        return self.resultado

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "tipo": self.tipo,
            "quantidade": self.quantidade,
            "preco_entrada": self.preco_entrada,
            "preco_atual": self.preco_atual,
            "data_abertura": self.data_abertura.isoformat() if self.data_abertura else None,
            "data_fechamento": self.data_fechamento.isoformat() if self.data_fechamento else None,
            "preco_saida": self.preco_saida,
            "status": self.status,
            "corretagem": self.corretagem,
            "taxas": self.taxas,
            "resultado": self.resultado,
            "resultado_percentual": self.resultado_percentual,
            "observacao": self.observacao,
        }
