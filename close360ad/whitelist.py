import json
import os


def _path():
    d = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Close360Ad')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'whitelist.json')


def load():
    try:
        with open(_path(), encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'rules': []}


def save(data):
    with open(_path(), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_rule(title, exe_name, class_name):
    data = load()
    rule = {
        'title': title.strip() if title else '',
        'exe': exe_name.strip() if exe_name else '',
        'class': class_name.strip() if class_name else '',
    }
    if not any(rule.get(k) for k in rule):
        return
    if rule not in data['rules']:
        data['rules'].append(rule)
    save(data)


def is_whitelisted(title, exe_name, class_name):
    data = load()
    t = title.lower() if title else ''
    e = exe_name.lower() if exe_name else ''
    c = class_name.lower() if class_name else ''
    for rule in data.get('rules', []):
        rt = rule.get('title', '').lower()
        re = rule.get('exe', '').lower()
        rc = rule.get('class', '').lower()
        if rt and rt not in t:
            continue
        if re and re != e:
            continue
        if rc and rc != c:
            continue
        if rt or re or rc:
            return True
    return False
