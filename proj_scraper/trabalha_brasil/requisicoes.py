from bs4 import BeautifulSoup
import re
from playwright.sync_api import sync_playwright, Playwright
import csv
url = 'https://www.trabalhabrasil.com.br/vagas-empregos-em-rio-de-janeiro-rj'



def html_formated(site):
    import pdb; pdb.set_trace()
    formated = BeautifulSoup(site, 'html.parser')
    return formated


def find_all_class(formated, tag = str, class_content = str):
  return formated.find_all(tag,attrs={ 'class' : f"{class_content}"})

def create_titlesJobs_list(formated):
  list_jobs = []
  for i in formated:
    list_jobs.append(i['title'])
  return list_jobs


def scraper_regex(formated):
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

def create_write_csv(name, colums):
  with open(f'{name}.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=colums)
    writer.writeheader()

def write_in_csv(name, colums, data):
  with open(f'{name}.csv', 'a', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=colums)
    if(type(data) != list):
      writer.writerow(data)
    for item in data:
        writer.writerow(item)
