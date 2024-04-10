from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/heartRate', methods=['POST'])
def heart_rate():
    data = request.get_json()  # Parse JSON data from request body
    print("Heart Rate Received: ", data['heartRate'])
    return jsonify(success=True), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
