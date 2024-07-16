import requests
from bs4 import BeautifulSoup
import re

url = 'https://www.trabalhabrasil.com.br/vagas-empregos-em-rio-de-janeiro-rj'

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}



def request(url, headers):
  global site
  site = requests.get(url, headers=headers)
  #status = site.status_code
  #print(status)
  return site

def html_formated(site):
  formated = BeautifulSoup(site, 'html.parser')
  return formated


def find_all_class(formated, tag = str, class_content = str):
  return formated.find_all(tag,attrs={ 'class' : f"{class_content}"})

def create_titlesJobs_list(formated):
  list_jobs = []
  for i in formated:
    list_jobs.append(i['title'])
  return list_jobs


def scrapper_regex(formated):
  new_list = []
  for i in formated:
    result_search = re.search(r'.*para (.*) na empresa (.*) em', i)
    if result_search:
        item = {
          'job': result_search.group(1),
          'company': result_search.group(2)
        }
        new_list.append(item)
  return new_list

