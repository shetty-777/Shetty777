from website import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
    #app.run(debug=True, port=7000)
