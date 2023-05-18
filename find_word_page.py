import json, re

def read_json(file:str) -> list:
    with open(file) as f:
        p = json.load(f)
        v = ['']*13759
        for i in range(13759):
            if (128 <= i & i < 256) or (0 <= i & i < 32): # 128 - 255: 'UNICODE' = '     '; 0 - 31: unable to print
                v[i] = '123'
            else:
                v[i] = '\\u' + p['CP950'][i]['UNICODE'][2:6] # ex: 0x1234 --> \\u1234
        return v

def find_page(v:list, code:str) -> int:
    for i, code_text in enumerate(v):
        if code_text == f'\\u{code}':
            return i // 100 + 1
    return 0

if __name__ == '__main__':
    v = read_json('./CP950.json')
    page = 0    # page number
    code = ''   # word unicode
    while True:
        code = input('Input the word unicode(e.g. FE54):')
        code = code.upper()
        if re.match('^[A-F0-9]{4}$', code):
            page = find_page(v, code)
            break
        else:
            print('You input error format.')
    
    if page:
        print(f'Found {code} in page {page}')
    else:
        print(f'Cannot find the {code} on any page! !')