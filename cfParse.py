#!/usr/bin/python3
# -*- coding: latin-1 -*-
import sys
import os
import requests
import codecs
from lxml import html
from PyPDF2 import PdfFileReader
import re
from fuzzywuzzy import fuzz #phonetische string suche
from lxml.html import HTMLParser


signaturePatterns = [
    r"([UVYXW][\d] *[0-9]{3}(?:[a-g](?:.{0,1}[a-g])?)?)",
    r"([UVYXW] {0,4}[\d]? *(?:(?:[0-9]{1,4})|(?:[0-9]{1,2} */ *[0-9]{1,2}))(?: *[a-g](?:.{0,1}[a-g])?)?)",
    ]

autorPatterns = [
    r"([\w]{2,20}, {0,5}[\w]{2,20})",
    r"([\w]{2,20}, {0,5}[\w]{2,20})"
    ]

datePatternLine = r"([a-zA-z���,]{3,20} {0,3}: {0,3}[a-zA-z���]{3,10}.{0,5}(19[\d]{2})|(20[\d]{2}))"    


crapPattern = r"([a-d]=[\d]{2}/.{1,4})"

s=requests.session()
requestErrors=0
xmlErrors=0

cardCount=0
signaturesFound=0

def getDataOnline(autor,title):
    html_parser = HTMLParser(recover=True)
   
    
    try:
        page = s.get('http://katalogix.uni-muenster.de/Katalog/start.do')
        
    except:
        global requestErrors
        requestErrors+=1
        print("request errors")
        print(requestErrors)
        return [],"",0
    
    try:
        tree = html.fromstring(page.text,parser=html_parser) 
        
    except Exception as e:
        print(e)
        global xmlErrors
        xmlErrors+=1
        print("xml parse errors:")
        print(xmlErrors)
        return [],"",0
        
    

    CSId = tree.xpath('//input[@name="CSId"]/@value')
    #print(autor)
    #print(title)
    

    payload = {'methodToCall':'submit',
               'CSId':CSId,
               'methodToCallParameter':'submitSearch',
               'searchCategories[0]':'331',
               'searchString[0]':title,
               'combinationOperator[1]':'AND',
               'searchCategories[1]':'100',
               'searchString[1]':autor,
               'combinationOperator[2]':'AND',
               'searchCategories[2]':'902',
               'searchString[2]':'',
               'submitSearch':'Suchen',
               'callingPage':'searchParameters',
               'selectedViewBranchlib':'0',
               'searchBranchlibAutocomplete':'',
               'selectedSearchBranchlib':'',
               'searchRestrictionID[0]':'3',
               'searchRestrictionValue1[0]':'',
               'searchRestrictionID[1]':'2',
               'searchRestrictionValue1[1]':'',
               'searchRestrictionValue2[1]':'',
               'searchRestrictionID[2]':'1',
               'searchRestrictionValue1[2]':''}


    page = s.get('http://katalogix.uni-muenster.de/Katalog/search.do',params=payload)
    tree = html.fromstring(page.text,parser=html_parser)

    #anzahl der Treffer ermitteln
    hitCount = int(tree.xpath('count(//div[@id="hitlist"]/div/table/tr)'))
    

    
    title = tree.xpath('//td[@class="teaser-info"]/strong[1]/text()')

    signatures = tree.xpath('//div[@id="tab-content"]/table[@class="data"]/tr/td[2]/text()')

    #zeilenumbr�che l�schen
    signatures = list(map(lambda result : result.strip(), signatures))

        

    if(hitCount == 0 and len(signatures) > 0):
        hitCount = 1

    
    #zweites und drittes ergebnis ist leer
    return signatures[::3], title, hitCount


