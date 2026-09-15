"""Small offline regression for rendering real downloaded Huawei CHM-style HTML."""
import importlib.util
from pathlib import Path
import json

import pytest
pytest.importorskip('bs4')

from cli_reference_corpus.vendors.huawei import NE40ERenderedParser

SCRIPTS = Path(__file__).parents[1] / 'scripts'
spec = importlib.util.spec_from_file_location('chm_to_pdf', SCRIPTS / 'chm_to_pdf.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def test_html_render_pdf_parse_preserves_fields(tmp_path):
    root=tmp_path/'html';root.mkdir()
    (root/'contents.hhc').write_text('<ul><li><object type="text/sitemap"><param name="Name" value="sample"><param name="Local" value="sample.html"></object></li></ul>')
    (root/'sample.html').write_text('''<html><body><div class="articleBoxWithoutHead">
    <h1>sample</h1>
    <div class="clifunc"><h2>Function</h2><p>Sets a sample value.</p></div>
    <div class="cliformat"><h2>Format</h2><p><b>sample</b> <i>value</i></p><p><b>undo sample</b></p></div>
    <div class="cliparam"><h2>Parameters</h2><table><tr><th>Parameter</th><th>Description</th><th>Value</th></tr><tr><td>value</td><td>A number.</td><td>1 to 10</td></tr></table></div>
    <div><h2>Views</h2><p>System view</p></div>
    <div><h2>Usage Guidelines</h2><p>Configure before enabling.</p></div>
    <div class="cliexample"><h2>Example</h2><pre>&lt;HUAWEI&gt; system-view</pre><pre>[~HUAWEI] sample 3</pre></div>
    </div><div class="footerNavBar">Navigation must not leak.</div></body></html>''')
    html=(root/'sample.html').read_text()
    # A long CLI-output block must paginate instead of generating empty pages forever.
    html=html.replace('<pre>[~HUAWEI] sample 3</pre>', '<pre>[~HUAWEI] sample 3\n' + '\n'.join(f'output row {i}' for i in range(150)) + '\n[~HUAWEI] sample 4</pre>')
    (root/'sample.html').write_text(html)
    output=tmp_path/'rendered.pdf'
    mapping=renderer.render_topics(root,output,title='Test')
    result=NE40ERenderedParser().parse(output)
    assert len(result.commands)==1
    c=result.commands[0]
    assert c.clis==['sample <value>', 'undo sample']
    assert c.parameters[0].name=='value'
    assert c.parameters[0].info=='A number.\n1 to 10'
    assert c.usage_guidelines=='Configure before enabling.'
    assert c.examples==[['<HUAWEI> system-view','[~HUAWEI] sample 3','[~HUAWEI] sample 4']]
    assert result.page_count > 1
    assert 'Navigation' not in json.dumps(c.to_dict())
    assert mapping[0]['html_file']=='sample.html'
    assert len(mapping[0]['html_sha256'])==64
    assert result.report()['issues']==[]


def test_real_ne40e_captioned_output_table_and_superscript(tmp_path):
    import shutil
    root=tmp_path/'html';root.mkdir()
    shutil.copyfile(Path(__file__).parent/'fixtures/ne40e-ospfv3.html',root/'topic.html')
    (root/'contents.hhc').write_text('<object type="text/sitemap"><param name="Name" value="display ospfv3 routing"><param name="Local" value="topic.html"></object>')
    pdf=tmp_path/'ospfv3.pdf'
    renderer.render_topics(root,pdf,title='NE40E OSPFv3')
    result=NE40ERenderedParser().parse(pdf)
    c=result.commands[0]
    assert len(c.parameters)==12
    assert c.views==['Diagnostic view']
    assert len(c.examples)==2
    assert c.clis[0].endswith('[ age { min-value <min-age-value> | max-value <max-age-value> } * ]')
    assert c.clis[1]=='display ospfv3 [ <process-id> ] routing statistics'
    assert 'troubleshoot OSPFv3 faults' in c.usage_guidelines
    assert result.report()['issues']==[]
    assert result.page_count==3


def test_real_ne40e_long_parameter_row_preserves_following_sections(tmp_path):
    import shutil
    root=tmp_path/'html';root.mkdir()
    shutil.copyfile(Path(__file__).parent/'fixtures/ne40e-mpls.html',root/'topic.html')
    (root/'contents.hhc').write_text('<object type="text/sitemap"><param name="Name" value="mpls switch-l2vc"><param name="Local" value="topic.html"></object>')
    pdf=tmp_path/'mpls.pdf'
    mapping=renderer.render_topics(root,pdf,title='NE40E MPLS')
    result=NE40ERenderedParser().parse(pdf)
    assert mapping[0]['page_height']==1684
    assert result.commands[0].views==['System view']
    assert len(result.commands[0].usage_guidelines)>2000
    assert len(result.commands[0].parameters)==18
    assert not any(w in {'missing_views','missing_function','missing_format'} for w in result.report()['issues'][0]['warnings'])


def test_reference_book_keeps_introduction_and_excludes_other_books(tmp_path):
    from cli_reference_corpus.preparation.reference import ReferenceContents
    import pymupdf

    icon = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2))
    icon.clear_with(128)
    icon.save(tmp_path / "icon.png")

    (tmp_path / "reference.html").write_text('''<html><body><h1>Command Reference</h1>
    <p>Complete reference introduction.</p>
    <table><tr><td><img src="icon.png"></td><td>Important note.</td></tr></table>
    <ul class="ullinks">
    <dl><dt><a href="command.html">sample</a></dt></dl></ul>
    <p>Related command: <a href="debugging.html">debugging sample</a></p>
    </body></html>''')
    command = '''<html><body><h1>sample</h1>
    <div class="clifunc"><h2>Function</h2><p>Sets a sample value.</p></div>
    <div class="cliformat"><h2>Format</h2><p><b>sample</b></p></div>
    <div><h2>Views</h2><p>System view</p></div></body></html>'''
    (tmp_path / "command.html").write_text(command)
    (tmp_path / "debugging.html").write_text(command.replace("sample", "debugging sample"))
    topics = ReferenceContents(tmp_path, "reference.html").topics()
    assert [(topic.title, topic.is_command) for topic in topics] == [
        ("Command Reference", False), ("sample", True),
    ]
    pdf = tmp_path / "reference.pdf"
    mapping = renderer.render_topics(tmp_path, pdf, title="Test", entry_point="reference.html")
    with pymupdf.open(pdf) as document:
        assert "Complete reference introduction." in document[0].get_text()
        assert len(document[0].get_images()) == 1
    result = NE40ERenderedParser().parse(pdf)
    assert [command.title for command in result.commands] == ["sample"]
    assert result.report()["missing_outline_sections"] == []
    assert len(mapping) == 2


