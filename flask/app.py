from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('main.html', title='Flask App', content='Hello, Flask!')

if __name__ == '__main__':
    app.run(debug=True)
