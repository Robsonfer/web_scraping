import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict
import concurrent.futures
import urllib3
urllib3.disable_warnings()

class PriceTracker:
    def __init__(self, sites_config: Dict[str, Dict]):
        """
        Inicializa o rastreador de preços com configurações dos sites.
        
        :param sites_config: Dicionário com configurações de cada site
        """
        self.sites_config = sites_config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def _fetch_price(self, site_name: str, url: str) -> Dict:
        """
        Busca o preço de um produto em um site específico.
        
        :param site_name: Nome do site
        :param url: URL do produto
        :return: Dicionário com informações do produto
        """
        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            selector = self.sites_config[site_name]['price_selector']
            price_element = soup.select_one(selector)
            
            if price_element:
                price_text = price_element.get_text().strip()
                price = float(price_text.replace('R$', '').replace('.', '').replace(',', '.'))
                
                return {
                    'site': site_name,
                    'price': price,
                    'url': url
                }
        except Exception as e:
            print(f"Erro ao buscar preço de {site_name}: {e}")
        
        return None

    def track_product_prices(self, product_urls: List[str]) -> pd.DataFrame:
        """
        Rastreia preços de um produto em múltiplos sites.
        
        :param product_urls: Lista de URLs do mesmo produto em diferentes sites
        :return: DataFrame com preços ordenados
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for url in product_urls:
                site_name = next(
                    (site for site, config in self.sites_config.items() 
                     if config['domain'] in url), 
                    'Unknown'
                )
                futures.append(
                    executor.submit(self._fetch_price, site_name, url)
                )
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        df = pd.DataFrame(results)
        return df.sort_values('price') if not df.empty else pd.DataFrame()

# Exemplo de configuração de sites
sites_config = {
    'Magazine Luiza': {
        'domain': 'magazineluiza.com.br',
        'price_selector': '.price__current'
    },
    'Amazon': {
        'domain': 'amazon.com.br',
        'price_selector': '.a-price-whole'
    },
    'Americanas': {
        'domain': 'americanas.com.br',
        'price_selector': '[data-testid="price-value"]'
    }
}

def main():
    tracker = PriceTracker(sites_config)
    
    # URLs de um mesmo produto
    product_urls = [
        'https://www.magazineluiza.com.br/exemplo-produto',
        'https://www.amazon.com.br/exemplo-produto',
        'https://www.americanas.com.br/exemplo-produto'
    ]
    
    result = tracker.track_product_prices(product_urls)
    print(result)

if __name__ == "__main__":
    main()
