from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger, swag_from

from config import Config
from database import db
from models import Operacao
from services.calculos import consolidado
from services.yahoo_finance import cotacao_atual, fundamentos, historico


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Bolsa Dashboard API",
            "description": "API REST para registro e acompanhamento de operações em bolsa.",
            "version": "1.0.0",
        },
        "basePath": "/",
        "schemes": ["http"],
        "definitions": {
            "NovaOperacao": {
                "type": "object",
                "required": ["ticker", "tipo", "quantidade", "preco_entrada"],
                "properties": {
                    "ticker": {"type": "string", "example": "PETR4"},
                    "tipo": {"type": "string", "enum": ["BUY", "SELL"], "example": "BUY"},
                    "quantidade": {"type": "number", "example": 100},
                    "preco_entrada": {"type": "number", "example": 38.50},
                    "corretagem": {"type": "number", "example": 5.00},
                    "taxas": {"type": "number", "example": 1.20},
                    "observacao": {"type": "string", "example": "Estratégia de tendência"},
                },
            },
            "Operacao": {
                "allOf": [
                    {"$ref": "#/definitions/NovaOperacao"},
                    {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "example": 1},
                            "preco_atual": {"type": "number", "example": 40.15},
                            "preco_saida": {"type": "number", "example": 41.20},
                            "status": {
                                "type": "string",
                                "enum": ["ABERTA", "FECHADA"],
                            },
                            "resultado": {"type": "number", "example": 158.80},
                            "resultado_percentual": {
                                "type": "number",
                                "example": 4.12,
                            },
                            "data_abertura": {"type": "string", "format": "date-time"},
                            "data_fechamento": {"type": "string", "format": "date-time"},
                        },
                    },
                ]
            },
        },
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/openapi.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/",
    }

    Swagger(app, template=swagger_template, config=swagger_config)

    # ------------------------------------------------------------------
    # HEALTH
    # ------------------------------------------------------------------

    @app.get("/api/health")
    @swag_from({
        "tags": ["Sistema"],
        "summary": "Verifica o status da API",
        "responses": {
            200: {
                "description": "API operacional",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "example": "ok"}},
                },
            }
        },
    })
    def health():
        return jsonify({"status": "ok"})

    # ------------------------------------------------------------------
    # OPERAÇÕES
    # ------------------------------------------------------------------

    @app.get("/api/operacoes")
    @swag_from({
        "tags": ["Operações"],
        "summary": "Lista as operações",
        "parameters": [{
            "name": "status",
            "in": "query",
            "required": False,
            "type": "string",
            "enum": ["ABERTA", "FECHADA"],
        }],
        "responses": {
            200: {
                "description": "Lista de operações",
                "schema": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Operacao"},
                },
            }
        },
    })
    def listar_operacoes():
        status = request.args.get("status")
        query = Operacao.query
        if status:
            query = query.filter_by(status=status.upper())
        operacoes = query.order_by(Operacao.id.desc()).all()
        return jsonify([o.to_dict() for o in operacoes])

    @app.get("/api/operacoes/<int:id>")
    @swag_from({
        "tags": ["Operações"],
        "summary": "Consulta uma operação",
        "parameters": [{
            "name": "id",
            "in": "path",
            "required": True,
            "type": "integer",
        }],
        "responses": {
            200: {
                "description": "Operação encontrada",
                "schema": {"$ref": "#/definitions/Operacao"},
            },
            404: {"description": "Operação não encontrada"},
        },
    })
    def consultar_operacao(id):
        operacao = Operacao.query.get_or_404(id)
        return jsonify(operacao.to_dict())

    @app.post("/api/operacoes")
    @swag_from({
        "tags": ["Operações"],
        "summary": "Abre uma nova operação",
        "parameters": [{
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {"$ref": "#/definitions/NovaOperacao"},
        }],
        "responses": {
            201: {
                "description": "Operação criada",
                "schema": {"$ref": "#/definitions/Operacao"},
            },
            400: {"description": "Dados inválidos"},
        },
    })
    def abrir_operacao():
        data = request.get_json() or {}
        obrigatorios = ["ticker", "tipo", "quantidade", "preco_entrada"]
        faltantes = [campo for campo in obrigatorios if campo not in data]

        if faltantes:
            return jsonify({
                "erro": f"Campos obrigatórios: {', '.join(faltantes)}"
            }), 400

        tipo = str(data["tipo"]).upper()
        if tipo not in ("BUY", "SELL"):
            return jsonify({"erro": "tipo deve ser BUY ou SELL"}), 400

        if float(data["quantidade"]) <= 0:
            return jsonify({"erro": "quantidade deve ser maior que zero"}), 400

        if float(data["preco_entrada"]) <= 0:
            return jsonify({"erro": "preco_entrada deve ser maior que zero"}), 400

        operacao = Operacao(
            ticker=str(data["ticker"]).upper().replace(".SA", ""),
            tipo=tipo,
            quantidade=float(data["quantidade"]),
            preco_entrada=float(data["preco_entrada"]),
            corretagem=float(data.get("corretagem", 0) or 0),
            taxas=float(data.get("taxas", 0) or 0),
            observacao=data.get("observacao"),
        )

        operacao.preco_atual = operacao.preco_entrada
        operacao.calcular_resultado()

        db.session.add(operacao)
        db.session.commit()

        return jsonify(operacao.to_dict()), 201

    @app.put("/api/operacoes/<int:id>")
    @swag_from({
        "tags": ["Operações"],
        "summary": "Altera uma operação",
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "type": "integer",
            },
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {"$ref": "#/definitions/NovaOperacao"},
            },
        ],
        "responses": {
            200: {
                "description": "Operação alterada",
                "schema": {"$ref": "#/definitions/Operacao"},
            },
            404: {"description": "Operação não encontrada"},
        },
    })
    def alterar_operacao(id):
        operacao = Operacao.query.get_or_404(id)
        data = request.get_json() or {}

        if "ticker" in data:
            operacao.ticker = str(data["ticker"]).upper().replace(".SA", "")

        if "tipo" in data:
            tipo = str(data["tipo"]).upper()
            if tipo not in ("BUY", "SELL"):
                return jsonify({"erro": "tipo deve ser BUY ou SELL"}), 400
            operacao.tipo = tipo

        if "observacao" in data:
            operacao.observacao = data["observacao"]

        for campo in ["quantidade", "preco_entrada", "corretagem", "taxas"]:
            if campo in data:
                setattr(operacao, campo, float(data[campo]))

        if operacao.status == "ABERTA":
            operacao.calcular_resultado(
                operacao.preco_atual or operacao.preco_entrada
            )

        db.session.commit()
        return jsonify(operacao.to_dict())

    @app.delete("/api/operacoes/<int:id>")
    @swag_from({
        "tags": ["Operações"],
        "summary": "Apaga uma operação",
        "parameters": [{
            "name": "id",
            "in": "path",
            "required": True,
            "type": "integer",
        }],
        "responses": {
            200: {"description": "Operação removida"},
            404: {"description": "Operação não encontrada"},
        },
    })
    def apagar_operacao(id):
        operacao = Operacao.query.get_or_404(id)
        db.session.delete(operacao)
        db.session.commit()
        return jsonify({"mensagem": "Operação removida"})

    @app.post("/api/operacoes/<int:id>/fechar")
    @swag_from({
        "tags": ["Operações"],
        "summary": "Fecha uma operação",
        "description": (
            "O preço de saída é opcional. Quando omitido, "
            "a API tenta obter a cotação atual pelo Yahoo Finance."
        ),
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "type": "integer",
            },
            {
                "name": "body",
                "in": "body",
                "required": False,
                "schema": {
                    "type": "object",
                    "properties": {
                        "preco_saida": {
                            "type": "number",
                            "example": 41.20,
                        }
                    },
                },
            },
        ],
        "responses": {
            200: {
                "description": "Operação fechada",
                "schema": {"$ref": "#/definitions/Operacao"},
            },
            400: {"description": "Não foi possível fechar a operação"},
            404: {"description": "Operação não encontrada"},
        },
    })
    def fechar_operacao(id):
        operacao = Operacao.query.get_or_404(id)

        if operacao.status == "FECHADA":
            return jsonify({"erro": "Operação já está fechada"}), 400

        data = request.get_json(silent=True) or {}
        preco = data.get("preco_saida")

        if preco is None:
            try:
                preco = cotacao_atual(operacao.ticker)["preco"]
            except Exception:
                return jsonify({
                    "erro": (
                        "Não foi possível obter a cotação. "
                        "Informe preco_saida manualmente."
                    )
                }), 400

        operacao.preco_saida = float(preco)
        operacao.preco_atual = operacao.preco_saida
        operacao.data_fechamento = datetime.utcnow()
        operacao.status = "FECHADA"
        operacao.calcular_resultado(operacao.preco_saida)

        db.session.commit()
        return jsonify(operacao.to_dict())

    @app.post("/api/operacoes/atualizar")
    @swag_from({
        "tags": ["Operações"],
        "summary": "Atualiza as cotações das operações abertas",
        "description": "Consulta o Yahoo Finance e recalcula o P&L das posições abertas.",
        "responses": {
            200: {
                "description": "Resultado da atualização",
                "schema": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            }
        },
    })
    def atualizar_operacoes():
        abertas = Operacao.query.filter_by(status="ABERTA").all()
        atualizadas = []

        for operacao in abertas:
            try:
                cotacao = cotacao_atual(operacao.ticker)
                operacao.preco_atual = cotacao["preco"]
                operacao.calcular_resultado()
                atualizadas.append(operacao.to_dict())
            except Exception as exc:
                atualizadas.append({
                    "id": operacao.id,
                    "ticker": operacao.ticker,
                    "erro": str(exc),
                })

        db.session.commit()
        return jsonify(atualizadas)

    # ------------------------------------------------------------------
    # CARTEIRA
    # ------------------------------------------------------------------

    @app.get("/api/carteira/consolidado")
    @swag_from({
        "tags": ["Carteira"],
        "summary": "Retorna o resultado consolidado da carteira",
        "responses": {
            200: {
                "description": "Indicadores consolidados",
                "schema": {
                    "type": "object",
                    "properties": {
                        "resultado_fechado": {"type": "number"},
                        "resultado_aberto": {"type": "number"},
                        "resultado_total": {"type": "number"},
                        "capital_em_posicoes_abertas": {"type": "number"},
                        "operacoes_abertas": {"type": "integer"},
                        "operacoes_fechadas": {"type": "integer"},
                        "operacoes_ganhadoras": {"type": "integer"},
                        "operacoes_perdedoras": {"type": "integer"},
                        "taxa_acerto": {"type": "number"},
                        "profit_factor": {"type": "number"},
                        "maior_ganho": {"type": "number"},
                        "maior_perda": {"type": "number"},
                    },
                },
            }
        },
    })
    def carteira_consolidado():
        return jsonify(consolidado(Operacao.query.all()))

    # ------------------------------------------------------------------
    # ATIVOS
    # ------------------------------------------------------------------

    @app.get("/api/ativos/<ticker>")
    @swag_from({
        "tags": ["Ativos"],
        "summary": "Consulta cotação e fundamentos de um ativo",
        "parameters": [{
            "name": "ticker",
            "in": "path",
            "required": True,
            "type": "string",
            "example": "PETR4",
        }],
        "responses": {
            200: {
                "description": "Cotação e fundamentos",
                "schema": {
                    "type": "object",
                    "properties": {
                        "cotacao": {"type": "object"},
                        "fundamentos": {"type": "object"},
                    },
                },
            },
            404: {"description": "Ativo não encontrado"},
        },
    })
    def dados_ativo(ticker):
        try:
            return jsonify({
                "cotacao": cotacao_atual(ticker),
                "fundamentos": fundamentos(ticker),
            })
        except Exception as exc:
            return jsonify({"erro": str(exc)}), 404

    @app.get("/api/ativos/<ticker>/historico")
    @swag_from({
        "tags": ["Ativos"],
        "summary": "Consulta o histórico de preços de um ativo",
        "parameters": [
            {
                "name": "ticker",
                "in": "path",
                "required": True,
                "type": "string",
                "example": "PETR4",
            },
            {
                "name": "periodo",
                "in": "query",
                "required": False,
                "type": "string",
                "default": "1y",
            },
            {
                "name": "intervalo",
                "in": "query",
                "required": False,
                "type": "string",
                "default": "1d",
            },
        ],
        "responses": {
            200: {
                "description": "Histórico OHLCV",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "string", "format": "date-time"},
                            "abertura": {"type": "number"},
                            "maxima": {"type": "number"},
                            "minima": {"type": "number"},
                            "fechamento": {"type": "number"},
                            "volume": {"type": "number"},
                        },
                    },
                },
            },
            404: {"description": "Histórico não encontrado"},
        },
    })
    def historico_ativo(ticker):
        try:
            periodo = request.args.get("periodo", "1y")
            intervalo = request.args.get("intervalo", "1d")
            return jsonify(historico(ticker, periodo, intervalo))
        except Exception as exc:
            return jsonify({"erro": str(exc)}), 404

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
