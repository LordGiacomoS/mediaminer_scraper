import requests
import re
import ebooklib
import datetime

from bs4 import BeautifulSoup as BS
from ebooklib import epub
from ebooklib.utils import create_pagebreak

"""REQUEST HANDLER & SOUP MAKER"""
def get_page(url):
    req = requests.get(url)
    soup = BS(req.content, 'lxml')
    return soup

"""SCRAPING UTILITIES"""
def get_summary(metadata_tag):
    total_brs = len(metadata_tag.find_all('br'))
    
    br_count = 1
    curr_tag = metadata_tag.find('br')
    summary_tags = []
    while br_count <= total_brs:
        if type(curr_tag) == None:
            break
        elif curr_tag.name == 'br':
            br_count += 1
        else:
            if curr_tag == '\n':
                summary_tags.append('<br/>')
            else:
                summary_tags.append(curr_tag.strip('\n\t '))
        curr_tag = curr_tag.next_sibling    
    return ''.join(summary_tags)

"""BS4 SCRAPING FUNCTIONS"""
def looks_like_author_tag(tag):
    if tag.name == 'a' and tag.has_attr('href'):
        if re.match('/user_info\.php/\d+', tag['href']):
            return tag
        
def looks_like_fandom_tag(tag):
    if tag.name == 'a' and tag.has_attr('href'):
        if re.match('/fanfic/a/[a-z\-]+/\d+', tag['href']):
            return tag

def looks_like_fandom_section(tag):
    if tag.name == 'b' and tag.string.strip('\n\t ') in ['Non Anime:', 'Anime/Manga:']:
        return tag

def looks_like_chapters_div(tag):
    if tag.name == 'div' and tag.has_attr('id') == False and tag.has_attr('class') == False:
        return tag

"""MAJOR SCRAPING FUNCTIONS"""
def get_metadata(soup):
    title_tag = soup.body.find('h1', attrs={'id': 'post-title'})
    fandom_ignored, title = title_tag.string.split(' ❯ ', maxsplit=1)
    # technically if someone included the arrow in the fandom name (not fic title), it could throw stuff off but that is unlikely and I am lazy
    
    rating = title_tag.parent.find('div', attrs={'id': 'post-rating'}).string.strip('\n\t ')

    metadata_tag = title_tag.parent.find('div', attrs={'class': 'post-meta'})
    
    author_tags = metadata_tag.find_all(looks_like_author_tag)
    summary = get_summary(metadata_tag)
    fandom_tag = metadata_tag.find(looks_like_fandom_tag)
    
    #more metadata tba in future
    authors = []
    for author_tag in author_tags:
        author_dct = {
            'name': author_tag.string.strip('\n\t '),
            'url': 'https://mediaminer.org' + author_tag['href']
        }
        authors.append(author_dct)

    metadata = {
        'title': title,
        'rating': rating,
        'authors': authors, 
        'summary': summary,
        'fandom': {
            'section': metadata_tag.find(looks_like_fandom_section).string.strip('\n\t: '),
            'source': {
                'name': fandom_tag.string.strip('\n\t '),
                'link': 'https://mediaminer.org' + fandom_tag['href']
            }
        }
    }
    return metadata, title_tag 

def find_chapters(soup, title_tag):
    chapters_div = title_tag.parent.find(looks_like_chapters_div)
    chapters_paragraph = chapters_div.find('p', attrs={'style': 'margin-left:10px;'})
    
    chapters = []
    for a_tag in chapters_paragraph.find_all('a'):
        chap_dct = {
            'title': a_tag.string.strip('\n\t '),
            'link': 'https://mediaminer.org' + a_tag['href']
        }
        
        chapters.append(chap_dct)
    return chapters

def parse_chapter(chap_link_dct):
    url = chap_link_dct['link']
    soup = get_page(url)
    
    title_tag = soup.body.find('h1', attrs={'id': 'post-title'})
    metadata_tag = title_tag.parent.find('div', attrs={'class': 'post-meta'})

    chap_html_list = title_tag.parent.find('div', attrs={'id': 'fanfic-text'}).contents
    chap_html = ''.join([str(item) for item in chap_html_list])
    
    chapter_dct = {
        'title': chap_link_dct['title'],
        'chap_summary': get_summary(metadata_tag),
        'chap_contents': chap_html
    }
    return chapter_dct

