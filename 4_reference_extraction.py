'''
This script automatically adds reference data to CSV files using the paper's PDF file. 
The reference key from within the CSV file is matched against the extracted PDF reference,
in case no extact matches are found, some heuristics are applied to look for other 
references that could be correct (using automatic reference key generation etc.)
'''

import requests
from habanero import Crossref
import json
import pandas as pd 
from tei_reader import TeiReader
from lxml import etree
import string
import argparse
import requests
from termcolor import colored
import dateutil.parser
import os.path
import re
import editdistance
import settings

GROBID_API = os.getenv('GROBID_API')
vocab = dict()
cr = Crossref()

# Stats for counting the results 
stats = {
    'papers': 0,
    'foundReferences': 0,
    'notFoundReferences': 0,
    'cellsNoReferences': 0,
    'cellsWithReferences': 0
}

def main():
    # Check if there is a data directory param, otherwise use the default './data' directory 
    parser = argparse.ArgumentParser(description='Reference extractor')
    parser.add_argument("--dir", default=None)
    args = parser.parse_args()
    data_dir = args.dir
    data_dir = './data/' if not data_dir else data_dir
    directory = os.fsencode(data_dir)


    # Loop through each CSV file in the data directory
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith('.csv'): 
            tableId = filename.replace('.csv', '')
            paperId = tableId.split('.')[0]
            #tableId = '.' + str(tableId)
            paperFileName = str(paperId) + '.pdf'
            
            # Only continue if a PDF version of the paper is present
            if os.path.exists(data_dir + paperFileName):
                # In case the PDF hasn't been parsed by GROBID already, do that now
                if not os.path.exists(data_dir + 'parsedPaper-' + str(paperId) + '.xml'):
                    print('Parsing full paper with GROBID...')
                    url = GROBID_API + '/processFulltextDocument'
                    files = {
                        'input': open(data_dir + paperFileName, 'rb'), 
                        'includeRawCitations': 1, 
                        'consolidateCitations': 1 
                    }
                
                    # Save to a file for the parsed PDF XML can be used later 
                    r = requests.post(url, files=files)
                    referencesFile = open(data_dir + 'parsedPaper-' + str(paperId) + '.xml', 'w')
                    referencesFile.write(r.text)
                    referencesFile.close()
                
                # Open the PDF parsing results and load the tree
                tree = etree.parse(data_dir + 'parsedPaper-' + str(paperId) + '.xml') 
                references = loadReferences(tree)

                print(colored('Select table: ' + filename, 'yellow'))

                df = pd.read_csv(data_dir + filename) 
                papers = df.iloc

                # Lists for metadata that will be collected
                titles = []
                authors = []
                publicationMonths = []
                publicationYears = []
                dois = []
                referenceRaws = []

                # Loop through all rows in the CSV file (each row is a paper)
                for paper in papers:
                    # Get the bibliographical metadata for each paper
                    result = processPaper(paper, references, paperId)

                    titles.append(result['title'])
                    authors.append(result['author'])
                    publicationMonths.append(result['publicationMonth'])
                    publicationYears.append(result['publicationYear'])
                    dois.append(result['doi'])
                    referenceRaws.append(result['referenceRaw'])
                
                # Add the fetched metadata to the dataframe
                if len(titles) > 0:
                    df['title'] = titles
                    df['authors'] = authors
                    df['publicationMonth'] = publicationMonths
                    df['publicationYear'] = publicationYears
                    df['doi'] = dois
                    df['referenceRaw'] = referenceRaws
                
                # Count the stats for the references
                localCount = 0
                localCountRefs = 0
                for value in df.count(axis='columns'):
                    localCount += value - 7 # Remove the bibliographical metadata, 6 columns plus the reference key itself
                    localCountRefs += value - 1

                stats['cellsNoReferences'] += localCount
                stats['cellsWithReferences'] += localCountRefs
                
                # Save the new metadata 
                df.to_csv(data_dir + filename, index=False)
    
    print('Found paper:', str(stats['papers']))
    print('Found references:', str(stats['foundReferences']))
    print('Not found references:', str(stats['notFoundReferences']))
    print('Total imported cells: ', str(stats['cellsNoReferences']))
    print('Total imported cells with references: ', str(stats['cellsWithReferences']))

