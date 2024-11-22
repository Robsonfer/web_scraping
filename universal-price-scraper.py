import requests
from bs4 import BeautifulSoup
import pandas as pd
import concurrent.futures
from urllib.parse import quote_plus, urlparse
import re

class UniversalPriceTracker:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.search_engines = [
            'https://www.google.com/search?q=',
            'https://www.bing.com/search?q='
        ]

    def _clean_price(self, price_text):
        """Limpa e converte texto de preço para float"""
        price_text = price_text.replace('R$', '').replace('.', '').replace(',', '.')
        price_matches = re.findall(r'\d+\.\d+', price_text)
        return float(price_matches[0]) if price_matches else None

    def _extract_domain(self, url):
        """Extrai domínio da URL"""
        return urlparse(url).netloc.replace('www.', '')

    def search_product_prices(self, product_name, max_results=10):
        """
        Busca preços de um produto em múltiplos sites
        
        :param product_name: Nome do produto a ser buscado
        :param max_results: Número máximo de resultados
        :return: DataFrame com preços
        """
        results = []

        def search_engine_scrape(search_url):
            try:
                response = requests.get(
                    search_url + quote_plus(product_name + " preço"),
                    headers=self.headers
                )
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extrai links de resultados
                links = []
                for link in soup.find_all('a', href=True):
                    url = link['href']
                    if url.startswith('http') and not any(blocked in url for blocked in [
                        'google.com', 'bing.com', 'youtube.com'
                    ]):
                        links.append(url)
                
                return links[:max_results]
            except Exception as e:
                print(f"Erro na busca: {e}")
                return []

        # Busca em múltiplos motores de busca
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            search_futures = [
                executor.submit(search_engine_scrape, engine) 
                for engine in self.search_engines
            ]
            
            all_links = []
            for future in concurrent.futures.as_completed(search_futures):
                all_links.extend(future.result())

        def scrape_product_page(url):
            try:
                response = requests.get(url, headers=self.headers, timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')

                # Tentativa de encontrar preços usando múltiplas estratégias
                price_selectors = [
                    'meta[property="product:price:amount"]',
                    '.price', '.product-price', 
                    '[data-price]', '#price',
                    '.preco', '.valor'
                ]

                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get('content', '') or price_element.get_text()
                        price = self._clean_price(price_text)
                        
                        if price:
                            return {
                                'site': self._extract_domain(url),
                                'price': price,
                                'url': url
                            }
            except Exception as e:
                print(f"Erro ao extrair preço de {url}: {e}")
            
            return None

        # Extração de preços em paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            price_futures = [
                executor.submit(scrape_product_page, link) 
                for link in set(all_links)
            ]
            
            for future in concurrent.futures.as_completed(price_futures):
                result = future.result()
                if result:
                    results.append(result)

        # Converte para DataFrame e ordena
        df = pd.DataFrame(results)
        return df.sort_values('price').drop_duplicates(subset=['site'])

def main():
    tracker = UniversalPriceTracker()
    
    # Exemplo de uso
    product_name = input("Digite o nome do produto: ")
    result = tracker.search_product_prices(product_name)
    
    print("\n--- Comparativo de Preços ---")
    print(result)
    print("\nPara detalhes, visite os links acima.")

if __name__ == "__main__":
    main()
