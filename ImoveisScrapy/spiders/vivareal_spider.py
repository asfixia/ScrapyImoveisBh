from collections import defaultdict

import scrapy
import requests
import json
import math
import logging
import time
import pip

#Adiciona ao path o ./exe e o /firefox.exe
#pip install selenium
class VivaRealSpider(scrapy.Spider):
    name = "VivaReal"
    startUrl = "https://www.vivareal.com.br/aluguel/minas-gerais/belo-horizonte/#area-ate=250&area-desde=40&banheiros=1&onde=BR-Minas_Gerais-NULL-Belo_Horizonte,BR-Minas_Gerais-NULL-Contagem,BR-Minas_Gerais-NULL-Betim&preco-ate=2200&preco-desde=300&tipos=apartamento_residencial,casa_residencial,condominio_residencial,flat_residencial"
    pageSize = 36

    def getPageUrl(self, iPage):
        return 'https://glue-api.vivareal.com/v2/listings?addressCity=Belo%20Horizonte%2CBetim%2CContagem&addressLocationId=BR%3EMinas%20Gerais%3ENULL%3EBelo%20Horizonte%2CBR%3EMinas%20Gerais%3ENULL%3EBetim%2CBR%3EMinas%20Gerais%3ENULL%3EContagem&addressNeighborhood=%2C%2C&addressState=Minas%20Gerais%2CMinas%20Gerais%2CMinas%20Gerais&addressCountry=BR%2CBR%2CBR&addressStreet=%2C%2C&addressZone=%2C%2C&addressPointLat=-19.9166813%2C-19.9673078%2C-19.91615&addressPointLon=-43.9344931%2C-44.2011904%2C-44.080876&usableAreasMin=40&usableAreasMax=250&bathrooms=1&business=RENTAL&facets=amenities&unitTypes=APARTMENT%2CHOME%2CCONDOMINIUM%2CFLAT&unitSubTypes=%7C%7C%7C&unitTypesV3=%2C%2C%2C&usageTypes=%2C%2C%2C&priceMin=300&priceMax=2200&listingType=USED&parentId=null&categoryPage=RESULT&includeFields=page%2Csearch%2Cexpansion%2Cnearby%2CfullUriFragments%2Caccount%2Cowners%2Cboosted&q=&developmentsSize=5&__vt=&size=' + str(self.pageSize) + '&from=' + str(self.pageSize * iPage) + '&page=' + str(iPage)
        # return 'https://glue-api.vivareal.com/v2/listings?addressCity=Belo%20Horizonte%2CContagem%2CBetim&addressLocationId=BR%3EMinas%20Gerais%3ENULL%3EBelo%20Horizonte%3EBarrios%3EVenda%20Nova%2CBR%3EMinas%20Gerais%3ENULL%3EContagem%2CBR%3EMinas%20Gerais%3ENULL%3EBetim&addressNeighborhood=Venda%20Nova%2C%2C&addressState=Minas%20Gerais%2CMinas%20Gerais%2CMinas%20Gerais&addressCountry=BR%2CBR%2CBR&addressStreet=%2C%2C&addressZone=Bairros%2C%2C&addressPointLat=-19.815959%2C-19.91615%2C-19.9673078&addressPointLon=-43.952023%2C-44.080876%2C-44.2011904&usableAreasMin=45&usableAreasMax=250&bathrooms=1&business=RENTAL&facets=amenities&unitTypes=APARTMENT%2CHOME%2CHOME%2CAPARTMENT&unitSubTypes=UnitSubType_NONE%2CDUPLEX%2CLOFT%2CSTUDIO%2CTRIPLEX%7CUnitSubType_NONE%2CSINGLE_STOREY_HOUSE%2CVILLAGE_HOUSE%2CKITNET%7CCONDOMINIUM%7CFLAT&unitTypesV3=APARTMENT%2CHOME%2CCONDOMINIUM%2CFLAT&usageTypes=RESIDENTIAL%2CRESIDENTIAL%2CRESIDENTIAL%2CRESIDENTIAL&priceMin=300&priceMax=2200&listingType=USED&parentId=null&categoryPage=RESULT&includeFields=page%2Csearch%2Cexpansion%2Cnearby%2CfullUriFragments%2Caccount%2Cowners%2Cboosted&size=' +str(self.pageSize)+ '&from='+str(self.pageSize * iPage)+'&q=&developmentsSize=5&__vt=' + "&page=" + str(iPage)
        # return 'https://glue-api.vivareal.com/v2/listings?addressCity=Belo%20Horizonte&addressLocationId=BR%3EMinas%20Gerais%3ENULL%3EBelo%20Horizonte&addressNeighborhood=&addressState=Minas%20Gerais&addressCountry=BR&addressStreet=&addressZone=&addressPointLat=-19.91615&addressPointLon=-44.080876&usableAreasMin=90&usableAreasMax=150&bathrooms=2&bedrooms=3&business=RENTAL&facets=amenities&unitTypes=APARTMENT&unitSubTypes=UnitSubType_NONE%2CDUPLEX%2CLOFT%2CSTUDIO%2CTRIPLEX&unitTypesV3=APARTMENT&usageTypes=RESIDENTIAL&rentalTotalPriceMin=1000&rentalTotalPriceMax=2000&parkingSpaces=1&listingType=USED&parentId=null&categoryPage=RESULT&includeFields=page%2Csearch%2Cexpansion%2Cnearby%2CfullUriFragments%2Caccount&size=' + str(self.pageSize) + '&from=' + str(self.pageSize * iPage) + '&sort=pricingInfos.rentalInfo.monthlyRentalTotalPrice%20ASC%20sortFilter%3ApricingInfos.businessType%3D%27RENTAL%27&q=&developmentsSize=5&__vt=&page=' + str(iPage)


    def getDefaultHeaders(self):
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
            "origin": "https://www.vivareal.com.br",
            "referer": 'https://www.vivareal.com.br/aluguel/minas-gerais/belo-horizonte/apartamento_residencial/',
            # "sec-fetch-dest": "empty",
            # "sec-fetch-mode": "cors",
            # "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36",
            "x-domain": "www.vivareal.com.br"
        }

    def start_requests(self):
        from selenium import webdriver
        driver = webdriver.Firefox()
        driver.get(self.startUrl)
        time.sleep(10)
        # cookies = driver.get_cookies()
        startResp = requests.get(self.startUrl, headers=self.getDefaultHeaders())
        totalImoveis = int(
            #startResp.text
            driver.page_source
                .split('class="results-summary__count js-total-records">')[
                1].split("</strong>")[0].replace(",", "").replace(".", ""))
        logging.warning("Total de Imoveis: " + str(totalImoveis))
        driver.close()
        driver.quit()
        logging.warning(startResp.cookies)
        for pageInd in range(int(math.floor(totalImoveis / self.pageSize))):
            yield scrapy.Request(url=self.getPageUrl(pageInd + 1), callback=self.parse,
                                 headers=self.getPageHeader(pageInd + 1))  # , cookies=startResp.cookies.get_dict())


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

    def getData(self, item):
        updatedAt = ''
        if "updatedAt" in item["listing"]:
            updatedAt = item["listing"]['updatedAt']
        createdAt = ''
        if "createdAt" in item["listing"]:
            createdAt = item["listing"]['createdAt']

        return updatedAt or createdAt

    def getIptu(self, item):
        iptus = [price["yearlyIptu"] for price in item["listing"]["pricingInfos"] if price["businessType"] == "RENTAL" and "yearlyIptu" in price]
        if len(iptus) > 0:
            return iptus[0]
        else:
            return 0

    def getCondoFee(self, item):
        prices = [price["monthlyCondoFee"] for price in item["listing"]["pricingInfos"] if price["businessType"] == "RENTAL" and "monthlyCondoFee" in price]
        if len(prices) > 0:
            return int(prices[0])
        else:
            return 0

    def getLogradouro(self, item):
        addrs = ""
        if "street" in item["listing"]["address"]:
            addrs = addrs + item["listing"]["address"]["street"]
        else:
            addrs = addrs + item["listing"]["address"]["name"]
        return addrs + ", bairro: " + item["listing"]["address"]["complement"] + ", bairro: " + item["listing"]["address"]["neighborhood"] + ", CEP: " + item["listing"]["address"]["zipCode"]

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
                'url': "www.vivareal.com.br/" + item["link"]["href"],
                'video': self.getVideoItem(item),
                'thumb': self.getThumbItem(item),
                '360': "",
                'data': self.getData(item),
                'bairro': item["listing"]["address"]["neighborhood"],
                'venda': 0,
                'aluguel': int([price["price"] for price in item["listing"]["pricingInfos"] if price["businessType"] == "RENTAL"][0]),
                'condominio': self.getCondoFee(item),
                'iptu': self.getIptu(item),
                'iptu_parcelas': 12,
                'vagas': sum(item["listing"]["parkingSpaces"]),
                'quartos': sum(item["listing"]["suites"]) + sum(item["listing"]["bedrooms"]),
                'banheiros': sum(item["listing"]["bathrooms"]),
                'area': sum([float(area) for area in item["listing"]["usableAreas"]]),
                'logradouro': self.getLogradouro(item),
                'descricao': item["listing"]["description"],

                'full': json.dumps(item)
            }