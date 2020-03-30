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
import settings

orkg = settings.init_orkg() 
vocab = dict()
cr = Crossref()

def main():
    df = pd.DataFrame(columns=['URL', 'Paper title'])

    # List the IDs of the comparison from which papers should be collected 
    comparisonIds = []

    for comparisonId in comparisonIds:
        statements = orkg.statements.get_by_subject(subject_id=comparisonId).content
        for statement in statements:
                if statement['predicate']['id'] == 'url':
                    contributionIds = statement['object']['label'].replace('?contributions=', '').split(',')
                    for contributionId in contributionIds:
                        getPaper = orkg.statements.get_by_object(object_id=contributionId).content
                        df = df.append({'URL': 'https://www.orkg.org/orkg/paper/' + getPaper[0]['subject']['id'], 'Paper title': getPaper[0]['subject']['label']}, ignore_index=True)
                        print(getPaper[0]['subject']['label'] + ' https://www.orkg.org/orkg/paper/' + getPaper[0]['subject']['id'])

    df.to_csv('./ingested_papers.csv', index=False)

if __name__ == "__main__":
    main()
