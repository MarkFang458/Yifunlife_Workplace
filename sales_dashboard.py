"""Sales lifecycle view of authorized shared records; no preview fixtures."""
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import project_access as access
from ceo_dashboard import local_day


def report(db, user, projects, orders, quotes, start, end, today):
    employees = {r['id']: dict(r) for r in db.execute('SELECT id,name,role,status FROM employees')}
    rows = lambda table: [dict(r) for r in db.execute('SELECT * FROM '+table) if r['project_id'] in projects]
    designs, engineers, tasks, tickets = (rows(t) for t in ('design_tasks','engineering_orders','work_tasks','service_tickets'))
    countries = {}
    for r in db.execute('SELECT project_id,payload FROM connected_sales WHERE active=1'):
        if r['project_id'] in projects:
            countries[r['project_id']] = json.loads(r['payload']).get('country','')
    def market(p):
        country = str(countries.get(p['id']) or p['location'] or '').strip().lower().replace(' ','')
        if not country or country in ('待确认','unknown','未填写'): return 'unknown'
        return 'domestic' if country in ('cn','chn','china','中国','中国大陆','prc','中华人民共和国','mainlandchina') else 'foreign'
    def totals(records):
        out = defaultdict(int)
        for r in records: out[r['currency']] += r['agreed_minor']
        return dict(out)
    def rmb(amounts):
        return amounts.get('CNY',0)+int((Decimal(amounts.get('USD',0))*Decimal('6.8')).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    def period(r):
        day = local_day(r.get('assigned_at') or r['created_at'])
        return bool(day and start <= day.isoformat() <= end)
    purchases = [dict(r) for r in db.execute('''SELECT po.*,pc.project_id FROM purchase_orders po
        JOIN procurement_context pc ON pc.order_id=po.id WHERE po.archived_at IS NULL''') if r['project_id'] in projects and access.visible_order(db,user,r['id'])]
    purchase_ids = {p['id'] for p in purchases}
    items = [dict(r) for r in db.execute('SELECT * FROM order_items') if r['order_id'] in purchase_ids]
    def person(key): return employees.get(key,{}).get('name') or '待分配'
    customer_orders = defaultdict(list)
    for o in orders: customer_orders[projects[o['project_id']]['customer_id']].append(o)
    output = []
    for pid,p in projects.items():
        signed=[o for o in orders if o['project_id']==pid]
        design=sorted([d for d in designs if d['project_id']==pid and d['status']!='cancelled'],key=lambda d:d['updated_at'],reverse=True)
        engineering=sorted([e for e in engineers if e['project_id']==pid],key=lambda e:e['created_at'],reverse=True)
        buying=[b for b in purchases if b['project_id']==pid]
        lines=[i for i in items if i['order_id'] in {b['id'] for b in buying}]
        installations=[t for t in tasks if t['project_id']==pid and t['kind']=='installation']
        active_design=any(d['status'] not in ('accepted','confirmed','handoff') for d in design)
        production=any(i.get('workflow_stage')=='in_production' for i in lines)
        installation=any(t['status'] in ('in_progress','awaiting_acceptance') for t in installations)
        quote=next((q for q in quotes if q['project_id']==pid),None)
        shipment=defaultdict(lambda:{'total':0,'shipped':0})
        for i in lines:
            unit=i.get('unit') or '未标单位'
            shipment[unit]['total']+=i['quantity'];shipment[unit]['shipped']+=i['shipped_quantity']
        deadlines=[b['promised_ship_date'] or b['required_ship_date'] for b in buying if b['promised_ship_date'] or b['required_ship_date']]
        due=min(deadlines) if deadlines else None
        alerts=[]
        if due and due<today and any(i['shipped_quantity']<i['quantity'] for i in lines):alerts.append('发货逾期')
        if any(d['due_date'] and d['due_date']<today and d['status'] not in ('confirmed','handoff','accepted') for d in design):alerts.append('设计逾期')
        if any(t['due_date']<today and t['status']!='accepted' for t in installations):alerts.append('安装待推进')
        owner=db.execute("SELECT employee_id FROM project_members WHERE project_id=? AND assignment_role='owner'",(pid,)).fetchone()
        history=customer_orders[p['customer_id']]
        output.append({'id':pid,'name':p['name'],'market':market(p),'sales':person(owner[0]) if owner else p['owner'] or '待分配',
            'design_owner':'、'.join(dict.fromkeys(person(d['owner_id']) for d in design)) or '待分配',
            'design_status':'设计中' if active_design else '已确认' if design else '未建任务',
            'engineering_owner':person(engineering[0]['released_by'] or engineering[0]['created_by']) if engineering else '待分配',
            'engineering_status':'已下达' if engineering and engineering[0]['status']=='released' else '草稿' if engineering else '待交接',
            'production':'生产中' if production else '生产完成' if lines and all(i['production_completed'] for i in lines) else '待生产' if lines else '未下采购单',
            'due':due,'shipped':[dict(unit=k,**v) for k,v in shipment.items()],
            'installation':'安装验收中' if installation else '已验收' if installations and all(t['status']=='accepted' for t in installations) else '待安装',
            'installation_owner':'、'.join(dict.fromkeys(person(t['owner_id']) for t in installations)) or '待分配',
            'amounts':totals(signed) if signed else ({quote['final_currency']:round(float(quote['final_amount'])*100)} if quote and quote['final_amount'] is not None else {}),
            'signed':bool(signed),'customer_amounts':totals(history),'customer_count':sum(o['kind']=='original' for o in history),
            'alerts':alerts,'designing':active_design,'quoted':bool(quote and not signed),'producing':production,'installing':installation,
            'future':not signed and any(o['project_id']==pid and o['stage'] not in ('won','lost') for o in db.execute('SELECT * FROM crm_opportunities'))})
    monthly=[o for o in orders if period(o)]
    markets={m:totals([o for o in monthly if market(projects[o['project_id']])==m]) for m in ('domestic','foreign','unknown')}
    summary=[{'label':'本月销售额','kind':'money','total':rmb(totals(monthly)),'markets':markets}]
    for label,key in [('设计中订单','designing'),('已报价订单','quoted'),('生产中订单','producing'),('安装中订单','installing'),('未来成交订单','future')]:
        summary.append({'label':label,'kind':'count','total':sum(p[key] for p in output),'markets':{m:sum(p[key] and p['market']==m for p in output) for m in markets}})
    tagged={}
    for lead in db.execute("SELECT * FROM crm_leads WHERE customer_grade='A'"):
        if user['role'] not in ('admin','ceo') and lead['owner_id']!=user['id']:continue
        if projects and not any(p['customer_id']==lead['customer_id'] for p in projects.values()) and user['role'] not in ('admin','ceo'):continue
        region=str(lead['region'] or '').strip().lower()
        key=lead['customer_id'] or 'lead:'+lead['id']
        tagged[key]='domestic' if region in ('中国','中国大陆','cn','china','内贸','国内') else 'foreign' if region else 'unknown'
    for raw in db.execute('SELECT * FROM connected_sales WHERE active=1'):
        if not access.visible_customer(db,user,raw['customer_id']):continue
        payload=json.loads(raw['payload'])
        if str(payload.get('grade') or '').upper() in ('A','A类','A 类'):
            country=str(payload.get('country') or '').strip().lower()
            tagged[raw['customer_id']]='domestic' if country in ('中国','中国大陆','cn','china') else 'foreign' if country else 'unknown'
    summary.append({'label':'A 类客户','kind':'customers','total':len(tagged),'markets':{m:sum(v==m for v in tagged.values()) for m in markets},'note':'运营标签 · 客户去重'})
    groups=[{'name':n,'received':None,'count':None,'amounts':None} for n in ('澳洲分公司','北美分公司')]
    salespeople=[e for e in employees.values() if e['role']=='sales' and e['status']=='active' and (user['role'] in ('admin','ceo') or e['id']==user['id'])]
    for e in salespeople:
        owned=[o for o in monthly if o['created_by']==e['id']]
        allocated=set()
        for allocation in db.execute('SELECT * FROM marketing_lead_allocations WHERE owner_id=?',(e['id'],)):
            if period(dict(allocation)):allocated.add(allocation['lead_id'])
        groups.append({'name':e['name'],'received':len(allocated),'count':sum(o['kind']=='original' for o in owned),'amounts':totals(owned)})
    if user['role'] in ('admin','ceo'):
        groups += [{'name':'业务员 '+str(i+1),'received':None,'count':None,'amounts':None} for i in range(len(salespeople),7)]
    period_tickets=[t for t in tickets if period(t)]
    stages=[json.loads(t['payload']).get('stage') or '接收反馈' for t in period_tickets]
    after={'total':len(stages),'pending':sum(s=='接收反馈' for s in stages),'closed':sum(s=='关闭与复盘' for s in stages)}
    after['processing']=after['total']-after['pending']-after['closed']
    return {'summary':summary,'projects':output,'groups':groups,'aftersales':after,'rate':6.8,'period':{'from':start,'to':end},
        'notices':['运营分配数量读取分配历史；A 类客户读取运营客户标签及已同步客户标签。旧资料未登记分配日期的，不推算历史月份。','分公司归属待后台接入；员工姓名沿用人员档案。成交业绩暂按正式订单创建人统计。','客户累计成交仅汇总当前账号可见的正式订单，原单计成交次数、增项计金额。','发货数量读取采购供应商发货记录，按单位分别显示；未填写国家的项目单独列为地区待确认。']}
