"""Local unified Workplace service. Bind to loopback; no production credentials."""
import hashlib,hmac,json,secrets,time,sqlite3,mimetypes,logging,os
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from datetime import datetime,timezone
from pathlib import Path
import database,core
import project_access as access
import ceo_dashboard
import operations
import centers
import connections
ROOT=database.ROOT
PORT=int(os.environ.get('YIFUN_PORT','8975'))
BRIDGE_PATH=database.DATA_ROOT/'secrets/bridge.key'
ROLES={'admin':['quote','procurement','aftersales'],'ceo':['quote','procurement','aftersales'],'sales':['quote','aftersales'],'purchasing':['procurement'],'engineering':['procurement'],'warehouse':['procurement'],'aftersales':['aftersales'],'finance':['procurement'],'supplier':['procurement'],'installation':[]}

def init():
    database.init()
    BRIDGE_PATH.parent.mkdir(parents=True,exist_ok=True)
    if not BRIDGE_PATH.exists():
        BRIDGE_PATH.write_text(secrets.token_urlsafe(48));BRIDGE_PATH.chmod(0o600)

def password_hash(password,salt):return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),300000).hex()
def public(user):return {k:user[k] for k in ('id','email','name','role','status','supplier_id')}
def password(value):
    if not isinstance(value,str) or not 10<=len(value)<=256:raise core.Problem('密码须为 10 至 256 位')
    return value