def build_chap(chap_dct, count):
    chap_html = f"""<html>
        <head>
            <center><h2>""" + chap_dct['title'] + """</h2></center>
            <br/>
            <p>""" + chap_dct['chap_summary'] + """</p>
        </head>
        <hr>
        <body>
            """ + chap_dct['chap_contents'] + """
        </body>
    <html>"""
    chap_obj = epub.EpubHtml(title=chap_dct['title'], file_name=f'ch{count}.xhtml')
    chap_obj.set_content(chap_html)
    return chap_obj
    
def load_chapters(chapter_lst):
    chap_objs = []
    count = 1
    for dct in chapter_lst:
        parsed = parse_chapter(dct)
        chap_obj = build_chap(parsed, count)
        
        chap_objs.append(chap_obj)
        count += 1
    
    return chap_objs
    
def parse_story_link(url):
    soup = get_page(url)
    
    metadata, title_tag = get_metadata(soup)
    chapters = find_chapters(soup, title_tag)
    
    book_dct = {
        'origin_url': url,
        'metadata': metadata,
        'chapters': load_chapters(chapters)
    }
    return book_dct


"""BOOK BINDING FUNCTIONS"""
def cover_chap(metadata):
    author_lines = [f'<h4><a href="' + author['url'] + '">' + author['name'] + "</a></h4>" for author in metadata['authors']]
    
    intro_txt = '<html><head><center><b><h1>' + metadata['title'] + '</h1></b><hr><p><i>' + '\n'.join(author_lines) + '</i></p></head><body><hr></center><p>' + metadata['summary'] + '</p></body></html>'
    
    chap_0 = epub.EpubHtml(title='Story Info', file_name='ch0.xhtml')
    chap_0.content = intro_txt
    return chap_0
        
def set_metadata(book_dct, book_obj):
    metadata = book_dct['metadata']
    book_obj.set_title(metadata['title'])
    
    #NOTE: SHOULD PROBABLY ADD LANGUAGE TAG `book_obj.set_language([use lang code from RFC 4646])`
    
    for author in metadata['authors']:
        book_obj.add_author(author['name'])
    
    chap_0 = cover_chap(metadata)
    
    return chap_0
    
def create_chapters(chaps_lst, book_obj):
    chapters = []
    count = 1
    for chap_dct in chaps_lst:
        chap_html = f"""<html>
            <head>
                <center><h2>""" + chap_dct['title'] + """</h2></center>
                <br/>
                <p>""" + chap_dct['chap_summary'] + """</p>
            </head>
            <hr>
            <body>
                """ + ''.join(chap_dct['chap_contents']) + """
            </body>
        <html>"""
        chap_obj = epub.EpubHtml(title=chaps_dct['title'], file_name=f'ch{count}.xhtml')
        chap_obj.set_content(chap_html)
        
        chapters.append(chap_obj)
        count += 1
    return chapters

def bind_from_dct(book_dct):
    book_obj = epub.EpubBook()
    
    c0 = set_metadata(book_dct, book_obj)
    chaps = book_dct['chapters']
    
    for chapter in [c0] + chaps:
        book_obj.add_item(chapter)
    
    book_obj.toc = (
        epub.Link('ch0.xhtml', 'Story Info', 'cover'),
        (
            epub.Section('Contents'),
            tuple(chaps)
        )
    )
    
    book_obj.spine = [c0] + chaps
    
    book_obj.add_item(epub.EpubNcx())
    book_obj.add_item(epub.EpubNav())
    
    return book_obj

def download_story(url, save_to=None):
    book_dct = parse_story_link(url)
    book_obj = bind_from_dct(book_dct)
    
    if save_to == None:
        save_to = book_dct['title'].lowercase() + '_' + datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + '.epub
    
    epub.write_epub(save_to, book_obj)
