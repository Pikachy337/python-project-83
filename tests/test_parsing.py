from page_analyzer.app import parse_seo_data


def test_parse_seo_data():
    html = """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
        </head>
        <body>
            <h1>Main Header</h1>
        </body>
    </html>
    """

    result = parse_seo_data(html)
    assert result == {
        'h1': 'Main Header',
        'title': 'Test Page',
        'description': 'Test description'
    }


def test_parse_empty_seo_data():
    result = parse_seo_data("<html></html>")
    assert result == {
        'h1': '',
        'title': '',
        'description': ''
    }