def add_employee(db,p,setup=False):
    email=core.text(p.get('email'),'邮箱').lower()
    if '@' not in email or len(email)>254:raise core.Problem('请填写有效邮箱')
    role='admin' if setup else p.get('role')
    if role not in ROLES:raise core.Problem('请选择有效岗位')
    supplier=p.get('supplier_id') or None
    if role=='supplier':core.need(db,'suppliers',supplier)
    else:supplier=None
    salt=secrets.token_hex(16);key=core.uid();secret=password(p.get('password'))
    db.execute('INSERT INTO employees VALUES(?,?,?,?,?,?,?,?,?)',(key,email,core.text(p.get('name'),'姓名'),role,supplier,'active',password_hash(secret,salt),salt,core.now()))
    return core.need(db,'employees',key)

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,fmt,*args):
        if args and ('/internal/database' in str(args[0]) or '/api/internal/session' in str(args[0])):return
        logging.info('%s %s',self.address_string(),fmt%args)
    def allowed(self):return self.headers.get('Host','') in (f'127.0.0.1:{PORT}',f'localhost:{PORT}')
    def bridge(self):return hmac.compare_digest(self.headers.get('X-Workspace-Bridge',''),BRIDGE_PATH.read_text())
    def session(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''));token=cookie.get('workplace_complete_session')
        except Exception:return None
        if not token:
            config = ROOT/'data/local-admin.json'
            if not config.exists() or self.client_address[0] != '127.0.0.1' or not self.allowed():
                return None
            origin = self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
                return None
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return None
            with database.connect() as db:
                user = core.row(db, "SELECT * FROM employees WHERE id=? AND role='admin' AND status='active'", (json.loads(config.read_text())['user_id'],))
                if not user:return None
                raw = secrets.token_urlsafe(32)
                digest = hashlib.sha256(raw.encode()).hexdigest()
                csrf = secrets.token_urlsafe(32)
                expires = time.time()+8*3600
                db.execute('INSERT INTO employee_sessions(token_hash,user_id,expires,csrf) VALUES(?,?,?,?)', (digest,user['id'],expires,csrf))
                user.update(token_hash=digest, csrf=csrf, expires=expires, project_id=None, quote_kind='original', parent_order_id=None)
            self.cookie_out=f'workplace_complete_session={raw}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'
            return user
        digest=hashlib.sha256(token.value.encode()).hexdigest()
        with database.connect() as db:
            user=core.row(db,"SELECT e.*,s.token_hash,s.csrf,s.project_id,s.quote_kind,s.parent_order_id,s.expires FROM employee_sessions s JOIN employees e ON e.id=s.user_id WHERE s.token_hash=? AND e.status='active' AND s.expires>?",(digest,time.time()))
            if not user and (ROOT/'data/local-admin.json').exists():
                del self.headers['Cookie']
                return self.session()
            if user and user['project_id'] and not access.visible_project(db,user,user['project_id']):
                user.update(project_id=None,quote_kind='original',parent_order_id=None)
            return user
    def respond(self,status,body,mime='application/json; charset=utf-8'):
        raw=json.dumps(body,ensure_ascii=False).encode() if isinstance(body,(dict,list)) else body
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src http://127.0.0.1:8991 http://127.0.0.1:8992 http://127.0.0.1:8993; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")
        if getattr(self,'attachment_name',None):
            from urllib.parse import quote
            self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(self.attachment_name))
        if getattr(self,'cookie_out',None):self.send_header('Set-Cookie',self.cookie_out)
        self.end_headers();self.wfile.write(raw)
    def read_json(self):
        size=int(self.headers.get('Content-Length','0'))
        if not 0<size<=20*1024*1024:raise core.Problem('提交内容为空或超过 20 MB')
        p=json.loads(self.rfile.read(size))
        if not isinstance(p,dict):raise core.Problem('请求格式不正确')
        return p
    def dispatch(self):
        self.cookie_out=None
        self.attachment_name=None
        try:
            if not self.allowed():raise core.Problem('仅允许本机访问',403)
            path=urlparse(self.path).path;method=self.command
            if method=='GET':return self.get(path)
            if method!='POST':raise core.Problem('接口不存在',404)
            p=self.read_json()
            if path=='/internal/database':
                if not self.bridge():raise core.Problem('来源无效',403)
                return self.respond(200,{'results':database.d1_batch(p.get('statements'))})
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):raise core.Problem('不允许跨站提交',403)
            if path in ('/api/auth/setup','/api/auth/login'):return self.authenticate(path,p)
            user=self.session()
            if not user:raise core.Problem('请先登录统一工作平台',401)
            if not self.bridge() and not hmac.compare_digest(self.headers.get('X-Yifun-Token',''),user['csrf']):raise core.Problem('会话已失效，请刷新后重试',403)
            if path=='/api/auth/logout':
                with database.connect() as db:db.execute('DELETE FROM employee_sessions WHERE token_hash=?',(user['token_hash'],))
                self.cookie_out='workplace_complete_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0';return self.respond(200,{'ok':True})
            if path=='/api/context':
                with database.connect() as db:
                    project=access.require(db,user,'projects',p.get('project_id')) if p.get('project_id') else None
                    kind=p.get('quote_kind','original');parent=p.get('parent_order_id') or None
                    if kind not in ('original','addition'):raise core.Problem('报价类型无效')
                    if kind=='addition':
                        b=core.need(db,'order_baselines',parent)
                        if not project or b['project_id']!=project['id']:raise core.Problem('请选择该原订单对应的项目')
                    else:parent=None
                    db.execute('UPDATE employee_sessions SET project_id=?,quote_kind=?,parent_order_id=? WHERE token_hash=?',(project['id'] if project else None,kind,parent,user['token_hash']))
                return self.respond(200,{'ok':True})
            if path=='/api/employees':
                core.permit(user,'admin')
                with database.connect() as db:
                    db.execute('BEGIN IMMEDIATE');employee=add_employee(db,p);core.audit(db,user,'employee',employee['id'],'创建员工',public(employee))
                return self.respond(201,{'user':public(employee)})
            if path=='/api/employee-status':
                core.permit(user,'admin')
                with database.connect() as db:
                    employee=core.need(db,'employees',p.get('id'));status=p.get('status')
                    if employee['id']==user['id']:raise core.Problem('不能停用自己的管理账号')
                    if status not in ('active','disabled'):raise core.Problem('状态无效')
                    db.execute('UPDATE employees SET status=? WHERE id=?',(status,employee['id']));db.execute('DELETE FROM employee_sessions WHERE user_id=?',(employee['id'],));core.audit(db,user,'employee',employee['id'],'更新账号状态',{'status':status})
                return self.respond(200,{'ok':True})
            if path=='/api/password':
                if not hmac.compare_digest(password_hash(password(p.get('current')),user['salt']),user['password_hash']):raise core.Problem('原密码不正确',403)
                salt=secrets.token_hex(16)
                with database.connect() as db:db.execute('UPDATE employees SET password_hash=?,salt=? WHERE id=?',(password_hash(password(p.get('password')),salt),salt,user['id']));db.execute('DELETE FROM employee_sessions WHERE user_id=? AND token_hash!=?',(user['id'],user['token_hash']))
                return self.respond(200,{'ok':True})
            if path=='/api/connections/sync':
                core.permit(user,'admin')
                import threading
                threading.Thread(target=connections.sync,daemon=True).start()
                return self.respond(202,{'ok':True})
            if path=='/api/connections/quote-context':
                core.permit(user,'admin','ceo','sales')
                with database.connect() as db:
                    project=access.require(db,user,'projects',p.get('project_id'))
                    projects=connections.project_payload(db)
                connections.remote(connections.configuration(),'/api/workplace-sync',{'projects':projects})
                from urllib.parse import quote
                return self.respond(200,{'url':connections.ORIGIN+'/?workplaceProject='+quote(project['id'])})
            if path=='/api/connections/link':
                with database.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    result=connections.action(db,user,'link',p)
                return self.respond(200,result)
            if path.startswith('/api/ops/action/'):
                with database.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    result=operations.execute(db,user,path.rsplit('/',1)[1],p)
                return self.respond(200,result)
            if path.startswith('/api/centers/action/'):
                with database.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    result=centers.execute(db,user,path.rsplit('/',1)[1],p)
                return self.respond(200,result)
            if path.startswith('/api/action/'):
                return self.respond(200,core.mutate(user,path.rsplit('/',1)[1],p))
            raise core.Problem('接口不存在',404)
        except core.Problem as e:self.respond(e.status,{'error':e.message})
        except sqlite3.IntegrityError as e:
            message=str(e);self.respond(409,{'error':'编号或凭证已存在，请刷新核对' if 'UNIQUE' in message else message if any('\u4e00'<=c<='\u9fff' for c in message) else '关联资料或数量不符合规则，请核对后重试'})
        except (ValueError,TypeError,KeyError) as e:
            logging.exception('Invalid request');self.respond(400,{'error':'资料格式不完整，请刷新并核对必填项'})
        except Exception:
            logging.exception('Request failed');self.respond(500,{'error':'未能完成操作，资料未确认保存。请查看本地运行日志后重试'})
    def get(self,path):
        assets={'/dashboard.css':'dashboard.css','/operations.js':'operations.js','/operations.css':'operations.css','/':'workplace.html','/workplace.js':'workplace.js','/dashboard.js':'dashboard.js','/workplace.css':'workplace.css','/workplace-theme.css':'workplace-theme.css','/workplace-logo.png':'workplace-logo.png','/workplace-favicon.svg':'workplace-favicon.svg','/workplace-favicon.png':'workplace-favicon.png'}
        if path in assets:
            file=ROOT/assets[path];return self.respond(200,file.read_bytes(),mimetypes.guess_type(file)[0] or 'application/octet-stream')
        if path in ('/centers.js','/centers.css','/connections.js'):
            return self.respond(200,(ROOT/path[1:]).read_bytes(),mimetypes.guess_type(path)[0])
        user=self.session()
        if path=='/api/auth/session':
            with database.connect() as db:
                setup=db.execute('SELECT COUNT(*) FROM employees').fetchone()[0]==0
                department_centers=centers.available(db,user) if user else []
            return self.respond(200,{'authenticated':bool(user),'needsSetup':setup,'user':public(user) if user else None,'csrf':user['csrf'] if user else None,'project_id':user['project_id'] if user else None,'modules':ROLES.get(user['role'],[]) if user else [],'centers':department_centers})
        if not user:raise core.Problem('请先登录统一工作平台',401)
        if path=='/api/connections':
            with database.connect() as db:
                result=connections.status(db,user,parse_qs(urlparse(self.path).query).get('project',[None])[0])
            return self.respond(200,result)
        if path=='/api/connections/sales-project':
            source=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            with database.connect() as db:
                record=core.row(db,'SELECT customer_id,project_id FROM connected_sales WHERE source_id=? AND active=1',(source,))
                if not record:raise core.Problem('客户尚未同步，请在连接资料中刷新后重试',404)
                access.require(db,user,'customers',record['customer_id'])
            return self.respond(200,record)
        if path=='/api/internal/session':
            if not self.bridge():raise core.Problem('来源无效',403)
            module=parse_qs(urlparse(self.path).query).get('module',[''])[0]
            if module not in ROLES[user['role']]:raise core.Problem('没有此中心的使用权限',403)
            with database.connect() as db:
                enabled=core.setting(db,'finance_enabled')=='1'
                if user['role']=='finance' and not enabled:raise core.Problem('财务功能暂未开放',403)
                project=core.row(db,'SELECT p.*,c.name customer_name,c.contact,c.phone,c.email FROM projects p JOIN customers c ON c.id=p.customer_id WHERE p.id=?',(user['project_id'],))
                if project and not access.visible_project(db,user,project['id']):project=None
                ids=access.project_ids(db,user)
                order_ids=[r['id'] for r in db.execute('SELECT id FROM purchase_orders') if access.visible_order(db,user,r['id'])] if module=='procurement' else []
                if module=='procurement':core.shadow_user(db,user)
            return self.respond(200,{'user':public(user),'project':project,'project_ids':ids,'order_ids':order_ids,'finance_enabled':enabled,'quote_kind':user['quote_kind'],'parent_order_id':user['parent_order_id'],'expiresAt':datetime.fromtimestamp(user['expires'],timezone.utc).isoformat()})
        if path=='/api/internal/access':
            if not self.bridge():raise core.Problem('来源无效',403)
            query=parse_qs(urlparse(self.path).query)
            with database.connect() as db:access.require(db,user,query.get('entity',[''])[0],query.get('id',[''])[0])
            return self.respond(200,{'ok':True})
        if path=='/api/employees':
            core.permit(user,'admin')
            with database.connect() as db:
                employees=[public(dict(r)) for r in db.execute('SELECT * FROM employees ORDER BY created_at')]
                for employee in employees:employee['centers']=[r[0] for r in db.execute('SELECT center FROM center_members WHERE employee_id=?',(employee['id'],))]
            return self.respond(200,{'items':employees})
        if path in ('/api/centers/dashboard','/api/centers/records'):
            query=parse_qs(urlparse(self.path).query);q=lambda key,default=None:query.get(key,[default])[0]
            with database.connect() as db:
                result=centers.dashboard(db,user,q('center'),q('from'),q('to'),q('project'),q('currency','CNY')) if path.endswith('/dashboard') else centers.records(db,user,q('page'),q('project'))
            return self.respond(200,result)
        if path=='/api/centers/followups':
            query=parse_qs(urlparse(self.path).query);entity=query.get('entity',[''])[0];key=query.get('id',[''])[0]
            if entity not in ('leads','opportunities'):raise core.Problem('记录类型无效')
            with database.connect() as db:
                operations.get_record(db,user,entity,key)
                items=[dict(r) for r in db.execute('SELECT f.*,e.name actor_name FROM crm_followups f JOIN employees e ON e.id=f.created_by WHERE entity=? AND entity_id=? ORDER BY contact_date DESC,f.created_at DESC,f.rowid DESC',(entity,key))]
            return self.respond(200,{'items':items})
        if path=='/api/ops/view':
            query=parse_qs(urlparse(self.path).query)
            with database.connect() as db:result=operations.view(db,user,query.get('page',[''])[0],query.get('project',[None])[0])
            return self.respond(200,result)
        if path.startswith('/api/ops/file/'):
            with database.connect() as db:r=operations.file(db,user,path.rsplit('/',1)[1])
            self.attachment_name=r['file_name']
            return self.respond(200,r['content'],r['mime'])
        if path in ('/api/dashboard','/api/dashboard/export'):
            query=parse_qs(urlparse(self.path).query)
            with database.connect() as db:result=ceo_dashboard.dashboard(db,user,query.get('from',[None])[0],query.get('to',[None])[0],project_id=query.get('project',[None])[0])
            if path.endswith('/export'):
                tab=query.get('tab',['overview'])[0]
                content=ceo_dashboard.ceo_finance.export_csv(result,tab)
                self.attachment_name='CEO-'+('资金分析' if tab=='finance' else '经营总况')+'-'+result['period']['to']+'.csv'
                return self.respond(200,content,'text/csv; charset=utf-8')
            return self.respond(200,result)
        if path=='/api/service-state':
            with database.connect() as db:result=core.service_view(db,user)
            return self.respond(200,result)
        if path=='/api/change-purchases':
            core.permit(user,'purchasing','sales','admin','ceo');key=parse_qs(urlparse(self.path).query).get('id',[''])[0]
            with database.connect() as db:
                c=access.require(db,user,'order_changes',key)
                items=[dict(r) for r in db.execute('SELECT i.id,i.product_name,i.quantity,i.unit_price,i.shipped_quantity,i.received_quantity,o.po_number FROM procurement_allocations a JOIN order_items i ON i.id=a.order_item_id JOIN purchase_orders o ON o.id=i.order_id WHERE a.baseline_line_id=? AND o.archived_at IS NULL',(c['baseline_line_id'],))]
            return self.respond(200,{'items':items})
        if path.startswith('/api/view/'):
            project=parse_qs(urlparse(self.path).query).get('project',[''])[0] or None
            with database.connect() as db:result=core.view(db,user,path.rsplit('/',1)[1],project)
            return self.respond(200,result)
        raise core.Problem('页面不存在',404)
    def authenticate(self,path,p):
        email=core.text(p.get('email'),'邮箱').lower();secret=password(p.get('password'));stamp=time.time()
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if path.endswith('/setup'):
                if db.execute('SELECT COUNT(*) FROM employees').fetchone()[0]:raise core.Problem('管理员已建立，请登录',409)
                user=add_employee(db,p,True);core.audit(db,user,'employee',user['id'],'初始化管理员',{})
            else:
                attempts=core.row(db,'SELECT * FROM login_attempts WHERE email=?',(email,))
                if attempts and attempts['expires']>stamp and attempts['count']>=8:raise core.Problem('尝试次数过多，请 15 分钟后重试',429)
                user=core.row(db,"SELECT * FROM employees WHERE email=? AND status='active'",(email,))
                valid=user and hmac.compare_digest(password_hash(secret,user['salt']),user['password_hash'])
                if not valid:
                    db.execute('INSERT INTO login_attempts VALUES(?,1,?) ON CONFLICT(email) DO UPDATE SET count=CASE WHEN expires<? THEN 1 ELSE count+1 END,expires=?',(email,stamp+900,stamp,stamp+900));db.commit();raise core.Problem('邮箱或密码不正确',401)
                db.execute('DELETE FROM login_attempts WHERE email=?',(email,))
            token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
            db.execute('DELETE FROM employee_sessions WHERE expires<?',(stamp,))
            db.execute('INSERT INTO employee_sessions(token_hash,user_id,expires,csrf) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],stamp+8*3600,csrf))
        self.cookie_out=f'workplace_complete_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'
        self.respond(200,{'ok':True,'user':public(user),'csrf':csrf})
    do_GET=dispatch
    do_POST=dispatch
    do_PUT=dispatch
    do_DELETE=dispatch

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s');init()
    print(f'YIFUN Workplace V2：http://127.0.0.1:{PORT}',flush=True)
    connections.start()
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
