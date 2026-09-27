import yfinance as yf

def normalizar_ticker(ticker):
    ticker = ticker.upper().strip()
    # Para ações brasileiras, permite informar PETR4 ou PETR4.SA.
    if "." not in ticker and (ticker.isalpha() or (ticker and ticker[-1].isdigit)):
        ticker = ticker + ".SA"
    return ticker

def cotacao_atual(ticker):
    symbol = normalizar_ticker(ticker)
    t = yf.Ticker(symbol)
    data = t.history(period="1d", interval="1m", auto_adjust=False)
    if data.empty:
        data = t.history(period="5d", interval="1d", auto_adjust=False)
    if data.empty:
        raise ValueError(f"Não foi possível obter cotação para {ticker}")
    row = data.iloc[-1]
    return {
        "ticker": ticker.upper(),
        "symbol": symbol,
        "preco": float(row["Close"]),
        "abertura": float(row["Open"]),
        "maxima": float(row["High"]),
        "minima": float(row["Low"]),
        "volume": float(row["Volume"]),
        "data": data.index[-1].isoformat(),
    }

def historico(ticker, periodo="1y", intervalo="1d"):
    symbol = normalizar_ticker(ticker)
    data = yf.Ticker(symbol).history(period=periodo, interval=intervalo, auto_adjust=False)
    if data.empty:
        raise ValueError(f"Histórico não encontrado para {ticker}")

    resultado = []
    for idx, row in data.iterrows():
        resultado.append({
            "data": idx.isoformat(),
            "abertura": float(row["Open"]),
            "maxima": float(row["High"]),
            "minima": float(row["Low"]),
            "fechamento": float(row["Close"]),
            "volume": float(row["Volume"]),
        })
    return resultado

def fundamentos(ticker):
    symbol = normalizar_ticker(ticker)
    info = yf.Ticker(symbol).info

    campos = [
        "longName", "sector", "industry", "marketCap", "enterpriseValue",
        "trailingPE", "forwardPE", "priceToBook", "dividendYield",
        "returnOnEquity", "returnOnAssets", "profitMargins",
        "operatingMargins", "revenueGrowth", "earningsGrowth",
        "debtToEquity", "currentRatio", "beta", "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow", "targetMeanPrice"
    ]

    return {
        campo: info.get(campo)
        for campo in campos
    }
