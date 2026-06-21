#!/usr/bin/env python3
import cgi
import http.server
import json
from pathlib import Path

PORT = 8080
ROOT = Path(__file__).parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path == '/save-works':
            self._save_works()
        elif self.path == '/upload-media':
            self._upload_media()
        else:
            self.send_response(404)
            self.end_headers()

    def _save_works(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            works = json.loads(body)
            script_path = ROOT / 'script.js'
            content = script_path.read_text(encoding='utf-8')
            marker = '\nfunction getThumb'
            idx = content.index(marker)
            new_content = (
                'const defaultWorks = '
                + json.dumps(works, ensure_ascii=False, indent=2)
                + ';\n'
                + content[idx:]
            )
            script_path.write_text(new_content, encoding='utf-8')
            self._respond(200, {'ok': True})
        except Exception as e:
            self._respond(500, {'error': str(e)})

    def _upload_media(self):
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': self.headers['Content-Type'],
                    'CONTENT_LENGTH': self.headers.get('Content-Length', '0'),
                },
            )
            work_id = form.getvalue('workId', 'unknown')
            work_dir = ROOT / 'assets' / 'works' / work_id
            work_dir.mkdir(parents=True, exist_ok=True)

            saved_paths = []
            thumb_path = None

            if 'files' in form:
                items = form['files']
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    if item.filename:
                        dest = work_dir / item.filename
                        dest.write_bytes(item.file.read())
                        saved_paths.append(f'assets/works/{work_id}/{item.filename}')

            if 'thumb' in form:
                item = form['thumb']
                if item.filename:
                    dest = work_dir / item.filename
                    dest.write_bytes(item.file.read())
                    thumb_path = f'assets/works/{work_id}/{item.filename}'

            self._respond(200, {'paths': saved_paths, 'thumb': thumb_path})
        except Exception as e:
            self._respond(500, {'error': str(e)})

    def _respond(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f'  {args[0]}')


if __name__ == '__main__':
    with http.server.HTTPServer(('', PORT), Handler) as httpd:
        print(f'Dev server → http://localhost:{PORT}')
        httpd.serve_forever()
