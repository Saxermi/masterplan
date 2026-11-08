"""Read missing weekly slots from the official VVZ HTML (no guessed times)."""
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urlsplit


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ''.join(c if isinstance(c, str) else c.text() for c in self.children).replace('\xa0', ' ').strip()

    def find(self, tag):
        for child in self.children:
            if isinstance(child, Node):
                if child.tag == tag:
                    yield child
                yield from child.find(tag)


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_official_courses(html):
    doc = Document()
    doc.feed(html)
    courses = []
    days = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
    for row in doc.root.find('tr'):
        cells = [c for c in row.children if isinstance(c, Node) and c.tag == 'td']
        if len(cells) < 4 or not re.fullmatch(r'\d{3}-\d{4}-\d{2}\s+[A-Z]+', cells[0].text()):
            continue
        slots = []
        for slot_row in cells[3].find('tr'):
            cols = [c for c in slot_row.children if isinstance(c, Node) and c.tag == 'td']
            if len(cols) != 3 or cols[0].text() not in days:
                continue
            times = re.fullmatch(r'(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})', cols[1].text())
            if not times:
                continue  # date-specific / irregular slots require manual review
            room = {}
            for a in cols[2].find('a'):
                url = urlsplit(a.attrs.get('href', ''))
                params = parse_qs(url.query)
                if a.attrs.get('rel') == 'geb':
                    room = {k: params.get(v, [''])[0] for k, v in
                            [('building', 'gebaeude'), ('floor', 'geschoss'), ('room', 'raumNr')]}
                    break
            slots.append({'weekday': days[cols[0].text()], 'start_time': times[1], 'end_time': times[2], **room})
        comments = [c for c in cells[1].children if isinstance(c, Node) and
                    'kommentar-lv' in c.attrs.get('class', '').split()]
        title = ' '.join(c.strip() if isinstance(c, str) else c.text()
                         for c in cells[1].children if c not in comments).strip()
        courses.append({'number': cells[0].text(), 'title': title, 'timeslots': slots,
                        'comment': ' '.join(c.text() for c in comments)})
    if not courses:
        raise ValueError('Official VVZ returned no recognizable courses')
    return courses
