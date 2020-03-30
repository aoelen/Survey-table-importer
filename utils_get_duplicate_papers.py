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

vocab = dict()
cr = Crossref()

def main():
    data_dir = './data/' 
    directory = os.fsencode(data_dir)

    paper_titles = {}
    duplicates = {}

    # Make a dict with all files, paper titles and their respective reference keys
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith('.csv'): 
            df = pd.read_csv(data_dir + filename) 
            papers = df.iloc

            
            for paper in papers:
                if filename not in paper_titles:
                    paper_titles[filename] = {}

                if paper['title'] not in paper_titles[filename]:
                    paper_titles[filename][paper['title']] = []
                
                if paper['Reference'] not in paper_titles[filename][paper['title']]:
                    paper_titles[filename][paper['title']].append(paper['Reference'])
    
    # Count and print the files with duplicate paper titles but with different citation keys 
    duplicate = 0
    for csvFile in paper_titles:
        for paper in paper_titles[csvFile]:    
            if len(paper_titles[csvFile][paper]) > 1 and paper == paper:
                duplicates = len(paper_titles[csvFile][paper])
                print(str(duplicates) + ' : ' + csvFile +' : ' + str(paper))
   

if __name__ == "__main__":
    main()