if __name__ == '__main__':
   

    #alle pdf dateien im aktuellen verzeichnis finden
    pdfFiles = []
    for file in os.listdir("."):
        if(file.endswith(".pdf")):
            pdfFiles.append(file) 

    pdfCount = len(pdfFiles)
    print("{0} Pdf Datei(en) gefunden:".format(pdfCount))
    for pdfFile in pdfFiles:
        print(pdfFile)
    

    

    pdfFileNum = 1
    for pdfFile in pdfFiles:
        
        csvFileName = pdfFile.split('.')[0] + ".csv"
        
        csvFile = codecs.open(csvFileName,"w+",encoding='utf-8')
        cardFileText = []
        pdfInput = PdfFileReader(pdfFile,"rb")
        
        numPages = pdfInput.getNumPages()
        #pdf seiten in text umwandlen
        for pageNum in range(0,numPages):
            #semikolons entfernen - wegen csv
            pageText = pdfInput.getPage(pageNum).extractText().replace(";","")
            pageText = pageText.replace("\"","")
            pageText = pageText.replace("'","")
            cardFileText.append(pageText)
        
        
        #cardFileText = [card for card in cardFileText if len(card) > 0]


        
        pageNum = 1


        for card in cardFileText:
            cardCount+=1
            signature = ''
            dateLine = ''
            autors = []
            print(pdfFile +"({0}/{1})".format(pdfFileNum,pdfCount) + " - Seite {0}/{1}".format(pageNum,numPages))

            crapData = re.findall(crapPattern,card)
            for crap in crapData:
                
                card = card.replace(crap,"")

            dateLineMatch = re.search(datePatternLine,card)
            if(dateLineMatch):
                dateLine = dateLineMatch.group(0).replace("\n","")
                card = card.replace(dateLine,"")
                
            for signaturePattern in signaturePatterns:
                signatureMatches = re.findall(signaturePattern,card.replace(" ",""))

                if(len(signatureMatches) > 0):
                    #nimm erste  gefunde  Signatur, da die normalerweise ganz oben steht
                    signature = signatureMatches[0]
                    signaturesFound+=1
                    card = card.replace(signature,"")
                    break
                
                
                
            for autorPattern in autorPatterns:
                autors = re.findall(autorPattern,card)[0:1]
                if(len(autors) > 0):
                    break


            for autor in autors:
                card = card.replace(autor,"")
                #print(autor)

            #Zeilenumbrueche aus Titeldaten entfernen
            content = card.replace("\n","")

            onlineSignatures = ''
            onlineTitle = ' '
            signatures = []

            #zahlen und sonderzeichen fuer die suche entfernen
            titlePhrases = re.findall(r'[\w]{3,30}',content)
            #titlePhrases = content.split(" ")
            if(len(autors)>0):

                for autor in autors:
                    #zuerst ohne titel probieren
                    signatures, title, hitCount = getDataOnline(autor,'')

                    
                    if(hitCount == 1):
                        #nur ein treffer -fertig
                        
                        onlineTitle = "".join(title)
                        print("online gefunden: " + onlineTitle + " " + onlineSignatures)
                        break
                        
                    elif(hitCount > 1):
                        #mehr als ein treffer mit autor alleine - suche mit titelwoertern
                        for phrase in titlePhrases:
                            signatures, title, hitCount = getDataOnline(autor,phrase)
                            if(hitCount == 1):
                                #nur ein treffer -fertig
                                
                                onlineTitle = ("".join(title))
                                print("online gefunden: " + onlineTitle + " " + onlineSignatures)
                                break
                        
                    if(len(onlineSignatures)>0):
                        break
                    

            #gefundenen titel mit titel von karteikarte vergleichen und score ermitteln
            titleMatchScore = fuzz.token_set_ratio(content, onlineTitle)
            
            
            onlineSignatures = (";".join(signatures))
            
            
            columns = [
                       signature,
                       ",".join(autors),
                       dateLine,
                       content,
                       onlineTitle,
                       str(titleMatchScore),
                       pdfFile,
                       str(pageNum),
                       onlineSignatures,
                       ]
            csvFile.write(";".join(columns) +  os.linesep)
            csvFile.flush()
            pageNum+=1
        pdfFileNum+=1
        csvFile.close()
        
    print("{0} % der Signaturen der Karteikarten erkannt".format((signaturesFound/cardCount)*100))
          
