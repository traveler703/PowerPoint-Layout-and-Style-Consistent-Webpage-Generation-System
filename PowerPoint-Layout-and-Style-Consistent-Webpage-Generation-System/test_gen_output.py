import asyncio, sys, json, os
sys.path.insert(0, '.')
from scripts.template_generator import TemplateGenerator

async def test():
    gen = TemplateGenerator()
    result = await gen.generate('古风水墨画PPT模板')
    tpl = result['parsed']
    print('success:', result['success'])
    print('validation:', result['validation'])
    print()
    for ptype, cfg in tpl.get('page_types', {}).items():
        sk = cfg.get('skeleton', '')
        pls = cfg.get('placeholders', [])
        ends_ok = sk.strip().endswith('</div>')
        pn_ok = '{{page_number}}' in sk
        print(f'--- {ptype} ---')
        print(f'  placeholders: {pls}')
        print(f'  ends with </div>: {ends_ok}')
        print(f'  has page_number placeholder: {pn_ok}')
        print(f'  skeleton len: {len(sk)}')
        print(f'  skeleton: {sk[:300]}...' if len(sk) > 300 else f'  skeleton: {sk}')
        print()

    # 保存
    out_dir = os.path.join('templates', 'data', 'user_generated')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'test_gufeng.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(tpl, f, ensure_ascii=False, indent=2)
    print(f'saved to {out_path}')

    # 关键检查
    print()
    print('=== 格式一致性检查 ===')
    raw = tpl.get('raw_html', '')
    checks = {
        'has {{SLIDES_CONTENT}}': '{{SLIDES_CONTENT}}' in raw,
        'has <html': '<html' in raw,
        'has </html>': '</html>' in raw,
        'has {{TOTAL_PAGES}}': '{{TOTAL_PAGES}}' in raw,
        'has :root': ':root' in raw,
        'all skeletons end properly': all(
            cfg.get('skeleton', '').strip().endswith('</div>')
            for cfg in tpl.get('page_types', {}).values()
        ),
        'all skeletons have page_number': all(
            '{{page_number}}' in cfg.get('skeleton', '')
            for cfg in tpl.get('page_types', {}).values()
        ),
        'has css_variables': len(tpl.get('css_variables', {})) > 0,
        'has viewport': tpl.get('viewport', {}) != {},
        'has tags': len(tpl.get('tags', [])) > 0,
    }
    for k, v in checks.items():
        status = 'PASS' if v else 'FAIL'
        print(f'  [{status}] {k}')

asyncio.run(test())
