from app import create_app

app = create_app()

if __name__ == '__main__':
    # Em produção (Render), debug deve ser False para segurança.
    # No Codespace, você pode mudar temporariamente para True se precisar.
    app.run(host='0.0.0.0', port=5000, debug=False)


