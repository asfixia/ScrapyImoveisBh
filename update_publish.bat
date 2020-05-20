
cd F:\Danilo\Temp\imoveisBH\
git pull

cd %~dp0
rm %~dp0/netimoveis.json
rm %~dp0/vivareal.json
rm %~dp0/zapimoveis.json

call %~dp0/getNetImoveis.bat
call %~dp0/getVivaRealImoveis.bat
call %~dp0/getZapImoveis.bat
python %~dp0/publish_changes.py


cd F:\Danilo\Temp\imoveisBH\
git add *
git commit -m "Update de hoje"
git push
