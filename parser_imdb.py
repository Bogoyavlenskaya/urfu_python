import requests
import logging
import re
import pandas as pd
from bs4 import BeautifulSoup
import argparse

def collect_args():
    logging.info('Collect args')
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--title_type",
        type=str,
        default='',
        choices=['feature','tv_movie','tv_series','tv_episode','tv_special','tv_miniseries','documentary','video_game','short','video','tv_short'],
        help="Title Type of film.",
    )
    parser.add_argument(
        "--release_date_before",
        type=str,
        default='0000-00-00',
        help="If you would like to search for titles released before certain dates(e.g. 1987-03-13,1988-03-13)."
    )
    parser.add_argument(
        "--release_date_after",
        type=str,
        default='3000-00-00',
        help="If you would like to search for titles released after certain dates(e.g. 1987-03-13,1988-03-13)."
    )
    parser.add_argument(
        "--genres",
        type=str,
        default='',
        choices=['Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime',
         'Documentary', 'Drama', 'Family', 'Fantasy', 'Film-Noir', 'Game-Show',
         'History', 'Horror', 'Music', 'Musical', 'Mystery', 'News', 'Reality-TV',
         'Romance', 'Sci-Fi', 'Sport', 'Talk-Show', 'Thriller', 'War', 'Western'],
        help="Movie genres."
    )
    parser.add_argument(
        "--user_raiting_begin",
        type=float,
        default=1.0,
        choices=[j+(i/10) for j in range(1, 10) for i in range(11)],
        help="User Rating."
    )
    parser.add_argument(
        "--user_raiting_end",
        type=float,
        default=10.0,
        choices=[j + (i / 10) for j in range(1, 10) for i in range(11)],
        help="User Rating."
    )
    parser.add_argument(
        "--countries",
        type=str,
        default='',
        choices=get_counties(),
        help="Countries."
    )
    args = parser.parse_args()
    return args

def get_counties():
    url = 'https://www.imdb.com/search/title/'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')
    quotes = [tag['value'] for tag in soup.find('select', class_='countries').children if tag != '\n']
    return quotes

def get_html(args):
    if args.release_date_before != '0000-00-00':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.release_date_before):
            args.release_date_before = '0000-00-00'
    if args.release_date_before != '3000-00-00':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.release_date_after):
            args.release_date_after = '3000-00-00'
    url = 'https://www.imdb.com/search/title/?user_rating=%(user_raiting_begin)s,%(user_raiting_end)s&title_type=%(title_type)s&genres=%(genres)s&countries=%(countries)s&release_date=%(release_date_before)s,%(release_date_after)s' \
          % {
              'user_raiting_begin': args.user_raiting_begin,
              'user_raiting_end': args.user_raiting_end,
              'title_type': args.title_type,
              'release_date_before': args.release_date_before,
              'release_date_after': args.release_date_after,
              'genres': args.genres,
              'countries': args.countries
          }
    logging.info('Get html')
    return url

def get_num_pages(start_url):
    r = requests.get(start_url)
    soup = BeautifulSoup(r.text, 'lxml')
    quotes = [tag.text for tag in
              soup.find('div', class_='article').find('div', class_='nav').find('div', class_='desc').find_all('span')]
    for quot in quotes:
        if re.search(r'titles', quot):
            num_pages = quot.split(' ')[2].replace(',','')
    logging.info('Get num pages')
    return num_pages

def parse_pages(start_url, num_pages):
    num_pages = int(num_pages)
    if num_pages > 1000:
        num_pages = 1000
    name = []
    genres = []
    stars = []
    types = []
    other_info = []
    for i in range(1, num_pages+50, 50):
        logging.info('Parse page '+str(i))
        print(str(i)+' of '+str(num_pages+50))
        url = start_url+'&start='+str(i)
        name_, genres_, stars_, types_, other_info_ = parse_url(url)
        name += name_
        genres += genres_
        stars += stars_
        types += types_
        other_info += other_info_
    name_file = write_doc(name, genres, stars, types, other_info)
    logging.info('Parse pages')
    return name_file

def parse_url(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')
    name = []
    genres = []
    stars = []
    types = []
    other_info = []
    links = []
    quotes = soup.find('div', class_='lister-list')
    names = quotes.find_all_next('h3', class_='lister-item-header')
    slots = quotes.find_all_next('div', class_='lister-item-content')
    for name_slot in names:
        name.append(name_slot.find('a').text)
    for genres_slot in slots:
        try:
            genre = genres_slot.find('p', class_='text-muted').find('span', class_='genre').text
        except AttributeError:
            genre = ''
        genres.append(genre)
    for slot in slots:
        try:
            star = slot.find('div', class_='ratings-bar').find('div', class_='inline-block ratings-imdb-rating').text
            stars.append(star.replace('\n',''))
        except AttributeError:
            stars.append('')
    for slot in slots:
        link = slot.find('h3', class_='lister-item-header').find('a', href=True)['href']
        links.append(link)

    for link in links:
        type_, other_info_ = parse_film_link(link)
        types.append(type_)
        other_info.append(other_info_)
    logging.info('Parse page of 50 films')
    return name, genres, stars, types, other_info

def parse_film_link(link):
    url = 'https://www.imdb.com'+link
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')
    quotes = soup.find('div', attrs={'class':'flatland', 'id':'content-2-wide'}).find('div', attrs={'class':'article', 'id':'titleDetails'})
    if quotes.find('h3', class_='subheading'):
        type_ = 'movie'
    else:
        type_ = 'serial'
    other_info_ = ''
    other_slots = quotes.find_all_next('div', class_='txt-block')
    for other_slot in other_slots:
        other_info_ += other_slot.text
    logging.info('Parse page of film')
    return type_, other_info_.replace('See more »','').replace('\n',' ').replace('  ',' ').replace('Show more on IMDbPro »','')

def write_doc(name, genres, stars, types, other_info):
    df = pd.DataFrame({'name':name,'genres':genres, 'stars':stars, 'types':types, 'details, box office, technical specs':other_info})
    name_file = 'Parse_imdb.csv'
    df.to_csv(name_file, index=False)
    logging.info('Parse_info writen on doc.')
    return name_file

if __name__ == "__main__":
    logging.basicConfig(handlers=[logging.FileHandler('app.log', 'w', 'utf-8')],level=logging.INFO, format='%(asctime)s - %(message)s')
    args = collect_args()
    start_url = get_html(args)
    num_pages = get_num_pages(start_url)
    name_file = parse_pages(start_url, num_pages)
    print('Information written to file: '+str(name_file))
    logging.info('Parsing ended without errors')