from bs4 import BeautifulSoup
import os
from app.utils import get_relevant_images, extract_title
from tavily import TavilyClient

class TavilyExtract:
    def __init__(self, link, session=None):
        self.link = link
        self.session = session
        self.tavily_client = TavilyClient(api_key=self.get_api_key())

    def get_api_key(self) -> str:
        try:
            api_key = os.environ["TAVILY_API_KEY"]
        except KeyError:
            raise Exception(
                "Tavily API key not found. Please set the TAVILY_API_KEY environment variable.")
        return api_key

    def scrape(self) -> tuple:
        try:
            response = self.tavily_client.extract(urls=self.link)
            if not isinstance(response, dict):
                print("TavilyExtract: неожиданный формат ответа:", response)
                return "", [], ""
            if response.get('failed_results'):
                return "", [], ""
            results = response.get('results', [])
            if not isinstance(results, list) or not results:
                print("TavilyExtract: нет успешных результатов:", response)
                return "", [], ""
            response_bs = self.session.get(self.link, timeout=4)
            soup = BeautifulSoup(
                response_bs.content, "lxml", from_encoding=response_bs.encoding
            )
            content = results[0].get('raw_content', '')
            image_urls = get_relevant_images(soup, self.link)
            title = extract_title(soup)
            return content, image_urls, title
        except Exception as e:
            print("Error! : " + str(e))
            return "", [], "" 