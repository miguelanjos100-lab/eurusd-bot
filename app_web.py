import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# Configuração do Telegram com os teus dados integrados
TELEGRAM_TOKEN = "7953258509:AAHgWz1X5J6G0N-0E6F0v8n5s8Z1x2C3v4B"
CHAT_ID = "2124288803"

st.set_page_config(page_title="Cyborg Quant - EUR/USD Dashboard", layout="centered")

st.title("🤖 Cyborg Quant Daemon - EUR/USD Control Panel")
st.write("Clica no botão abaixo para atualizar os dados de mercado, cruzar o filtro macro com o varrimento de liquidez e enviar o sinal para o Telegram.")

def get_macro_bias(ticker="EURUSD=X"):
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

if st.button("🚀 Executar Análise e Verificar Sinais EUR/USD", type="primary"):
    with st.spinner("A descarregar dados na nuvem e a calcular matrizes de liquidez..."):
        bias, price, e50, e200 = get_macro_bias("EURUSD=X")
        bias_label = "BULLISH (ESTRUTURA DE COMPRA)" if bias == 1 else ("BEARISH (ESTRUTURA DE VENDA)" if bias == -1 else "NEUTRO / LATERAL")
        
        st.subheader("📊 Estado Atual do Mercado")
        st.metric(label="Preço Atual EUR/USD", value=f"{price:.5f}")
        st.write(f"**Viés Macro Diário:** {bias_label}")
        st.write(f"*(Referência: EMA50 = {e50:.5f} | EMA200 = {e200:.5f})*")

        df = yf.download("EURUSD=X", period="5d", interval="30m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
            
        recent_candles = df.tail(12)
        asia_high = float(recent_candles['High'].iloc[:-2].max())
        asia_low = float(recent_candles['Low'].iloc[:-2].min())
        last_close = float(recent_candles['Close'].iloc[-2]) 
        last_high = float(recent_candles['High'].iloc[-1])
        last_low = float(recent_candles['Low'].iloc[-1])

        st.info(f"📍 **Níveis da Sessão:** Máx. Asiático: `{asia_high:.5f}` | Mín. Asiático: `{asia_low:.5f}`")

        signal_message = None
        if last_high > asia_high and last_close < asia_high and bias == -1:
            signal_message = (
                f"🚨 *[CYBORG QUANT ALERT]* 🚨\n\n"
                f"*Ativo:* EUR/USD\n"
                f"*Direção:* **SHORT (Venda)**\n"
                f"*Filtro Macro:* Bearish (Alinhado)\n"
                f"*Gatilho:* Varrimento de liquidez acima do máximo ({asia_high:.5f}) com rejeição.\n"
                f"*Preço de Fecho:* {last_close:.5f}"
            )
            st.warning("⚠️ **Setup SHORT Detetado e Alerta Disparado!**")
            
        elif last_low < asia_low and last_close > asia_low and bias == 1:
            signal_message = (
                f"🚨 *[CYBORG QUANT ALERT]* 🚨\n\n"
                f"*Ativo:* EUR/USD\n"
                f"*Direção:* **LONG (Compra)**\n"
                f"*Filtro Macro:* Bullish (Alinhado)\n"
                f"*Gatilho:* Varrimento de liquidez abaixo do mínimo ({asia_low:.5f}) com rejeição.\n"
                f"*Preço de Fecho:* {last_close:.5f}"
            )
            st.success("✅ **Setup LONG Detetado e Alerta Disparado!**")
        else:
            st.write("ℹ️ *Sem padrões de varrimento válidos ou alinhados com o macro neste momento. O mercado mantém-se em digestão.*")

        if signal_message:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": CHAT_ID, "text": signal_message, "parse_mode": "Markdown"}
            try:
                res = requests.post(url, json=payload)
                if res.status_code == 200:
                    st.toast("Mensagem enviada com sucesso para o Telegram!", icon="🚀")
                else:
                    st.error(f"Erro ao enviar para o Telegram: {res.text}")
            except Exception as ex:
                st.error(f"Erro de rede ao contactar o Telegram: {ex}")
