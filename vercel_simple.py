from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html><body style="margin:40px;font-family:Arial">
        <h1>🛡️ CyberGuard NG</h1>
        <input id="code" value="*901#"><button onclick="check()">Check</button>
        <div id="result"></div>
        <script>
            async function check() {
                const response = await fetch('/check', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code: document.getElementById('code').value})
                });
                const result = await response.json();
                document.getElementById('result').textContent = result.message;
            }
        </script>
    </body></html>
    '''

@app.route('/check', methods=['POST'])
def check():
    code = request.json.get('code', '')
    if '*901#' in code:
        return jsonify({'message': '✅ SAFE - Legitimate code'})
    else:
        return jsonify({'message': '⚠️ Check with provider'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
else:
    application = app
