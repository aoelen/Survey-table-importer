'''
This script takes the fully formatted CSV files and adds the papers from this file to the 
ORKG. The scripts handles creating the triples and distinguishes between resources/literals. 
Additionally, a comparison object is created, so each survey can be viewed directly from the ORKG 
user interface.
'''

import requests
from orkg import ORKG
from habanero import Crossref
import json
import pandas as pd 
from tei_reader import TeiReader
from lxml import etree
import string
import argparse
from termcolor import colored
import re
import os.path

ORKG_API = 'http://0313cbb4.ngrok.io'
orkg = ORKG(ORKG_API) #https://www.orkg.org/orkg
vocab = dict()
cr = Crossref()

def main():
    parser = argparse.ArgumentParser(description='Graph builder')
    parser.add_argument("--dir", default=None)
    parser.add_argument("--settings", default=None)
    args = parser.parse_args()
    data_dir = args.dir
    settingsFile = args.settings
    data_dir = './data/' if not data_dir else data_dir
    settingsFile = './tables.csv' if not settingsFile else settingsFile

    settings_df = pd.read_csv(settingsFile, dtype=str)
    tables = settings_df.iloc

    # For each table listed in the settings CSV
    for table in tables:
        table_id = table['tableID']
        table_file_name = str(table_id) + '.csv'

        # If a corresponding table CSV file exists
        if os.path.exists(data_dir + table_file_name):
            print('Loading CSV file...' + data_dir + table_file_name)

            research_field = 'R11'
            research_problem = table['problem']
            standard_statements = {}
            paper_ids = []

            df = pd.read_csv(data_dir + table_file_name, dtype=str) 
            papers = df.iloc

            # For each paper in the table CSV
            for paper in papers:
                insert_paper = {}
                #print('Inserting:' + str(paper['title']))

                if paper['title'] and paper['title'] != '' and paper['title'] == paper['title']:
                    insert_paper['paper'] = {}
                    insert_paper['paper']['title'] = paper['title']
                    insert_paper['paper']['authors'] = []
                    insert_paper['paper']['publicationYear'] = ''
                    insert_paper['paper']['publicationMonth'] = ''

                    if paper['authors'] == paper['authors']: # Exclude NaN values 
                        for author in paper['authors'].split(','):
                            insert_paper['paper']['authors'].append({"label": author})

                    if paper['publicationMonth'] == paper['publicationMonth']: # Exclude NaN values 
                        insert_paper['paper']['publicationMonth'] = paper['publicationMonth']
                    
                    if paper['publicationYear'] == paper['publicationYear']: # Exclude NaN values 
                        insert_paper['paper']['publicationYear'] = paper['publicationYear']

                    if paper['doi'] == paper['doi']:  # Exclude NaN values 
                        insert_paper['paper']['doi'] = paper['doi']
                    
                    # Delete the metadata from the triples that will be inserted (metadata is already added when adding a paper)
                    del paper['Reference']
                    del paper['title']
                    del paper['authors']
                    del paper['publicationMonth']
                    del paper['publicationYear']
                    del paper['doi']

                    if 'referenceRaw' in paper:
                        del paper['referenceRaw']

                    statements = {}

                    #print('Lookup predicates and resources...')

                    for item in paper.iteritems(): 
                        predicate = item[0].rstrip(string.digits) # Column, remove digits that are used to make columns unique by OpenRefine
                        value = item[1] # Cell

                        # If predicate starts with [R], insert it as resource instead of literal
                        if predicate.startswith('[R]'):
                            valueAsResource = True
                            predicate = predicate.strip('[R]')
                        else:
                            valueAsResource = False

                        if (value != value): # Don't insert NaN values
                            continue
                            
                        predicateId = createOrFindPredicate(predicate)
                        
                        # Choose between adding a literal v.s. a resource
                        if valueAsResource: 
                            # Resource 
                            resourceId = createOrFindResource(value)
                            if predicateId in statements: 
                                statements[predicateId].append({"@id": resourceId})
                            else:
                                statements[predicateId] = [
                                    {"@id": resourceId}
                                ]
                        else:
                            # Literal
                            if predicateId in statements: 
                                statements[predicateId].append({"text": value})
                            else:
                                statements[predicateId] = [
                                    {"text": value}
                                ]

                    # Check if in the standard statements predicate IDs are used, or just strings
                    # If there are only strings, it should be replace by the ID - and - insert the statements 
                    statementsToInsert = standard_statements.copy()

                    if len(statementsToInsert) > 0:
                        for predicate in statementsToInsert:
                            if isinstance(statementsToInsert[predicate], list): #if is array
                                for i in range(len(statementsToInsert[predicate])):
                                    if statementsToInsert[predicate][i]['values'] == 'CSV_PLACEHOLDER':
                                        statementsToInsert[predicate][i]['values'] = statements

                            if not re.search("^[P]+[a-zA-Z0-9]*$", predicate):                    
                                predicateId = createOrFindPredicate(predicate)
                                statementsToInsert[predicateId] = statementsToInsert[predicate]
                                del statementsToInsert[predicate]
                    else:
                        statementsToInsert = statements
                    
                    # Add the table data to the default statements
                
                    # Create first contribution 
                    insert_paper['paper']['researchField'] = research_field
                    insert_paper['paper']['contributions'] = [
                        {
                            "name": "Contribution 1",
                            "values": statementsToInsert
                        }
                    ]

                    # Add research problem to the first contribution 
                    if research_problem != '':
                        research_problemId = createOrFindResource(research_problem) # Replace with something that assigns a class to the problem
                        
                        insert_paper['paper']['contributions'][0]['values']['P32'] = [
                            {"@id": research_problemId}
                        ]

                    #print(json.dumps(insert_paper))
                    response1 = orkg.papers.add(insert_paper)

                    if ('id' in response1.content):
                        #print(response1.content['id'])
                        paper_ids.append(response1.content['id'])
                    else:
                        print(colored('Error, paper has not been added to ORKG', 'red'))
                else:
                    print(colored('Skipping paper without a title', 'yellow'))

            createComparison(table['title'], table['reference'], paper_ids)

            print('Finished: done inserting all papers')

# Create a comparison resource in ORKG, add the title, reference and the URL 
def createComparison(title, reference, paper_ids):
    comparisonId = orkg.resources.add(label=title, classes=['Comparison']).content['id']
    #descriptionId = orkg.literals.add(label=description).content['id']
    referenceId = orkg.literals.add(label=reference).content['id']
    paper_ids = ",".join(paper_ids)
    urlId = orkg.literals.add(label="?contributions=" + paper_ids).content['id']
    
    #orkg.statements.add(subject_id=comparisonId, predicate_id="description", object_id=descriptionId).content['id']
    orkg.statements.add(subject_id=comparisonId, predicate_id="url", object_id=urlId).content['id']
    orkg.statements.add(subject_id=comparisonId, predicate_id="reference", object_id=referenceId).content['id']

    print('comparisonId', comparisonId)

# Loopup resource by label, create if it doesn't exist
def createOrFindResource(label):
    findResource = orkg.resources.get(q=label, exact=True).content
    if (len(findResource) > 0):
        resource = findResource[0]['id']
    else:
        resource = orkg.resources.add(label=label).content['id']
    return resource

# Loopup predicate by label, create if it doesn't exist
def createOrFindPredicate(label):
    findPredicate = orkg.predicates.get(q=label, exact=True).content
    if (len(findPredicate) > 0):
        predicate = findPredicate[0]['id']
    else:
        predicate = orkg.predicates.add(label=label).content['id']
    return predicate

if __name__ == "__main__":
    main()
