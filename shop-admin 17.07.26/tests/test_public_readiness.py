def test_public_legal_pages_are_available_and_not_indexed(client):
    for path in ('/privacy','/terms','/robots.txt'):
        response=client.get(path)
        assert response.status_code==200
        assert response.headers.get('x-robots-tag','').startswith('noindex')
    assert 'Disallow: /' in client.get('/robots.txt').text
    assert 'Политика обработки персональных данных' in client.get('/privacy').text

def test_api_responses_are_not_cached(client):
    response=client.get('/api/auth/setup-required')
    assert response.status_code==200
    assert 'no-store' in response.headers.get('cache-control','')
