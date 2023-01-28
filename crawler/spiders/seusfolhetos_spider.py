from time import sleep
import scrapy
import os
import requests
import shutil
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

class SeusFolhetosSpider(scrapy.Spider):
    name = "seusfolhetos"
    start_urls = [
        'https://seusfolhetos.com.br/arquivo/carrefour',
        'https://seusfolhetos.com.br/arquivo/atacadao',
        'https://seusfolhetos.com.br/arquivo/big',
        'https://seusfolhetos.com.br/arquivo/assai-atacadista',
        'https://seusfolhetos.com.br/arquivo/nacional',
        'https://seusfolhetos.com.br/arquivo/bompreco',
        'https://seusfolhetos.com.br/arquivo/gbarbosa',
        'https://seusfolhetos.com.br/arquivo/cooper',
        'https://seusfolhetos.com.br/arquivo/supermercados-imperatriz',
        'https://seusfolhetos.com.br/arquivo/economico-atacadao'
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.driver = webdriver.Chrome(ChromeDriverManager().install())

    def parse(self, response):
        print(f"response =  {response}")
        years = ["2022"]
        months = ["01"]
        months_elements = []
        for year in years:
            if len(months) == 0:
                months_elements += response.css(f'div.year ~ a[href*="{year}"]::attr(href)').getall()
            else:
                for month in months:
                    months_elements += response.css(f'div.year ~ a[href*="{month}-{year}"]::attr(href)').getall()

        yield from response.follow_all(months_elements, self.parse_months)

    def parse_months(self, response):
        url = response.url.split('/')
        path = f'folhetos/{url[-2]}/'
        os.makedirs(path, exist_ok=True)
        month, year = url[-1].split("-")

        self.driver.get(response.url)
        sleep(3)
        try:
            button = self.driver.find_element_by_css_selector('a.button-load.next-button')
            while button:
                try:
                    button.click()
                    self.driver.set_script_timeout(30)
                    button = self.driver.find_element_by_css_selector('a.button-load.next-button')
                except:
                    break
        except:
            pass

        valores = self.driver.execute_script("""
            var titles = []; 
            var links = [];
            var all = document.querySelectorAll("div.frame a.leaflet-img-mobile-detail-flex"); 
            for (var i=0, max=all.length; i < max; i++) { 
                titles.push(all[i].getAttribute('title')); 
                links.push(all[i].getAttribute('href')); 
            } 
            return {titles, links};
        """)
        sleep(1)
        titles = valores['titles']
        links = valores['links']
        flyers = list(dict(zip(titles, links)).values())
        yield from response.follow_all(flyers, self.parse_flyers)

        with open(f'{path}/log.txt', 'a') as f:
            f.write(f'{month}-{year}\n')

    def parse_flyers(self, response):
        url = response.url.split('/')
        #replace = url[-2].replace("-ofertas", "").replace("-hiper", "").replace("-market", "").replace("-drogaria", "")\
        #    .replace("-bairro", "").replace("mini-", "").replace("postos-", "").replace("mercado-", "")
        #path = f'folhetos/{replace}/'
        path = f'folhetos/'
        nome = f'{url[-1]}.jpg'
        filename = f'{path}{nome}'

        if not os.path.exists(filename):
            url_image = response.css('#leaflet::attr(src)').get()
            sleep(1)
            r = requests.get(url_image, stream=True)
            sleep(3)
            r.raw.decode_content = True
            with open(filename, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        next_page = response.css('div.numbers a[rel="next"]::attr(href)').get()
        sleep(1)
        if next_page is not None:
            yield response.follow(next_page, self.parse_flyers)
