mkdir -p ~/.streamlit/
echo "[general]  
echo "[server]
headless = true
port = $PORT
enableCORS = false"  >> ~/.streamlit/config.toml
