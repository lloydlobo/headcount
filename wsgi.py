from waitress import serve

from server.main import app

if __name__ == "__main__":
    """
    run your application using Waitress: 
        python wsgi.py
        
    production like:
        waitress-serve --listen=*:8000 wsgi:app
    """
    # app.run(debug=True)
    serve(app, host="0.0.0.0", port=5000)