def processPaper(paper, references, paperId):
    stats['papers'] += 1
    insertPaper = {}
    title = ''
    author = ''
    publicationMonth = ''
    publicationYear = ''
    doi = ''
    referenceRaw = ''
    
    # If a column with a reference exists
    if 'Reference' in paper: 
        paper['Reference'] = cleanReferenceKey(paper['Reference'])
        
        # If numeric citation key, cast to int
        if str(paper['Reference']).isdigit():
            paper['Reference'] = int(paper['Reference'])

        referenceKey = paper['Reference']
        
        # If the reference key is not numeric (so author name reference), and the year is not present, and a year column exists => append year to key
        if not bool(re.search(r'\d', str(referenceKey))):
            if 'Year' in paper:
                year = paper['Year']

                if year == year and isinstance(year , float):
                    year = int(year)

                referenceKey = str(referenceKey) + str(year)

        '''
        # Editdistance for reference keys has been disabled because there were too many reference keys that only 
        # differ one letter and are not the same
        # If the citation key is not found, and not numeric key, use the edit distance to find keys that are similar  
        if referenceKey not in references and not str(paper['Reference']).isdigit():
            for reference in references:
                distance = editdistance.eval(str(referenceKey), str(reference))
                
                if distance != 0 and distance <= 2:
                    referenceKey = reference
        '''

       # If a matching key has been found 
        if referenceKey in references:
            title = references[referenceKey]['title']
            author = references[referenceKey]['authors']

            if len(author) > 0:
                author = ",".join(author)
            else:
                author = ''

            publicationMonth = references[referenceKey]['publicationMonth']
            publicationYear = references[referenceKey]['publicationYear']
            doi = references[referenceKey]['doi']
            referenceRaw = references[referenceKey]['referenceRaw']
        
            stats['foundReferences'] += 1
        # No matching key has been found, but there is a referenceRaw column present
        elif 'referenceRaw' in paper and paper['referenceRaw'] != '' and paper['referenceRaw'] != 'none' and paper['referenceRaw'] == paper['referenceRaw']:
            # When the bibliographical data doesn't exist yet
            if 'title' not in paper or str(paper['title']) == '' or paper['title'] != paper['title']:
                print('Parsing missing references using GROBID...')
                url = GROBID_API + '/processCitation'
                files = {'citations': paper['referenceRaw'], 'consolidateCitations': 1}
                
                r = requests.post(url, data=files)

                parsedRef = loadReferenceFromString(r.text)

                title = parsedRef['title']
                author = parsedRef['authors']

                if len(author) > 0:
                    author = ",".join(author)
                else:
                    author = ''

                doi = parsedRef['doi']
                publicationMonth = parsedRef['publicationMonth']
                publicationYear = parsedRef['publicationYear']
                referenceRaw = paper['referenceRaw']
                stats['notFoundReferences'] += 1
            # Metadata already exists, make sure to use it 
            else:
                stats['notFoundReferences'] += 1
                title = paper['title']
                doi = paper['doi']
                publicationMonth = paper['publicationMonth']
                publicationYear = paper['publicationYear']
                author = paper['authors']
                referenceRaw = paper['referenceRaw']
        # No reference and no raw reference has been found, ask user to manually supply it  
        elif paper['referenceRaw'] != 'none':
            print(colored('Reference ' + str(referenceKey) + ' not found (Paper: ' + str(paperId) + '.pdf), please add manually the raw reference...', 'yellow'))
            stats['notFoundReferences'] += 1

            # Get multiple input lines 
            inputRawReference = []
            while True:
                line = input()
                if line:
                    inputRawReference.append(line)
                else:
                    break

            inputRawReference = ' '.join(inputRawReference)

            if inputRawReference != '':
                print('Saved!')
                referenceRaw = inputRawReference
        else:
            referenceRaw = paper['referenceRaw']
    else:
        print(colored('Error: Column Reference not found!', 'red'))

    return {
        'title': title,
        'author': author,
        'publicationMonth': publicationMonth,
        'publicationYear': publicationYear,
        'doi':doi,
        'referenceRaw': referenceRaw
    }

# Build a dict for connecting a internal reference ID with the actual reference number used in the paper
# Do this by finding <ref type="bibr" target="#INTERNAL_ID">ACTUAL_CITATION_NUMBER</ref> from the parsed PDF
def internalIdToCitation(tree):
    
    citationDict = {}

    refs = list(tree.findall(".//{http://www.tei-c.org/ns/1.0}ref[@type=\"bibr\"][@target]"))
    for ref in refs:
        citationKey = ref.text.replace(',', '').replace('[', '').replace(']', '').replace('(','').replace(')', '')
        internalId = ref.attrib['target'].replace('#b', '')
        
        if citationKey.isnumeric() and internalId.isnumeric(): 
            citationDict[int(internalId)] = int(citationKey)
        elif internalId.isnumeric():
            citationDict[int(internalId)] = cleanReferenceKey(citationKey)            

    return citationDict

# Key a key for improved matching (remove special characters, spaces etc.)
def cleanReferenceKey(key):
    # try/catch to prevent any string operation on a (numpy)int key
    try: 
        if key != -1:
            return re.sub('[^0-9a-zA-Z]+', '', key).lower() # make comparing string citations keys more reliable 
    except TypeError:
        return key

