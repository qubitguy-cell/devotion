from app import app

c = app.test_client()
r = c.get('/admin/devotionals')
print('GET', r.status_code)
r2 = c.post(
    '/admin/devotionals',
    data={
        'date': '2026-10-07',
        'title': 'Test Title',
        'verse': 'John 1:1',
        'body': 'Test body text',
    },
    follow_redirects=False,
)
print('POST', r2.status_code, r2.location)
print('FLASH', 'Devotional post saved successfully.' in (r2.get_data(as_text=True) or ''))
