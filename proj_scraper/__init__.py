__version__ = '0.1.0'

from bs4 import BeautifulSoup
from proj_scraper.trabalha_brasil.requisicoes import url, headers, request, html_formated, find_all_class, create_titlesJobs_list, scrapper_regex
[headers, url] = headers, url


site = request(url, headers)

print(site)

contentInSite = site.content
#print(contentInSite)

html_formated = html_formated(contentInSite)

#print(html_formated)

find_all_class = find_all_class(html_formated, 'a', 'jobCard highlighted')
#print(find_all_class)


create_titlesJobs_list = create_titlesJobs_list(find_all_class)
#print(create_titlesJobs_list)

scrapper_regex = scrapper_regex(create_titlesJobs_list)
print(scrapper_regex)

## Pensando em criar uma class para instânciar objetos com as informações de cada vaga
# class Vaga:
#  def __init__(self, titulo, empresa, local):
#   self.titulo = titulo
#  self.empresa = empresa
# self.local = local

