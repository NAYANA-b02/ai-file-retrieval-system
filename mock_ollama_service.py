import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class MockOllamaHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            payload = json.loads(body)
            messages = payload.get('messages', [])
            user_msg = messages[-1].get('content', '') if messages else ''
        except Exception:
            user_msg = ''

        # Generate a realistic grounded answer based on user query
        if 'latency' in user_msg.lower() or 'elena' in user_msg.lower() or 'researcher' in user_msg.lower():
            response_content = (
                "Based on the provided document context, Dr. Elena Rostova is the Lead Researcher "
                "at the Cybernetics Research Institute. The protocol achieves a handshake latency of "
                "42.7 milliseconds, which is 3.5 times faster than RSA-4096."
            )
        else:
            response_content = "The uploaded documents do not contain enough information to answer this question."

        response_data = {
            "model": "llama3.2:3b",
            "created_at": "2026-09-07T17:45:00Z",
            "message": {
                "role": "assistant",
                "content": response_content
            },
            "done": True
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ollama is running"}).encode('utf-8'))

    def log_message(self, format, *args):
        # Suppress noisy request logging
        pass

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 11434), MockOllamaHandler)
    print("Mock Ollama service running on http://127.0.0.1:11434")
    server.serve_forever()
