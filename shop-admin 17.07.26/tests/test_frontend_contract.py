from pathlib import Path

def test_frontend_has_no_business_localstorage_and_only_expected_tabs():
    js=Path('app.js').read_text()
    html=Path('index.html').read_text()
    assert 'id="navGroupToggle"' in html and 'aria-controls="sideNav"' in html
    assert 'id="closeSidebar"' in html and "on('closeSidebar','click'" in js
    assert "classList.remove('open')" in js
    assert "classList.toggle('collapsed',expanded)" in js
    assert 'localStorage' not in js
    for view in ('orders','schedule','payroll','debts'):
        assert f'data-view="{view}"' in html
    assert "api('/api/orders')" in js
    assert "api(`/api/advances?" in js
    assert "api(`/api/shifts?" in js
    assert "api(`/api/payroll?" in js
    assert 'Всё равно сохранить' in js
    assert "me.role==='Сотрудник'" in js
