# Instalazione su docker swarm

-----------------------------

copiare in locale la cartella con dockerfile

aprire docker desktop

lanciare cmd

posizionarsi nella cartella del repository locale
 
creare l'immagine:

docker image build -t registry.uni.com/tamara.quaranta/python/cen_iso_meetings:0.1 .      (il punto serve a dire che è nella cartella corrente)

docker image build -t registry.uni.com/diesys/xpod2/xpod2web:01 .
 
eseguire login al registry:

docker login registry.uni.com
 
eseguire il push verso il registry dell'immagine:

docker push registry.uni.com/tamara.quaranta/python/cen_iso_meetings:0.1

docker push registry.uni.com/diesys/xpod2/xpod2web:01
 
esecuzione del container:

docker run  registry.uni.com/tamara.quaranta/python/cen_iso_meetings:0.2 (latest)

docker run  registry.uni.com/tylconsulting/thothbe:01

 