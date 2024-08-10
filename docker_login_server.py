import os
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import threading

class CustomHandler(SimpleHTTPRequestHandler):
    containers = {}

    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_qs(post_data.decode('utf-8'))

            username = data.get('username', [''])[0]
            password = data.get('password', [''])[0]

            if username and password:
                container_id = self.create_docker_container(username, password)
                if container_id:
                    self.containers[username] = container_id
                    # Redirect to the shell page
                    self.send_response(302)
                    self.send_header('Location', f'/shell?container_id={container_id}')
                    self.end_headers()
                else:
                    self.send_error(500, "Failed to create Docker container")
            else:
                self.send_error(400, "Username and password required")

        elif self.path == '/logout':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_qs(post_data.decode('utf-8'))
            container_id = data.get('container_id', [''])[0]

            if container_id:
                self.stop_and_remove_container(container_id)
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<html><body><h2>You have been logged out and your container has been removed.</h2></body></html>")

    def do_GET(self):
        if self.path.startswith('/shell'):
            container_id = self.path.split('=')[1]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(f"""
                <html>
                <body>
                    <h2>Shell for Container {container_id}</h2>
                    <pre id="shell-output"></pre>
                    <input type="text" id="shell-input" placeholder="Type command here">
                    <button onclick="sendCommand()">Send</button>
                    <form action="/logout" method="post">
                        <input type="hidden" name="container_id" value="{container_id}">
                        <input type="submit" value="Logout">
                    </form>
                    <script>
                        function sendCommand() {{
                            var input = document.getElementById("shell-input").value;
                            var xhr = new XMLHttpRequest();
                            xhr.open("POST", "/exec?container_id={container_id}", true);
                            xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
                            xhr.onreadystatechange = function() {{
                                if (xhr.readyState == 4 && xhr.status == 200) {{
                                    document.getElementById("shell-output").innerHTML += xhr.responseText + "\\n";
                                    document.getElementById("shell-input").value = "";
                                }}
                            }};
                            xhr.send("command=" + encodeURIComponent(input));
                        }}
                    </script>
                </body>
                </html>""", 'utf-8'))

        elif self.path.startswith('/exec'):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_qs(post_data.decode('utf-8'))
            container_id = data.get('container_id', [''])[0]
            command = data.get('command', [''])[0]

            if container_id and command:
                result = subprocess.run(['docker', 'exec', container_id, 'sh', '-c', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(result.stdout + result.stderr)

    def create_docker_container(self, username, password):
        try:
            result = subprocess.run([
                'docker', 'run', '-d', '-t', '--rm',
                '--name', username,
                '-e', f'USER={username}',
                '-e', f'PASSWORD={password}',
                'ubuntu'
            ], stdout=subprocess.PIPE)
            return result.stdout.decode('utf-8').strip()
        except Exception as e:
            print(f"Error creating Docker container: {e}")
            return None

    def stop_and_remove_container(self, container_id):
        try:
            subprocess.run(['docker', 'stop', container_id])
        except Exception as e:
            print(f"Error stopping/removing Docker container: {e}")

if __name__ == "__main__":
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, CustomHandler)
    print('Running server...')
    threading.Thread(target=httpd.serve_forever).start()
