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
    comparisonIds = [
        'R25093',
        'R25115',
        'R25160',
        'R25201',
        'R25223',
        'R25255',
        'R25358',
        'R25400',
        'R25447',
        'R25495',
        'R25529',
        'R25583',
        'R25629',
        'R25663',
        'R25694',
        'R25726',
        'R25762',
        'R25768',
        'R25857',
        'R25900',
        'R25920',
        'R25931',
        'R25948',
        'R25961',
        'R25999',
        'R26017',
        'R26063',
        'R26083',
        'R26107',
        'R26127',
        'R26146',
        'R26194',
        'R26262',
        'R26352',
        'R26377',
        'R26421',
        'R26550',
        'R26608',
        'R26654',
        'R26729',
        'R26775',
        'R26850',
        'R26881',
        'R26918',
        'R26927',
        'R26982',
        'R27039',
        'R27061',
        'R27089',
        'R27123',
        'R27235',
        'R27264',
        'R27278',
        'R27380',
        'R27388',
        'R27393',
        'R27400',
        'R27403',
        'R27461',
        'R27482',
        'R27620',
        'R27705',
        'R27714',
        'R27723',
        'R27835',
        'R28099',
        'R28140',
        'R28191',
        'R28235',
        'R28333',
        'R28369',
        'R28407',
        'R28446',
        'R28487',
        'R28519',
        'R28614',
        'R28889',
        'R28897',
        'R28903',
        'R28940',
        'R28967',
        'R28981',
        'R29012',
        'R29034',
        'R29080',
        'R29108',
        'R29153',
        'R29184',
        'R29240',
        'R29275',
        'R29287',
        'R29351',
        'R29361',
        'R30476',
        'R30512',
        'R30536',
        'R30547',
        'R30579',
        'R30646',
        'R30698',
        'R30739',
        'R30817',
        'R30914',
        'R30950',
        'R31077',
        'R31090',
        'R31099',
        'R31160',
        'R31174',
        'R31214',
        'R31233',
        'R31249',
        'R31281',
        'R31299',
        'R31669',
        'R31689',
        'R31725',
        'R31768',
        'R31809',
        'R31878',
        'R31903',
        'R31928',
        'R31954',
        'R31991',
        'R32025',
        'R32061',
        'R32189',
        'R32424',
        'R32541',
        'R32871',
        'R32914',
        'R32940',
        'R32959',
        'R33008',
        'R33091',
        'R33581',
        'R33593',
        'R33610',
        'R33633',
        'R33783',
        'R33851',
        'R33953',
        'R33971',
        'R34099',
        'R34126',
        'R34183',
        'R34251',
        'R34282',
        'R34316',
        'R34411',
        'R34430',
        'R34454',
        'R34475',
        'R34493',
        'R34605',
        'R34621',
        'R34663',
        'R34706',
        'R34757',
        'R34845'
    ]

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
