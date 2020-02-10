from collections import defaultdict

import scrapy
import requests
import json
import math
import logging
import pip



class ZapImoveisSpider(scrapy.Spider):
    name = "ZapImoveis"
    startUrl = 'https://www.zapimoveis.com.br/aluguel/apartamentos/mg+belo-horizonte/3-quartos/?onde=,Minas%20Gerais,Belo%20Horizonte,,,,BR%3EMinas%20Gerais%3ENULL%3EBelo%20Horizonte,-19.916681,-43.934493&banheiros=2&quartos=3&transacao=Aluguel&vagas=1&precoMaximo=2000&precoMinimo=1000&areaMaxima=150&areaMinima=90&tipoUnidade=Residencial,Apartamento&tipo=Im%C3%B3vel%20usado&pagina=1'
    pageSize = 36

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

    def getDefaultHeaders(self, iPage):
        # return {
        #     "alt-svc": "h3-24=\":443\"; ma=86400, h3-23=\":443\"; ma=86400",
        #     "cache-control": "public, max-age=14400",
        #     "cf-cache-status": "MISS",
        #     "cf-ray": "5626097089a6f60f-GRU",
        #     "content-encoding": "br",
        #     "content-type": "text/html; charset=utf-8",
        #     # "date": "Sun, 09 Feb 2020 13:02:18 GMT",
        #     # "expect-ct": "max-age=604800, report-uri=\"https://report-uri.cloudflare.com/cdn-cgi/beacon/expect-ct\"",
        #     # "expires": "Sun, 09 Feb 2020 17:02:18 GMT",
        #     "server": "cloudflare",
        #     "status": "200",
        #     "strict-transport-security": "max-age=15724800, max-age=31536000; includeSubDomains; preload",
        #     "vary": "Accept-Encoding",
        #     "x-content-type-options": "nosniff",
        #     "x-dns-prefetch-control": "off",
        #     "x-download-options": "noopen",
        #     # "x-frame-options": "SAMEORIGIN",
        #     # "x-xss-protection": "1; mode=block",
        #     ":authority": "www.zapimoveis.com.br",
        #     ":method": "GET",
        #     ":path": "/aluguel/apartamentos/?banheiros=2&quartos=3&transacao=Aluguel&vagas=1&precoMaximo=2000&precoMinimo=1000&areaMaxima=150&areaMinima=90&tipoUnidade=Residencial,Apartamento&tipo=Im%C3%B3vel%20usado&pagina=" + str(iPage),
        #     ":scheme": "https",
        #     "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        #     "accept-encoding": "gzip, deflate, br",
        #     "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        # }
        return {
            "Sec-Fetch-Dest": "document",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36"
        }

    def getPageHeader(self, iPage):
        return {
            # ":authority": "glue-api.zapimoveis.com.br",
            # ":method": "GET",
            # ":path": "/v2/listings?addressCountry=&addressState=&addressCity=&addressZone=&addressNeighborhood=&addressStreet=&addressLocationId=&addressPointLat=&addressPointLon=&unitSubTypes=UnitSubType_NONE,DUPLEX,TRIPLEX&unitTypes=APARTMENT&usageTypes=RESIDENTIAL&unitTypesV3[]=APARTMENT&text=Apartamento&size="+str(self.pageSize)+"&from="+str(iPage * self.pageSize)+"&categoryPage=RESULT&business=RENTAL&listingType=USED&priceMin=1000&priceMax=2000&bedrooms=3&bathrooms=2&usableAreasMin=90&usableAreasMax=150&parkingSpaces=1&parentId=null&page=2&includeFields=search,page,fullUriFragments,developments,superPremium&developmentsSize=3&superPremiumSize=3&__zt=",
            # ":scheme": "https",
            "accept": "application/json, text/plain, */*",
            #"accept-encoding": "gzip, deflate, br",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://www.zapimoveis.com.br",
            "referer": "https://www.zapimoveis.com.br/aluguel/apartamentos/mg+belo-horizonte/3-quartos/?onde=,Minas%20Gerais,Belo%20Horizonte,,,,BR%3EMinas%20Gerais%3ENULL%3EBelo%20Horizonte,-19.916681,-43.934493&banheiros=2&quartos=3&transacao=Aluguel&vagas=1&precoMaximo=2000&precoMinimo=1000&areaMaxima=150&areaMinima=90&tipoUnidade=Residencial,Apartamento&tipo=Im%C3%B3vel%20usado&pagina=" + str(iPage),
            # "sec-fetch-dest": "empty",
            # "sec-fetch-mode": "cors",
            # "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36",
            "x-domain": "www.zapimoveis.com.br"
        }

    def updateCookie(self, cookie):
        defaultCookie = self.getDefaultCookie()
        if not isinstance(cookie, list):
            cookie = [cookie]

        for curDomain in cookie:
            if not "domain" in curDomain or ".zapimoveis.com.br" in curDomain["domain"] != -1:
                for key in curDomain:
                    defaultCookie[key] = curDomain[key]
        return defaultCookie

    def getPageUrl(self, iPage, cTry=0):
        # print("Pagina {}...".format(pagina))
        # url = 'https://www.zapimoveis.com.br/Busca/RetornarBuscaAssincrona/'
        # # url = 'https://www.zapimoveis.com.br/aluguel/apartamentos/mg+belo-horizonte/#{"precomaximo":"2147483647","parametrosautosuggest":[{"Bairro":"","Zona":"","Cidade":"BELO%20HORIZONTE","Agrupamento":"","Estado":"MG"}],"pagina":9,"ordem":"Relevancia","paginaOrigem":"ResultadoBusca","semente":"893405925","formato":"Lista"}'
        # print('Current Url: ' + url)
        # # 'https://www.zapimoveis.com.br/venda/apartamentos/mg+belo-horizonte/3-quartos/#{"precomaximo":"400000","filtrodormitorios":"3;","areautilminima":"60","parametrosautosuggest":[{"Bairro":"","Zona":"","Cidade":"BELO%20HORIZONTE","Agrupamento":"","Estado":"MG"}],"pagina":"'+str(pagina)+'","ordem":"Relevancia","paginaOrigem":"ResultadoBusca","semente":"202082721","formato":"Lista"}'
        # data = 'tipoOferta=Imovel&paginaAtual=' + str(
        #     pagina) + '&ordenacaoSelecionada=Relevancia&pathName=%2Faluguel%2Fapartamentos%2Fmg%2Bbelo-horizonte%2F&hashFragment=%7B%22precomaximo%22%3A%222147483647%22%2C%22parametrosautosuggest%22%3A%5B%7B%22Bairro%22%3A%22%22%2C%22Zona%22%3A%22%22%2C%22Cidade%22%3A%22BELO+HORIZONTE%22%2C%22Agrupamento%22%3A%22%22%2C%22Estado%22%3A%22MG%22%7D%5D%2C%22pagina%22%3A' + str(
        #     pagina) + '%2C%22ordem%22%3A%22Relevancia%22%2C%22paginaOrigem%22%3A%22ResultadoBusca%22%2C%22semente%22%3A%22893405925%22%2C%22formato%22%3A%22Lista%22%7D&formato=Lista'
        # return {'pagina': pagina, 'try': cTry, 'url': url,
        #         'rq': self.executor.submit(requests.post, url, data=data, headers=self.agent, proxies=self.getProxy(),
        #                                    timeout=25)}
        #url = 'https://www.zapimoveis.com.br/aluguel/apartamentos/mg+belo-horizonte/2-quartos/#{%22filtrodormitorios%22:%223;2;4;%22,%22areautilminima%22:%2260%22,%22areautilmaxima%22:%22180%22,%22possuiendereco%22:%22True%22,%22parametrosautosuggest%22:[{%22Bairro%22:%22%22,%22Zona%22:%22%22,%22Cidade%22:%22BELO%20HORIZONTE%22,%22Agrupamento%22:%22%22,%22Estado%22:%22MG%22}],%22pagina%22:%221%22,%22paginaOrigem%22:%22ResultadoBusca%22,%22semente%22:%22306391789%22,%22formato%22:%22Lista%22}'
        # 'https://www.zapimoveis.com.br/venda/apartamentos/mg+belo-horizonte/3-quartos/#{"precomaximo":"400000","filtrodormitorios":"3;","areautilminima":"60","parametrosautosuggest":[{"Bairro":"","Zona":"","Cidade":"BELO%20HORIZONTE","Agrupamento":"","Estado":"MG"}],"pagina":"'+str(pagina)+'","ordem":"Relevancia","paginaOrigem":"ResultadoBusca","semente":"202082721","formato":"Lista"}'
        return 'https://glue-api.zapimoveis.com.br/v2/listings?addressCountry=&addressState=Minas+Gerais&addressCity=Belo+Horizonte&addressZone=&addressNeighborhood=&addressStreet=&addressLocationId=BR%3EMinas+Gerais%3ENULL%3EBelo+Horizonte&addressPointLat=-19.916681&addressPointLon=-43.934493&unitSubTypes=UnitSubType_NONE,DUPLEX,TRIPLEX&unitTypes=APARTMENT&usageTypes=RESIDENTIAL&unitTypesV3[]=APARTMENT&text=Apartamento&size=' + str(self.pageSize) + '&from=' + str(self.pageSize * iPage) + '&categoryPage=RESULT&bathrooms=2&bedrooms=3&business=RENTAL&parkingSpaces=1&priceMax=2000&priceMin=1000&usableAreasMax=150&usableAreasMin=90&parentId=null&listingType=USED&includeFields=search,page,fullUriFragments,developments,superPremium&developmentsSize=3&superPremiumSize=3&__zt=&page=' + str(iPage)



    def start_requests(self):
        # from selenium import webdriver
        # # driver = webdriver.Firefox()
        # # driver.get(self.startUrl)
        # # cookies = driver.get_cookies()
        startResp = requests.get(self.startUrl, headers=self.getDefaultHeaders(1))
        totalImoveis = int(startResp.text.split("js-summary-title heading-regular heading-regular__bold align-left results__title\">")[1].split(" apartamentos ")[0].replace(",", "").replace(".", ""))
        logging.warning("Total de Imoveis: " + str(totalImoveis))
        logging.warning(startResp.cookies)
        for pageInd in range(int(math.floor(totalImoveis/self.pageSize))):
            yield scrapy.Request(url=self.getPageUrl(pageInd + 1), callback=self.parse, headers=self.getPageHeader(pageInd + 1))#, cookies=startResp.cookies.get_dict())

    def getThumbItem(self, item):
        imgs = [img for img in item["medias"] if img["type"] == "IMAGE"]
        if len(imgs) > 0:
            return imgs[0]["url"].replace("{action}", "view").replace("{width}", "600").replace("{height}", "400")
        return ""

    def getVideoItem(self, item):
        imgs = [img for img in item["medias"] if img["type"] != "IMAGE"]
        if len(imgs) > 0:
            return imgs[0]["url"].replace("{action}", "view").replace("{width}", "600").replace("{height}", "400")
        return 0

    def parse(self, response):
        # logging.warning(response)
        page = response.url.split("page=")[-1]
        filename = (self.name + '--%s.html') % page
        responseJson = json.loads(response.text)
        with open(filename, 'wb') as f:
            f.write(json.dumps(responseJson))
        logging.warning("RESPONSE:  \n " + response.text)
        for item in responseJson["search"]["result"]["listings"]:
            logging.warning("Item desc:  \n " + json.dumps(item))
            yield {
                'lat': item["listing"]["address"]["point"]["lat"],
                'long': item["listing"]["address"]["point"]["lon"],
                'url': "www.zapimoveis.com.br/" + item["link"]["href"],
                'video': self.getVideoItem(item),
                'thumb': self.getThumbItem(item),
                '360': "",
                'data': item["listing"]["updatedAt"] or item["listing"]["createdAt"],
                'bairro': item["listing"]["address"]["neighborhood"],
                'venda': 0,
                'aluguel': int([price["price"] for price in item["listing"]["pricingInfos"] if price["businessType"] == "RENTAL"][0]),
                'condominio': int([price["monthlyCondoFee"] for price in item["listing"]["pricingInfos"] if price["businessType"] == "RENTAL"][0]),
                'iptu': int([price["yearlyIptu"] for price in item["listing"]["pricingInfos"] if price["businessType"] == "RENTAL"][0]),
                'iptu_parcelas': 12,
                'vagas': sum(item["listing"]["parkingSpaces"]),
                'quartos': sum(item["listing"]["suites"]) + sum(item["listing"]["bedrooms"]),
                'banheiros': sum(item["listing"]["bathrooms"]),
                'area': sum([float(area) for area in item["listing"]["usableAreas"]]),
                'logradouro': item["listing"]["address"]["street"] + ", bairro: " + item["listing"]["address"]["complement"] + ", bairro: " + item["listing"]["address"]["neighborhood"] + ", CEP: " + item["listing"]["address"]["zipCode"],
                'descricao': item["listing"]["description"],

                'full': json.dumps(item)
            }
