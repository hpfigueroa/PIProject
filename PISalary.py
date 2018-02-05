# -*- coding: utf-8 -*-
"""
Created on Sun Feb  4 22:00:03 2018
@author: hpfigueroa
"""

#%% <libraries>
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd 
import numpy as np
from bs4 import BeautifulSoup
import hashlib
import random
import pprint
import requests
import time
import re
from urllib.request import urlopen

#%% <Variables>
_GOOGLEID = hashlib.md5(str(random.random()).encode('utf-8')).hexdigest()[:16]
_COOKIES = {'GSP': 'ID={0}:CF=4'.format(_GOOGLEID)}
_HEADERS = {
    'accept-language': 'en-US,en',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/41.0.2272.76 Chrome/41.0.2272.76 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml'
    }
_HOST = 'https://scholar.google.com'
_AUTHSEARCH = '/citations?view_op=search_authors&hl=en&mauthors='
_CITATIONAUTHRE = r'user=([\w-]*)'
_EMAILAUTHORRE = r'Verified email at '
_SESSION = requests.Session()
_PAGESIZE = 100

#%% <requests>
def _get_page(pagerequest):
    """Return the data for a page on scholar.google.com"""
    # Note that we include a sleep to avoid overloading the scholar server
    time.sleep(10+random.uniform(0, 5))
    resp = _SESSION.get(pagerequest, headers=_HEADERS, cookies=_COOKIES)
    if resp.status_code == 200:
        return resp.text
    else:
        raise Exception('Error: {0} {1}'.format(resp.status_code, resp.reason))

def _get_soup(pagerequest):
    """Return the BeautifulSoup for a page on scholar.google.com"""
    time.sleep(5+random.uniform(0, 5))
    html = urlopen(pagerequest).read().decode('ascii', 'ignore')
    return BeautifulSoup(html, 'html.parser')

def _search_citation_soup(soup):
    """Generator that returns Author objects from the author search page"""
    for row in soup.find_all('div', 'gsc_1usr'):
        yield Author(row)

class Author(object):
    """Returns an object for a single author"""
    def __init__(self, __data):
        if isinstance(__data, str):
            self.id = __data
        else:
            self.id = re.findall(_CITATIONAUTHRE, __data('a')[0]['href'])[0]
            self.url_picture = __data('img')[0]['src']
            self.name = __data.find('h3', class_='gsc_oai_name').text
            affiliation = __data.find('div', class_='gsc_oai_aff')
            if affiliation:
                self.affiliation = affiliation.text
            email = __data.find('div', class_='gsc_oai_eml')
            if email:
                self.email = re.sub(_EMAILAUTHORRE, r'@', email.text)
            self.interests = [i.text.strip() for i in
                              __data.find_all('a', class_='gsc_oai_one_int')]
            citedby = __data.find('div', class_='gsc_oai_cby')
            if citedby and citedby.text != '':
                self.citedby = int(citedby.text[9:])
        self._filled = False
    def __str__(self):
        return pprint.pformat(self.__dict__)
           
            
def search_author(name):
    """Search by author name and return a generator of Author objects"""
    url = _AUTHSEARCH+name
    soup = _get_soup(_HOST+url)
    print(_HOST+url)
    return _search_citation_soup(soup)

#%% <get hindex>
def parse_html_table(table):
    n_columns = 0
    n_rows=0
    column_names = []

    # Find number of rows and columns
    # we also find the column titles if we can
    for row in table.find_all('tr'):

        # Determine the number of rows in the table
        td_tags = row.find_all('td')
        if len(td_tags) > 0:
            n_rows+=1
            if n_columns == 0:
                # Set the number of columns for our table
                n_columns = len(td_tags)

        # Handle column names if we find them
        th_tags = row.find_all('th') 
        if len(th_tags) > 0 and len(column_names) == 0:
            for th in th_tags:
                column_names.append(th.get_text())

    # Safeguard on Column Titles
    if len(column_names) > 0 and len(column_names) != n_columns:
        raise Exception("Column titles do not match the number of columns")

    columns = column_names if len(column_names) > 0 else range(0,n_columns)
    df = pd.DataFrame(columns = columns,
                      index= range(0,n_rows))
    row_marker = 0
    for row in table.find_all('tr'):
        column_marker = 0
        columns = row.find_all('td')
        for column in columns:
            df.iat[row_marker,column_marker] = column.get_text()
            column_marker += 1
        if len(columns) > 0:
            row_marker += 1
    return df

