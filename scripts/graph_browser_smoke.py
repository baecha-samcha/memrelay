"""Exercise the real graph API/Cytoscape on a dedicated mock review server.

LLM_MODE=mock GRAPH_PREFIX=memrelay_graph_review python -m uvicorn app.main:app --port 8002
python scripts/graph_browser_smoke.py
No provider calls; synthetic writes use the dedicated app prefix.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url = os.getenv('MEMRELAY_GRAPH_TEST_URL', 'http://127.0.0.1:8002')
artifacts = Path('artifacts')
artifacts.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--disable-dev-shm-usage'])
    try:
        page = browser.new_page(viewport={'width':1440,'height':1080}, device_scale_factor=1)
        page.set_default_timeout(30000)
        expect.set_options(timeout=30000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        expect(page.locator('#knowledge-panel')).to_have_attribute('data-state','ready')
        expect(page.locator('#user')).to_be_enabled()
        # The dedicated normal graph must be different from the isolated demo.
        response = page.request.post(url+'/api/chat', data={'user':'alice','text':'We switched Project Atlas to Java'})
        assert response.status == 200
        page.click('#refresh')
        expect(page.locator('#user')).to_be_enabled()
        page.wait_for_function("MemoryGraph.cy.nodes().some(n=>n.data('properties').object==='Java')")
        print('PASS: real current Alice graph is rendered.', flush=True)
        page.click('#demo')
        expect(page.locator('#demo-panel')).to_be_visible(timeout=90000)
        expect(page.locator('#knowledge-panel')).to_have_attribute('data-state','ready',timeout=90000)
        expect(page.locator('#graph-scope')).to_have_text('DEMO · ALICE')
        expect(page.locator('#user')).to_be_enabled()
        assert page.locator('#demo-scenes .scene').count() == 8
        counts = page.evaluate("({nodes:MemoryGraph.cy.nodes().length,edges:MemoryGraph.cy.edges().length})")
        assert counts['nodes'] > 0 and counts['edges'] > 0
        revision = page.evaluate("""() => {const e=MemoryGraph.cy.edges('[type="SUPERSEDES"]').first();return {
            from:e.source().data('properties').object,to:e.target().data('properties').object};}""")
        assert revision == {'from':'Rust','to':'Python'}
        assert not page.evaluate("MemoryGraph.cy.nodes().some(n=>n.data('properties').object==='Java')")
        print(json.dumps({'check':'real_demo_projection','status':'PASS',**counts,'supersedes':revision}), flush=True)
        page.locator('#knowledge-panel').scroll_into_view_if_needed()
        page.click('#graph-revisions')
        expect(page.locator('#graph-count')).to_have_text('4/42 nodes · 3/65 edges')
        assert page.evaluate('MemoryGraph.cy.zoom()') >= .9
        print('PASS: revision focus rendered at readable zoom with exact visible counts.',flush=True)
        assert page.evaluate("MemoryGraph.cy.edges(':visible').some(e=>e.data('type')==='SUPERSEDES')")
        expect(page.locator('#graph-revision-note')).to_contain_text('Python → Rust')
        page.evaluate("() => { MemoryGraph.cy.nodes().filter(n=>n.data('properties').object==='Rust').first().emit('tap'); }")
        expect(page.locator('#graph-details')).to_contain_text('We switched Project Atlas to Rust')
        expect(page.locator('#graph-details')).to_contain_text('Source messages')
        print('PASS: Rust details and original source displayed.',flush=True)
        page.screenshot(path=str(artifacts/'knowledge-graph-revisions.png'))
        # Test canvas dragging through actual mouse events, not a position setter.
        node = page.evaluate("""() => {const n=MemoryGraph.cy.nodes().filter(n=>n.data('properties').object==='Rust').first();return {id:n.id(),x:n.renderedPosition('x'),y:n.renderedPosition('y'),px:n.position('x')};}""")
        box = page.locator('#knowledge-graph').bounding_box()
        page.mouse.move(box['x']+node['x'],box['y']+node['y'])
        page.mouse.down()
        page.mouse.move(box['x']+node['x']+50,box['y']+node['y']+25,steps=8)
        page.mouse.up()
        assert page.evaluate('(id)=>MemoryGraph.cy.getElementById(id).position("x")',node['id']) != node['px']
        old_zoom = page.evaluate('MemoryGraph.cy.zoom()')
        page.click('#graph-zoom-in')
        assert page.evaluate('MemoryGraph.cy.zoom()') > old_zoom
        page.click('#graph-fit')
        page.click('#graph-handoff')
        assert page.evaluate("MemoryGraph.cy.edges(':visible').some(e=>e.data('type')==='HANDED_OFF_TO')")
        page.evaluate("() => { MemoryGraph.cy.nodes('[type=\"Task\"]').first().emit('tap'); }")
        expect(page.locator('#graph-details')).to_contain_text('Create a project summary')
        expect(page.locator('#graph-details .graph-source').filter(has_text='Create a project summary')).to_have_count(1)
        page.evaluate("() => { MemoryGraph.cy.edges('[type=\"HANDED_OFF_TO\"]').first().emit('tap'); }")
        expect(page.locator('#graph-details')).to_contain_text('completed')
        page.click('#graph-arrange')
        page.screenshot(path=str(artifacts/'knowledge-graph-handoff.png'))
        print('PASS: actual canvas drag, zoom, fit, arrange, revisions, handoff and details.',flush=True)
        page.select_option('#graph-context','demo:bob')
        expect(page.locator('#graph-scope')).to_have_text('DEMO · BOB')
        expect(page.locator('#knowledge-panel')).to_have_attribute('data-state','ready')
        assert page.evaluate("MemoryGraph.cy.nodes().some(n=>n.data('properties').object==='Go')")
        assert not page.evaluate("MemoryGraph.cy.nodes().some(n=>n.data('properties').object==='Rust')")
        # Top user selector follows original behavior: return to current user graphs.
        page.select_option('#user','bob')
        expect(page.locator('#user')).to_be_enabled()
        expect(page.locator('#graph-scope')).to_have_text('CURRENT · BOB')
        page.select_option('#user','alice')
        expect(page.locator('#user')).to_be_enabled()
        expect(page.locator('#graph-scope')).to_have_text('CURRENT · ALICE')
        assert page.evaluate("MemoryGraph.cy.nodes().some(n=>n.data('properties').object==='Java')")
        print('PASS: demo Bob and normal Alice/Bob scope isolation.',flush=True)
        # Real network-backed data above; injected HTTP failures below test UI state.
        page.route('**/api/*/graph*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"database":"disconnected","detail":"FalkorDB unavailable"}'))
        page.click('#graph-reload')
        expect(page.locator('#knowledge-panel')).to_have_attribute('data-state','stale')
        expect(page.locator('#graph-message')).to_be_visible()
        assert page.evaluate('MemoryGraph.cy.elements().length') == 0
        expect(page.locator('#graph-details')).not_to_contain_text('We switched')
        page.unroute('**/api/*/graph*')
        page.click('#graph-reload')
        expect(page.locator('#knowledge-panel')).to_have_attribute('data-state','ready')
        assert page.evaluate('MemoryGraph.cy.nodes().length') > 0
        print('PASS: failed graph request clears nodes/details and reload restores them.',flush=True)
        # A successful health poll alone must not resurrect a stale diagram.
        page.evaluate("connection(false); connection(true)")
        assert page.evaluate('MemoryGraph.cy.elements().length') == 0
        expect(page.locator('#knowledge-panel')).to_have_attribute('data-state','stale')
        page.click('#graph-reload')
        expect(page.locator('#knowledge-panel')).to_have_attribute('data-state','ready')
        page.set_viewport_size({'width':390,'height':844})
        page.click('#graph-revisions')
        page.screenshot(path=str(artifacts/'knowledge-graph-mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert not errors, errors
        print('PASS: stale-state protection and mobile width; no browser errors.',flush=True)
    finally:
        browser.close()
