from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Playwright 
from requisicoes import scraper_regex, create_titlesJobs_list, create_write_csv, write_in_csv
import numpy as np
import csv
import time

BASE_URL = 'https://www.trabalhabrasil.com.br/vagas-empregos-em-rio-de-janeiro-rj'


dataset = []

def run(playwright: Playwright):
    #webkit = playwright.webkit
    webkit = playwright.firefox
    browser = webkit.launch()
    context = browser.new_context()
    page = context.new_page()
    ##test_page(1);
    page.goto(BASE_URL)
    body = page.inner_html("body")
    formated = BeautifulSoup(body, 'html.parser')
    formated_class = formated.find('nav', 'jg__container').find_all('a')
    #Jobs_List= create_titlesJobs_list(formated_class)
    #regex_JobsList = scraper_regex(Jobs_List)
    #print(len(regex_JobsList))
    #return regex_JobsList

    i = 1;
    media =2.5;
    std = 0.1;
    colums = ['job', 'company']
    create_write_csv('dataset_trabalha_brasil', colums)
    create_write_csv('dataset_pages_reader', ['page'])
    while(formated_class != []):
        Jobs_List= create_titlesJobs_list(formated_class)
        regex_JobsList = scraper_regex(Jobs_List)
        dataset.extend(regex_JobsList);
        write_in_csv('dataset_trabalha_brasil', colums, regex_JobsList)
        write_in_csv('dataset_pages_reader', ['page'], [{'page': i}])
        import pdb; pdb.set_trace()
        i += 1
        print(i)
        s = np.random.normal(media, std)
        time.sleep(s)
        page.goto(BASE_URL + f"?pagina={i}")
        body = page.inner_html("body")
        time.sleep(s)
        formated = BeautifulSoup(body, 'html.parser')
        formated_class = formated.find('nav', 'jg__container').find_all('a')
        #print(regex_JobsList)
        print(len(dataset))


    return dataset
    
    
    
    #page.screenshot(path="screenshot.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
