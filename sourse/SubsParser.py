from chardet.universaldetector import UniversalDetector
import re, math
from os import listdir
from os.path import isdir, join
from rutermextract import TermExtractor
from statistics import median

class SubsReader:
    def __init__(self, filePath):
        self.listOfTexts = None
        self.listOfTexts = self.__readFiles__(filePath)

    def __fileEncoding__(self, filename):
        detector = UniversalDetector()
        with open(filename, 'rb') as fh:
            for line in fh:
                detector.feed(line)
                if detector.done:
                    break
        detector.close()
        return detector.result['encoding']

    def __fileInLineReader__(self, filename):
        file = open(filename, encoding=self.__fileEncoding__(filename))
        allLines = ''
        for line in file:
            clearLine = re.sub('<i>|</i>|\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+|\n+|\r+|^\d+', '', line)
            if clearLine:
                allLines += ' ' + clearLine.replace('{\\an8}', '')
        return allLines

    def __readFiles__(self, wayToDir):
        listOfTexts = []
        files = listdir(wayToDir)
        for file in files:
            if isdir(join(wayToDir,file)):
                listOfTexts.extend(self.__readFiles__(join(wayToDir, file)))
            elif file.endswith('.srt'):
                data = self.__fileInLineReader__(join(wayToDir,file))
                listOfTexts.append(data)
                #listOfTexts.append([])
        return listOfTexts

class SubsParser(SubsReader):
    def __init__(self, listOrPath):
        if not isinstance(listOrPath, list):
            SubsReader.__init__(self, listOrPath)
        else:
            self.listOfTexts = listOrPath
        self.__tf = None
        self.__idf = None
        self.__simpliFrequency = None

    def __tf__(self, text):
        wordDic = {}
        termsQuantity = 0
        term_extractor = TermExtractor()
        for term in term_extractor(text, nested = 'true'):
            termsQuantity += term.count
        for term in term_extractor(text, nested = 'true', weight=lambda term: term.count / termsQuantity):
            wordDic[term.normalized] = term.count / termsQuantity
        return wordDic

    def __tfAll__(self, listOfTexts):
        listOfTf = []
        for text in listOfTexts:
            listOfTf.append(self.__tf__(text))
        return listOfTf


    def __idf__(self, textsList):
        korpDic = {}
        for text in textsList:
            term_extractor = TermExtractor()
            for term in term_extractor(text, nested = 'true'):
                if term.normalized in korpDic:
                    korpDic[term.normalized] = korpDic[term.normalized] + 1
                else:
                    korpDic[term.normalized] = 1
        for key in korpDic:
            korpDic[key] = math.log2(len(textsList) / korpDic[key])
        return korpDic

    def __simpliFrequency__(self, textsList):
        korpDic = {}
        for text in textsList:
            term_extractor = TermExtractor()
            for term in term_extractor(text, nested = 'true'):
                if term.normalized in korpDic:
                    korpDic[term.normalized] = korpDic[term.normalized] + term.count
                else:
                    korpDic[term.normalized] = 1
        for key in korpDic:
            korpDic[key] = korpDic[key] / len(textsList)
        return korpDic


    @property
    def tf(self):
        if self.__tf is None:
            self.__tf = self.__tfAll__(self.listOfTexts)
        return self.__tf

    @property
    def idf(self):
        if self.__idf is None:
            self.__idf = self.__idf__(self.listOfTexts)
        return self.__idf

    @property
    def simpliFrequency(self):
        if self.__simpliFrequency is None:
            self.__simpliFrequency = self.__simpliFrequency__(self.listOfTexts)
        return self.__simpliFrequency

