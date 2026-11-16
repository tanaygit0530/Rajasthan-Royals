"""Screenshots of every page at 1440 px and 390 px + password-gate checks. Uses the installed Chrome via Playwright.
Usage: python scripts/screens.py [base_url]   (password read from site/.env.local)"""
import re, sys, os, json
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4173/'
PW = re.search(r'^SITE_PASSWORD=(.*)$', open(os.path.join(os.path.dirname(__file__), '..', '.env.local')).read(), re.M).group(1).strip()
OUT = os.path.join(os.path.dirname(__file__), '..', 'screens'); os.makedirs(OUT, exist_ok=True)
PAGES = [('landing', '#/'), ('rankings', '#/rankings'), ('rankings_bowl_value', '#/rankings?role=bowl&list=value'),
         ('rankings_youth', '#/rankings?role=bat&list=youth'), ('player_bumrah', '#/player/462411b3'),
         ('player_sooryavanshi', '#/player/470f446b'), ('compare', '#/compare'), ('how', '#/how-it-works'),
         ('strategy', '#/strategy'), ('report', '#/report')]
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome', headless=True)
    for w, h, tag in [(1440, 900, 'desktop'), (390, 844, 'mobile')]:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1 if w > 400 else 2)
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(BASE); pg.wait_for_selector('#pw')
        pg.screenshot(path=f'{OUT}/{tag}_00_gate.png')
        pg.fill('#pw', 'wrong-password'); pg.click('button:has-text("Open")'); pg.wait_for_selector('[role=alert]', timeout=20000)
        res[f'{tag}_wrong_password_rejected'] = 'did not work' in pg.inner_text('[role=alert]')
        pg.fill('#pw', PW); pg.click('button:has-text("Open")'); pg.wait_for_selector('main', timeout=30000)
        res[f'{tag}_unlocked'] = True
        for name, route in PAGES:
            pg.goto(BASE + route); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1800)
            pg.screenshot(path=f'{OUT}/{tag}_{name}.png', full_page=True)
        res[f'{tag}_js_errors'] = errs
        ctx.close()
    # dark mode sample
    ctx = b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark'); pg = ctx.new_page()
    pg.goto(BASE); pg.fill('#pw', PW); pg.click('button:has-text("Open")'); pg.wait_for_selector('main')
    for name, route in [('landing', '#/'), ('player_bumrah', '#/player/462411b3'), ('strategy', '#/strategy')]:
        pg.goto(BASE + route); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1500)
        pg.screenshot(path=f'{OUT}/dark_{name}.png', full_page=True)
    b.close()
print(json.dumps(res, indent=1))
