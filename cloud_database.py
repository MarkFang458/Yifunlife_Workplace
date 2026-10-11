"""Transactional SQLite compatibility over an external Cloudflare database service.

Each connection reads one consistent remote snapshot. Statements execute against an
isolated in-memory replica, then commit atomically with a remote revision check.
No business database is persisted on the application container's filesystem.
"""
import base64
import json
import os
import sqlite3
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class ConcurrentUpdate(sqlite3.OperationalError):
    pass


def encode(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'$bytes': base64.b64encode(value).decode('ascii')}
    return value


def decode(value):
    return base64.b64decode(value['$bytes'], validate=True) if isinstance(value, dict) and set(value) == {'$bytes'} else value


def request(path, payload=None):
    endpoint = os.environ.get('YIFUN_DATABASE_ENDPOINT', '').rstrip('/')
    token = os.environ.get('YIFUN_DATABASE_TOKEN', '')
    parsed = urlsplit(endpoint)
    private_binding = os.environ.get('YIFUN_CONTAINER_MODE') == '1' and endpoint == 'http://database.yifun.internal'
    if not private_binding and (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or not token):
        raise RuntimeError('Cloud database endpoint and private service authentication are required')
    body = None if payload is None else json.dumps(payload, separators=(',', ':')).encode()
    headers = {'Content-Type': 'application/json'}
    if not private_binding:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(endpoint + path, data=body, headers=headers,
        method='GET' if payload is None else 'POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            raise ConcurrentUpdate('资料已被另一位用户更新，请刷新后重试') from None
        if exc.code == 422:
            raise sqlite3.IntegrityError('云数据库拒绝了不符合约束的资料') from None
        raise sqlite3.OperationalError('云数据库暂时不可用，未确认保存') from None
    except (OSError, TimeoutError):
        raise sqlite3.OperationalError('云数据库暂时不可用，未确认保存') from None
    if len(raw) > 32 * 1024 * 1024:
        raise sqlite3.OperationalError('Cloud snapshot exceeds the tested size limit')
    return json.loads(raw)


def statements(script):
    pending = ''
    for character in script:
        pending += character
        if character == ';' and sqlite3.complete_statement(pending):
            yield pending
            pending = ''
    if pending.strip():
        yield pending


class Connection(sqlite3.Connection):
    def __init__(self):
        super().__init__(':memory:', timeout=20)
        self.row_factory = sqlite3.Row
        self._pending = []
        self._failed = False
        snapshot = request('/snapshot')
        self._revision = snapshot['revision']
        # Restore data before installing triggers, so opening a connection does
        # not duplicate inventory, audit, or other trigger effects.
        super().execute('PRAGMA foreign_keys=OFF')
        for item in snapshot['schema']:
            if item['type'] == 'table':
                super().execute(item['sql'])
        for table in snapshot['tables']:
            quoted = '"' + table['name'].replace('"', '""') + '"'
            if table['name'] == 'sqlite_sequence':
                super().execute('DELETE FROM sqlite_sequence')
            columns = ','.join('"' + name.replace('"', '""') + '"' for name in table['columns'])
            if table['rows']:
                super().executemany(f'INSERT INTO {quoted} ({columns}) VALUES ({",".join("?" for _ in table["columns"])})',
                                    [[decode(value) for value in row] for row in table['rows']])
        for item in snapshot['schema']:
            if item['type'] != 'table':
                super().execute(item['sql'])
        super().commit()
        super().execute('PRAGMA foreign_keys=ON')

    def execute(self, sql, parameters=()):
        if self._failed:
            raise sqlite3.OperationalError('Cloud connection must be reopened after an uncertain commit')
        parameters = tuple(parameters)
        cursor = super().execute(sql, parameters)
        command = sql.lstrip().split(None, 1)[0].upper().rstrip(';')
        if command not in {'SELECT', 'PRAGMA', 'BEGIN', 'COMMIT', 'ROLLBACK', 'END'}:
            self._pending.append({'sql': sql, 'params': [encode(value) for value in parameters]})
        return cursor

    def executemany(self, sql, parameters):
        cursor = None
        for values in parameters:
            cursor = self.execute(sql, values)
        return cursor or super().execute('SELECT 1 WHERE 0')

    def executescript(self, script):
        self.commit()
        cursor = None
        for sql in statements(script):
            # Scripts in the original migrations wrap their own transaction.
            # The external service commits the entire script atomically.
            stripped = sql.lstrip()
            while stripped.startswith('--'):
                stripped = stripped.partition('\n')[2].lstrip()
            command = stripped.split(None, 1)[0].upper().rstrip(';') if stripped else ''
            if command in {'BEGIN', 'COMMIT', 'END'}:
                continue
            cursor = self.execute(sql)
        self.commit()
        return cursor or super().execute('SELECT 1 WHERE 0')

    def commit(self):
        if self._pending:
            try:
                result = request('/commit', {'revision': self._revision, 'statements': self._pending})
            except Exception:
                super().rollback()
                self._pending.clear()
                self._failed = True
                raise
            self._revision = result['revision']
            self._pending.clear()
        return super().commit()

    def rollback(self):
        self._pending.clear()
        return super().rollback()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.rollback() if exc_type else self.commit()
        finally:
            self.close()
        return False