def test_reference_book_rejects_missing_child(tmp_path):
    from cli_reference_corpus.preparation.reference import ReferenceContents

    (tmp_path / "reference.html").write_text('''<html><body><h1>Command Reference</h1>
    <ul class="ullinks"><dl><dt><a href="missing.html">missing</a></dt></dl></ul>
    </body></html>''')
    with pytest.raises(ValueError, match="Missing reference topic"):
        ReferenceContents(tmp_path, "reference.html").topics()


def test_conversion_census_detects_missing_body_text():
    import pymupdf
    from cli_reference_corpus.preparation.text_coverage import text_coverage

    with pymupdf.open() as document:
        document.new_page().insert_text((40, 40), "Function Configure routing.")
        coverage = text_coverage("Function Configure routing. Required prerequisite.", document.tobytes())
    assert coverage["missing_words"] == {"Required": 1, "prerequisite": 1}


def test_reference_outline_stops_before_debugging_and_detects_omission(tmp_path):
    from cli_reference_corpus.preparation.contents import BookOutline
    from cli_reference_corpus.preparation.topics import HTMLTopic

    def entry(title, path):
        return f'<li><object type="text/sitemap"><param name="Name" value="{title}"><param name="Local" value="{path}"></object>'

    # HHC files commonly omit </li>; use explicit <ul> nesting for depth.
    (tmp_path / "contents.hhc").write_text(
        '<ul>' + entry('Command Reference', 'reference.html') + '<ul>'
        + entry('sample', 'command.html') + '</ul>'
        + entry('Debugging Command Reference', 'debugging.html') + '</ul>'
    )
    outline = BookOutline(tmp_path, 'reference.html')
    assert [entry.local for entry in outline.entries()] == ['reference.html', 'command.html']
    topics = [HTMLTopic(tmp_path / 'reference.html', 'Command Reference', False)]
    with pytest.raises(ValueError, match="missing=.*command.html"):
        outline.verify(topics)
    topics.append(HTMLTopic(tmp_path / 'command.html', 'sample'))
    assert outline.verify(topics)['unique_html_topics'] == 2


