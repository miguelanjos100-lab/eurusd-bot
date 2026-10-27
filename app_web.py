import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# Configuração do Telegram
TELEGRAM_TOKEN = "7953258509:AAHgWz1X5J6G0N-0E6F0v8n5s8Z1x2C3v4B"
CHAT_ID = "2124288803"

st.set_page_config(page_title="Cyborg Quant - Multi-Market Dashboard", layout="centered")

st.title("🤖 Cyborg Quant Daemon - Multi-Market Control Panel")
st.write("Seleciona o ativo pretendido e clica no botão para executar a análise, calcular SL/TP e enviar alertas para o Telegram.")

# Seletor de Mercados
selected_ticker = st.selectbox(
    "Escolhe o Ativo para Análise:",
    ("EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "GC=F")
)

def get_macro_bias(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty:
            return 0, 0, 0, 0
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        current_price = float(df['Close'].iloc[-1])
        ema50 = float(df['EMA50'].iloc[-1])
        ema200 = float(df['EMA200'].iloc[-1])
        
        if current_price > ema50 and ema50 > ema200:
            return 1, current_price, ema50, ema200
        elif current_price < ema50 and ema50 < ema200:
            return -1, current_price, ema50, ema200
        else:
            return 0, current_price, ema50, ema200
    except Exception as e:
        st.error(f"Erro no filtro macro: {e}")
        return 0, 0, 0, 0

if st.button(f"🚀 Executar Análise para {selected_ticker}", type="primary"):
    with st.spinner(f"A descarregar dados e a calcular matrizes de risco para {selected_ticker}..."):
        bias, price, e50, e200 = get_macro_bias(selected_ticker)
        bias_label = "BULLISH (ESTRUTURA DE COMPRA)" if bias == 1 else ("BEARISH (ESTRUTURA DE VENDA)" if bias == -1 else "NEUTRO / LATERAL")
        
        st.subheader(f"📊 Estado Atual - {selected_ticker}")
        st.metric(label=f"Preço Atual ({selected_ticker})", value=f"{price:.5f}")
        st.write(f"**Viés Macro Diário:** {bias_label}")
        st.write(f"*(Referência: EMA50 = {e50:.5f} | EMA200 = {e200:.5f})*")

        df = yf.download(selected_ticker, period="5d", interval="30m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
            
        recent_candles = df.tail(12)
        asia_high = float(recent_candles['High'].iloc[:-2].max())
        asia_low = float(recent_candles['Low'].iloc[:-2].min())
        last_close = float(recent_candles['Close'].iloc[-2]) 
        last_high = float(recent_candles['High'].iloc[-1])
        last_low = float(recent_candles['Low'].iloc[-1])

        st.info(f"📍 **Níveis da Sessão:** Máx. Referência: `{asia_high:.5f}` | Mín. Referência: `{asia_low:.5f}`")

        signal_message = None
        
        # Condição Short com SL e TP (Risco/Recompensa 1:2)
        if last_high > asia_high and last_close < asia_high and bias == -1:
            entry_price = last_close
            stop_loss = last_high + 0.0005  # margem técnica acima do varrimento
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * 2.0) # Alvo 1:2
            
            signal_message = (
                f"🚨 *[CYBORG QUANT ALERT]* 🚨\n\n"
                f"*Ativo:* {selected_ticker}\n"
                f"*Direção:* **SHORT (Venda)**\n"
                f"*Filtro Macro:* Bearish (Alinhado)\n\n"
                f"*Entrada (Fecho):* `{entry_price:.5f}`\n"
                f"*Stop Loss (SL):* `{stop_loss:.5f}`\n"
                f"*Take Profit (TP):* `{take_profit:.5f}` (R:R 1:2)"
            )
            st.warning(f"⚠️ **Setup SHORT Detetado em {selected_ticker}! Alerta com SL/TP enviado!**")
            st.write(f"**Plano de Trade:** Entrada: `{entry_price:.5f}` | SL: `{stop_loss:.5f}` | TP: `{take_profit:.5f}`")
            
        # Condição Long com SL e TP (Risco/Recompensa 1:2)
        elif last_low < asia_low and last_close > asia_low and bias == 1:
            entry_price = last_close
            stop_loss = last_low - 0.0005  # margem técnica abaixo do varrimento
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * 2.0) # Alvo 1:2
            
            signal_message = (
                f"🚨 *[CYBORG QUANT ALERT]* 🚨\n\n"
                f"*Ativo:* {selected_ticker}\n"
                f"*Direção:* **LONG (Compra)**\n"
                f"*Filtro Macro:* Bullish (Alinhado)\n\n"
                f"*Entrada (Fecho):* `{entry_price:.5f}`\n"
                f"*Stop Loss (SL):* `{stop_loss:.5f}`\n"
                f"*Take Profit (TP):* `{take_profit:.5f}` (R:R 1:2)"
            )
            st.success(f"✅ **Setup LONG Detetado em {selected_ticker}! Alerta com SL/TP enviado!**")
            st.write(f"**Plano de Trade:** Entrada: `{entry_price:.5f}` | SL: `{stop_loss:.5f}` | TP: `{take_profit:.5f}`")
        else:
            st.write("ℹ️ *Sem padrões de varrimento válidos ou alinhados com o macro neste momento para este ativo.*")

        if signal_message:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": signal_message, "parse_mode": "Markdown"}
            try:
                res = requests.post(url, json=payload)
                if res.status_code == 200:
                    st.toast("Mensagem com SL e TP enviada com sucesso para o Telegram!", icon="🚀")
                else:
                    st.error(f"Erro ao enviar para o Telegram: {res.text}")
            except Exception as ex:
                st.error(f"Erro de rede ao contactar o Telegram: {ex}")
