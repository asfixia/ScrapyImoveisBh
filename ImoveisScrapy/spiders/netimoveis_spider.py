from collections import defaultdict

import scrapy
import requests
import json
import math
import logging
import pip

#Adiciona ao path o ./exe e o /firefox.exe
#pip install selenium
class NetImoveisSpider(scrapy.Spider):
    name = "NetImoveis"
    perPage = 14

    @staticmethod
    def install(package):
        if hasattr(pip, 'main'):
            pip.main(['install', package])
        else:
            from pip._internal import main as pip_main
            if hasattr(pip_main, 'main'):
                pip_main.main(['install', package])
            else:
                pip_main(['install', package])

    startUrl = 'https://www.netimoveis.com/locacao/minas-gerais/belo-horizonte/apartamento?tipo=apartamento&transacao=locacao&quartos=3&valorMin=1000&valorMax=2000&vagas=1&banhos=1&localizacao=BR-MG-belo-horizonte---&areaMin=90&areaMax=150&pagina=1'

    def getPageUrl(self, iPage):
        return 'https://www.netimoveis.com/pesquisa?tipo=apartamento&transacao=locacao&quartos=3&valorMin=1000&valorMax=2000&vagas=1&banhos=1&localizacao=%5B%7B%22urlEstado%22%3A%22minas-gerais%22%2C%22urlCidade%22%3A%22belo-horizonte%22%2C%22urlRegiao%22%3A%22%22%2C%22urlBairro%22%3A%22%22%2C%22urlLogradouro%22%3A%22%22%2C%22idLocalizacao%22%3A%22BR-MG-belo-horizonte---%22%7D%5D&areaMin=90&areaMax=150&areaMaxima=150&areaMinima=90&valorMinimo=1000&valorMaximo=2000&outrasPags=true&pagina=' + str(iPage)

    def getDefaultHeaders(self, iPage):
        return {
            "Host": "www.netimoveis.com",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36",
            "Sec-Fetch-Dest": "document",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            #'referer': self.startUrl,
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def updateCookie(self, cookie):
        defaultCookie = self.getDefaultCookie()
        if not isinstance(cookie, list):
            cookie = [cookie]

        for curDomain in cookie:
            if not "domain" in curDomain or ".netimoveis.com" in curDomain["domain"] != -1:
                for key in curDomain:
                    defaultCookie[key] = curDomain[key]
        return defaultCookie

    def getDefaultCookie(self):
        return {
            "__trf.src": "encoded_eyJmaXJzdF9zZXNzaW9uIjp7InZhbHVlIjoiKG5vbmUpIiwiZXh0cmFfcGFyYW1zIjp7fX0sImN1cnJlbnRfc2Vzc2lvbiI6eyJ2YWx1ZSI6Iihub25lKSIsImV4dHJhX3BhcmFtcyI6e319LCJjcmVhdGVkX2F0IjoxNTgxMTc5Mzk1Mjc5fQ==",
            "_ga": "GA1.2.76456714.1581179395",
            "_gid": "GA1.2.1749620787.1581179395",
            "_gcl_au": "1.1.388234817.1581179395",
            "_st_ses": "5322072311717163",
            "_fbp": "fb.1.1581179396071.997022072",
            "_sptid": "4972",
            "_spcid": "4584",
            "_spl_pv": "1",
            "_st_no_user": "1",
            "_cm_ads_activation_retry": "false",
            "sback_browser": "0-27148100-15811794100f15321603dfdfbfceffa4465c7f9cc8e130d0ed876091075e3ee212424970-82190255-17918617259,5418223376-1581179410",
            "_st_cart_script": "customizada_cart.js",
            "_st_cart_url": "null",
            "rl_visitor_history": "8633e68c-5eb7-4835-bd94-bfee42c5a625",
            "rdtrk": "%7B%22id%22%3A%22670a7c06-eb61-4369-8ab2-ff6f72c926c3%22%7D",
            "sback_client": "5bf7fa285071c1b7220bf304",
            "sback_customer": "$2wcxAVVYJTMNNDbBZldtFWTkhXONRnaZ50QqllT6dlYNNFelF1YU5UWOpWcohmeR50TwwUTF1mUaZTe3UlZtlmT2$12",
            "sback_access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuc2JhY2sudGVjaCIsImlhdCI6MTU4MTE3OTQxMSwiZXhwIjoxNTgxMjY1ODExLCJhcGkiOiJ2MiIsImRhdGEiOnsiY2xpZW50X2lkIjoiNWJmN2ZhMjg1MDcxYzFiNzIyMGJmMzA0IiwiY2xpZW50X2RvbWFpbiI6Im5ldGltb3ZlaXMuY29tIiwiY3VzdG9tZXJfaWQiOiI1ZTNlZTIxMzZjYzExNGFjODc0Y2YyZTYiLCJjdXN0b21lcl9hbm9ueW1vdXMiOnRydWUsImNvbm5lY3Rpb25faWQiOiI1ZTNlZTIxMzZjYzExNGFjODc0Y2YyZTciLCJhY2Nlc3NfbGV2ZWwiOiJjdXN0b21lciJ9fQ.sUa1ZZVlY9gqKLxx1vCF0o05t0aBCH5-3tPNQvlfeKo.WrWrDriYWrWrEiHezRWrWr",
            "sback_partner": "false",
            "sback_current_session": "1",
            "sback_total_sessions": "1",
            "sb_days": "1581179398297",
            "sback_customer_w": "true",
            "sback_refresh_wp": "no"
        }


    def start_requests(self):
        # #NetImoveisSpider.install("selenium")
        # from selenium import webdriver
        # driver = webdriver.Firefox()
        # driver.get(self.startUrl)
        # cookies = driver.get_cookies()
        # newCookie = {}
        # for curCookie in cookies:
        #     newCookie[curCookie["name"]] = curCookie["value"]
        # logging.warning(cookies)
        # #requests.get(self.startUrl, headers=self.getDefaultHeaders(1))
        # logging.warning("BASE URL: \n\n\n" + self.getPageUrl(1))
        # logging.warning(cookies)
        # newCookie = self.updateCookie(newCookie)
        # res = requests.get(self.getPageUrl(1)).text
        # logging.warning("AAAAAEEEEEEE" + res)
        respJson = json.loads(requests.get(self.getPageUrl(1)).text)
        #logging.warning("RESP JSON: " + str(respJson))
        #logging.warning("TOTAL: " + str(respJson["totalDeRegistros"]))
        totalImoveis = respJson["totalDeRegistros"]
        logging.warning("TOTAL DE registros: " + str(totalImoveis))
        for pageInd in range(int(math.floor(totalImoveis/self.perPage))):
            yield scrapy.Request(url=self.getPageUrl(pageInd + 1), callback=self.parse)
            #yield scrapy.Request(url=self.getPageUrl(1), cookies=self.getCookie(), headers=self.getDefaultHeaders(), callback=self.parse)


    def parse(self, response):
        print(response)
        page = response.url.split("pagina=")[-1]
        responseJson = json.loads(response.text)
        #if bool(responseJson.erro):
        filename = (self.name + '--%s.html') % page
        with open(filename, 'wb') as f:
            f.write(json.dumps(responseJson))
        self.log('Saved file %s' % filename)
        for item in responseJson["lista"]:
            yield {
                'lat': item["latitude2"],
                'long': item["longitude2"],
                'url': "www.netimoveis.com/" + item["urlDetalheImovel"],
                'video': item["embedVideo"],
                'thumb': item["nomeArquivoThumb"],
                '360': item["embed360"],
                'data': item["dataHora"],
                'bairro': item["nomeBairro"],
                'venda': item["valorImovel"],
                'aluguel': item["valorLocacao"],
                'condominio': item["valorCondominio"],
                'iptu': item["valorIPTU"],
                'iptu_parcelas': item["parcelaIPTU"],
                'vagas': item["vagaGaragem"],
                'quartos': item["quartos"],
                'banheiros': item["banho"],
                'area': item["areaRealPrivativa"] or item["areaConstruida"],
                'logradouro': item["logradouroAutoComplete_url"],
                'descricao': item["textoComplementar"],

                'full': json.dumps(item)
            }