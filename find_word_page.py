import json, re

from s2_crop_page import read_json

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