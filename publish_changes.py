import json

folder = "F:\\Danilo\\Programacao\\python\\ImoveisScrapy\\"
allObjs = []
for file in [folder + file for file in ["netimoveis.json", "vivareal.json", "zapimoveis.json"]]:
    with open(file, 'r') as jsonFile:
        allObjs = allObjs + json.load(jsonFile)

with open("F:\\Danilo\\Temp\\imoveisBH\\" + "all.json", 'w') as jsonResult:
    json.dump(allObjs, jsonResult)