def get_hindex(userid):
    gsurl = 'https://scholar.google.com/citations?user='+userid
    gshtml = urlopen(gsurl).read().decode('ascii', 'ignore')
    soup = BeautifulSoup(gshtml,"lxml")
    tagtable = soup.find_all('table')[0]
    tablevalues = parse_html_table(tagtable)
    return tablevalues
#%% <load>
file = r'./data/WaStEmployeeHistSalary.xlsx'
rawdf = pd.read_excel(file,skiprows=6)

#%%
#Professor Dataset
profdf = rawdf[rawdf['Position'].str.contains('PROFESSOR', na=False)]
#%% 
profdf = pd.concat([profdf, profdf['Name'].str.replace(" ","").str.split(',', expand=True)], axis=1)
profdf.columns.values[8] = 'Last'
profdf.columns.values[9] = 'First'
#%%
nan_rows = profdf[profdf.isnull().any(1)]
profdf = profdf.dropna()
#%%
profdf['GSid']=""
profdf['CitationsAll']=np.nan
profdf['Citations13']=np.nan
profdf['hindex']=np.nan
profdf['hindex13']=np.nan
#%% 
for k in range(0,len(profdf)):
    FirstN = profdf['First'].iloc[k]
    LastN = profdf['Last'].iloc[k]
    Authorlst = list(search_author(FirstN+'+'+LastN))
    affiliated = [False]
    if len(Authorlst)>0:
        affiliated = ['Washington' in Authorlst[i].affiliation for i in range(0,len(Authorlst))]
    if any(affiliated):
        GSuserid = [i for (i, v) in zip(Authorlst, affiliated) if v][0].id
        print(k,GSuserid)
        profdf.loc[profdf.index[k],'GSid'] = GSuserid
        indextb = get_hindex(GSuserid)
        profdf.loc[profdf.index[k],'CitationsAll'] = int(indextb.iloc[0][1])
        profdf.loc[profdf.index[k],'Citations13'] = int(indextb.iloc[0][2])
        profdf.loc[profdf.index[k],'hindex'] = int(indextb.iloc[1][1])
        profdf.loc[profdf.index[k],'hindex13'] = int(indextb.iloc[1][2])

#%% <indexing>
profdf.to_csv('./data/Washingtondata.csv')
profdf = pd.read_csv('./data/Washingtondata.csv')
#%%
plotdf = profdf[['Position','2014','2015','2016', 'First',
                    'hindex','CitationsAll','Citations13',
                    'hindex13']].copy()
plotdf = plotdf.dropna(axis=0,subset=['hindex'])

#%%
def plot_withline(x,y,cl1):
    fit = np.polyfit(x,y,1)
    fit_fn = np.poly1d(fit) 
    plt.plot(x,y/1000, cl1+'o', x, fit_fn(x)/1000, '--'+cl1)
    plt.xlim(0, 160)
    plt.ylim(0, 700)

    

x2015 = [i for i in plotdf['2015']>180000]
plot_withline(plotdf['hindex'][x2015],plotdf['2015'][x2015],'r')
plot_withline(plotdf['hindex'],plotdf['2016'],'y')
red_patch = mpatches.Patch(color='r', label='2015')
yellow_patch = mpatches.Patch(color='y', label='2016')
plt.legend(handles=[red_patch,yellow_patch])
plt.grid()
plt.show()


#%%
plotdf['Increase'] = 100*(plotdf['2016'][x2015]-plotdf['2015'][x2015])/plotdf['2015'][x2015]
plot_withline(plotdf['hindex'][x2015],1000*plotdf['Increase'][x2015],'b')
plt.ylim(-40, 40)
plt.grid()
plt.show()


#%%
x2014 = [i for i in plotdf['2014']>160000]
plot_withline(plotdf['hindex'][x2014],plotdf['2014'][x2014],'w')
plt.rcParams['axes.facecolor'] = 'white'

plt.rcParams['axes.facecolor'] = '0.25'


#%%
plt.scatter(plotdf['hindex'],plotdf['2016'])
plt.show()
plt.scatter(plotdf['CitationsAll'],plotdf['2016'])
plt.show()
    