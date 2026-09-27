<img width="341" height="108" alt="image" src="https://github.com/user-attachments/assets/0f8a002a-19e4-4600-8e5b-63a53c11b3b5" />

---

O TradeDesk foi desenvolvido para registrar operações de compra e venda na bolsa de valores, acompanhar posições
abertas, consultar cotações e visualizar indicadores consolidados de desempenho.

Ele é o meu MVP da disciplina Arquitetura de Software do curso de Engenharia de Software da PUC-RIO.

Foram criados dois repositórios, um para o backend e outro para o frontend. Você está no repositório da API, o backend.

## Arquitetura
<img width="749" height="310" alt="image" src="https://github.com/user-attachments/assets/6294706f-e935-42ff-96b3-4f0a2a063070" />

O sistema é composto por uma API Principal, onde são registrada as operações, realizados os cálculos para a apuração dos resultados consolidados e o carregamento das informações no banco de dados. A API Principal também recebe as cotações atualizadas da API Externa yfinance (https://github.com/ranaroussi/yfinance), que além das últimas cotações fornece também vários outros dados sobre as ações.

## Instalação da API

1 - Ativar o ambiente virtual com os comandos:
```bash
python -m venv .venv
.venv\Scripts\activate
```
2 - Instalar as bibliotecas requeridas no arquivo requirements.txt com o comando:
```bash
pip install -r requirements.txt
```
## Rodando o Servidor

1 - Para executar a API basta executar:
```bash
(.venv)$ flask run --host 0.0.0.0 --port 5000
```
2 - Abra o http://localhost:5000/#/ no navegador para verificar o status da API em execução

## Como executar através do Docker

Certifique-se de ter o Docker instalado e em execução em sua máquina.

Navegue até o diretório que contém o Dockerfile e o requirements.txt no terminal. Execute como administrador o seguinte comando para construir a imagem Docker:
```bash
$ docker build -t backend .
```
Uma vez criada a imagem, para executar o container basta executar, como administrador, seguinte o comando:
```bash
$ docker run -p 5000:5000 backend
```

Uma vez executando, para acessar a API, basta abrir o http://localhost:5000/#/ no navegador.