class ExtendedParser:
    def __init__(self, contrast, parser):
        self.__parser1 = contrast
        self.__parser2 = parser
        self.__selfTfIdf = None
        self.__smartTfIdf = None

    def __tfIdf__(self, contrastDic, corpus):
        newTextDic = {}
        for val in corpus:
            newTextDic[val] = corpus[val] * contrastDic[val]
        return newTextDic

    def __forAllTextIter__(self, contrastDic, text):
        allTfIdf = []
        for it in text:
            allTfIdf.append(self.__tfIdf__(contrastDic, it))
        return allTfIdf

    def __smartTfIdf__(self, tf_idf):
        smartDict = {}
        for d in tf_idf:
            for it in d:
                if it not in smartDict:
                    smartDict[it] = [d[it]]
                else:
                    smartDict[it].append(d[it])
        for it in smartDict:
            smartDict[it] = median(smartDict[it])
        return smartDict

    @property
    def tf_idf(self):
        if self.__selfTfIdf is None:
            self.__selfTfIdf = self.__forAllTextIter__(self.__parser1.idf, self.__parser2.tf)
        return self.__selfTfIdf

    @property
    def smartTfIdf(self):
        if self.__smartTfIdf is None:
            self.__smartTfIdf = self.__smartTfIdf__(self.tf_idf)
        return self.__smartTfIdf

class ParsersCompranator:
    def __init__(self, parser1, parser2, N=None):
        self.__parser1 = parser1
        self.__parser2 = parser2
        self.__N = N
        self.__persentage = None
        self.__comprarableCoff = None

    def __compreraDict__(self, dic1, dic2, __N):
        simularCof = 0
        isSim = 0
        simpleFr1 = self.__sortDict__(dic1, __N)
        simpleFr2 = self.__sortDict__(dic2, __N) #здесь доделать
        for val in simpleFr1:
            if val in simpleFr2:
                isSim += 1
                simularCof += math.fabs(simpleFr1[val] - simpleFr2[val])
        if len(simpleFr1) <= len(simpleFr2):
            return ((isSim / len(simpleFr2) * 100), simularCof / len(simpleFr2))
        else:
            return ((isSim / len(simpleFr1) * 100), simularCof / len(simpleFr1))

    def __sortDict__(self, myDict, lenDict):
        sortDict = {}
        if lenDict is not None:
            sortDict.update(dict(sorted(myDict.items(), key=lambda x: x[1], reverse=True)[:lenDict]))
        else:
            sortDict.update(dict(sorted(myDict.items(), key=lambda x: x[1], reverse=True)))
        return sortDict

    @property
    def persantage(self):
        if self.__persentage is None:
            results = self.__compreraDict__(self.__parser1.simpliFrequency, self.__parser2.simpliFrequency, self.__N)
            self.__persentage, self.__comprarableCoff = results[0], results[1]
        return self.__persentage

    @property
    def comprarableCoff(self):
        if self.__comprarableCoff is None:
            results = self.__compreraDict__(self.__parser1.simpliFrequency, self.__parser2.simpliFrequency, self.__N)
            self.__persentage, self.__comprarableCoff = results[0], results[1]
        return self.__comprarableCoff

class ExstendedParserCompranator(ParsersCompranator):
    def __init__(self, contrast, parser1, parser2, N=None):
        ParsersCompranator.__init__(self, parser1, parser2, N)
        self.__N = N
        self.__exPars1 = ExtendedParser(contrast, parser1)
        self.__exPars2 = ExtendedParser(contrast, parser2)
        self.__advansePersantage = None
        self.__advanseCompreraCoff = None
        self.resalts = None

    @property
    def advansePersantage(self):
        if self.resalts is None:
            self.results = ParsersCompranator.__compreraDict__(self, self.__exPars1.smartTfIdf, self.__exPars2.smartTfIdf, self.__N)
            self.__advansePersantage, self.__advanseCompreraCoff = self.results[0], self.results[1]
        return self.__advansePersantage

    @property
    def advanseCompreraCoff(self):
        if self.resalts is None:
            self.results = ParsersCompranator.__compreraDict__(self, self.__exPars1.smartTfIdf, self.__exPars2.smartTfIdf, self.__N)
            self.__advansePersantage, self.__advanseCompreraCoff = self.results[0], self.results[1]
        return self.__advanseCompreraCoff