def test_inline_text_census_does_not_split_words_at_formatting_tags():
    from bs4 import BeautifulSoup
    from cli_reference_corpus.preparation.text_coverage import source_text, compare_text

    source = BeautifulSoup('<div><p><b>IPv</b>6</p><p>a<span>pply</span></p></div>', 'html.parser')
    assert compare_text(source_text(source), 'IPv6 apply')['missing_word_count'] == 0


def test_browser_page_check_rejects_missing_body_text(tmp_path):
    import pymupdf
    from cli_reference_corpus.preparation.browser_pages import BrowserPages, BrowserTopic
    from cli_reference_corpus.preparation.topics import HTMLTopic

    source = tmp_path / 'sample.html'
    source.write_text('''<html><body><h1>sample</h1>
    <div class="clifunc"><h2>Function</h2><p>Sets a value. Required prerequisite.</p></div>
    <div class="cliformat"><h2>Format</h2><p>sample</p></div></body></html>''')
    topic = BrowserTopic.prepare(HTMLTopic(source, 'sample'), 1, tmp_path)
    for body, complete in [('Sets a value. Required prerequisite.', True), ('Sets a value.', False)]:
        with pymupdf.open() as document:
            page = document.new_page()
            for y, text, size, font in [(55, '1.1 sample', 16, 'hebo'), (90, 'Function', 13, 'hebo'),
                                         (120, body, 10, 'helv'), (150, 'Format', 13, 'hebo'),
                                         (180, 'sample', 10, 'hebo')]:
                page.insert_text((45, y), text, fontsize=size, fontname=font)
            pages = BrowserPages(document, [topic], tmp_path)
            if complete:
                assert pages.mapping()[0]['text_coverage']['missing_character_count'] == 0
            else:
                with pytest.raises(ValueError, match='Printed text loss'):
                    pages.mapping()


def test_prepared_pdf_uses_complete_bookmark_title_for_wrapped_heading(tmp_path):
    import pymupdf

    title = 'peer graceful-restart (BGP multi-instance view)(group)'
    pdf = tmp_path / 'wrapped.pdf'
    with pymupdf.open() as document:
        page = document.new_page()
        for y, text, size in [(55, '1.1 peer graceful-restart (BGP multi-', 16),
                              (75, 'instance view)(group)', 16),
                              (110, 'Function', 13), (160, 'Format', 13),
                              (185, 'peer graceful-restart', 10)]:
            page.insert_text((45, y), text, fontsize=size, fontname='hebo')
        page.insert_text((45, 135), 'Enables graceful restart.', fontsize=10)
        document.set_toc([[1, '1.1 ' + title, 1]])
        document.save(pdf)
    command = NE40ERenderedParser().parse(pdf).commands[0]
    assert command.title == title
    assert command.function == 'Enables graceful restart.'
    assert command.clis == ['peer graceful-restart']