# Load the references from a parsed PDF 
def loadReferences(tree):

    citationNumbers = internalIdToCitation(tree)

    # get the reference for a specific internal reference ID (in the form of bXXX)
    references = {}
    
    tree = removeNameSpaceFromTree(tree)
    
    links = list(tree.findall(".//biblStruct[@{http://www.w3.org/XML/1998/namespace}id]"))

    for i in links:
        internalId = int(i.attrib['{http://www.w3.org/XML/1998/namespace}id'].replace('b', ''))
        parsedRef = parseSingleRef(i)

        if internalId in citationNumbers:
            citationKey = citationNumbers[internalId]
        else:
            citationKey = cleanReferenceKey(parsedRef['lastNameFirstAuthor'] + str(parsedRef['publicationYear'])) # generate key manually 

        title = ''
        doi = ''
        paperAuthors = []
        publicationMonth = ''
        publicationYear = ''
        referenceRaw = ''

        references[citationKey] = {
            'title': parsedRef['title'],
            'doi': parsedRef['doi'],
            'authors': parsedRef['authors'],
            'publicationMonth': parsedRef['publicationMonth'], 
            'publicationYear': parsedRef['publicationYear'],
            'referenceRaw': parsedRef['referenceRaw'],
        }

    return references

# Remove namespaces from tree for easier matching 
def removeNameSpaceFromTree(tree):

    for elem in tree.getiterator():
        elem.tag = etree.QName(elem).localname
    # Remove unused namespace declarations
    etree.cleanup_namespaces(tree)

    return tree

def loadReferenceFromString(tree):
    tree = etree.fromstring(tree)
    tree = removeNameSpaceFromTree(tree)
    links = list(tree)
    ref = parseSingleRef(links)

    return ref

def parseSingleRef(i):
    title = ''
    doi = ''
    paperAuthors = []
    publicationMonth = ''
    publicationYear = ''
    referenceRaw = ''
    lastNameFirstAuthor = ''

    for element in i:
        if (element.tag == 'monogr'): 

            # In case there is no title found for the article, use the monogr title (sometimes it is parsed as monogr, but it should be analytic)
            if title == '':
                title = parseTitle(element)

            if doi == '':
                doi = parseDoi(element)
            
            if lastNameFirstAuthor == '':
                lastNameFirstAuthor = parseFirstAuthor(element)

            if len(paperAuthors) == 0:
                paperAuthors = parseAuthors(element)

            # Parse date
            dateElement = element.find('imprint//date')
            if (dateElement is not None and 'when' in dateElement.attrib):
                # Don't use dateutil since the year and month should be undefined when they are unknown
                parsedDate = dateElement.attrib['when'].split('-')
                if len(parsedDate) > 0:
                    publicationYear = int(parsedDate[0])
                if len(parsedDate) > 1:
                    publicationMonth = int(parsedDate[1])

        if (element.tag == 'analytic'): 
            title = parseTitle(element)
            doi = parseDoi(element)
            paperAuthors = parseAuthors(element)
            lastNameFirstAuthor = parseFirstAuthor(element)
        
        if (element.tag) == 'note':
            if 'type' in element.attrib and  element.attrib['type'] == 'raw_reference':
                referenceRaw = element.text
            
    return {
        'title': title,
        'doi': doi,
        'authors': paperAuthors,
        'publicationMonth': publicationMonth, 
        'publicationYear': publicationYear,
        'referenceRaw': referenceRaw,
        'lastNameFirstAuthor': lastNameFirstAuthor
    }

def parseTitle(element):
    title = ''

    if (element.find('title') is not None):
        title = element.find('title').text

    return title

def parseRawReference(element):
    reference = ''
    if (element.find('note') is not None):
        reference = element.find('note').text
    return reference

def parseDoi(element):
    doi = ''

    if (element.find('idno[@type="DOI"]') is not None):
        doi = element.find('idno[@type="DOI"]').text

    return doi

# Generate a list of author names from the tree
def parseAuthors(element):
    authors = element.findall('author/persName')
    paperAuthors = []

    for author in authors:
        firstName = ''
        middleName = ''
        lastName = ''

        findFirstName = author.find('forename[@type="first"]')

        if (findFirstName is not None): 
            firstName = findFirstName.text + ' '

        findMiddleName = author.find('forename[@type="middle"]')

        if (findMiddleName is not None): 
            middleName = findMiddleName.text + ' '

        findLastName = author.find('surname')

        if (findLastName is not None): 
            lastName = findLastName.text

        paperAuthors.append(firstName + middleName + lastName)
    
    return paperAuthors

# For automatic key generation, get the last name of the first author and 
# optionally add _et al._ in case there are multiple authors
def parseFirstAuthor(element):
    authors = element.findall('author/persName')

    firstName = ''
    if (len(authors) > 0):
        findFirstName = authors[0].find('surname')

        if (findFirstName is not None): 
            firstName = findFirstName.text

    if (len(authors) == 2):
        findFirstNameSecondAuthor = authors[1].find('surname')

        if (findFirstNameSecondAuthor is not None): 
            nameSecondAuthor = findFirstNameSecondAuthor.text

            firstName = str(firstName) + 'and' + str(nameSecondAuthor)

    if (len(authors) > 2):
        firstName = str(firstName) + 'et al.'

    return str(firstName)

if __name__ == "__main__":
    main()
