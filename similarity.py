import spacy
import nltk
import pandas as pd
import numpy as np

#get the model from spacy
model = spacy.load('en_core_web_md')

def tokenise(text):
    tokens = nltk.word_tokenize(text.upper())
    return tokens

def get_keywords(tokens):
    
    tags = nltk.pos_tag(tokens)

    doc = []

    for word, tag in tags:
        if tag.startswith("N") or tag.startswith("RB") or tag.startswith("J") or tag.startswith("V") and not tag.endswith("Z"):
            doc.append(word)

    return doc

def get_similarity(text1, text2):

    #join each tokenised text to a single string 
    text1 = " ".join(text1)
    text2 = " ".join(text2)

    print (f"text1: {text1}\ntext2: {text2}")

    doc1 = model(text1)
    doc2 = model(text2)

    #vectorise each text
    vec1 = doc1.vector
    vec2 = doc2.vector

    #get the cosine similarity of the sentences
    dot_product = np.dot(vec1, vec2)

    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    return dot_product / (norm1 * norm2)

#for abstractness
def process(text1, text2):
    token1 = tokenise(text1)
    keyword1 = get_keywords(token1)

    token2 = tokenise(text2)
    keyword2 = get_keywords(token2)

    return get_similarity(keyword1, keyword2)

def keywords(text):
    tokens = tokenise(text)

    return get_keywords(tokens)

def profanity_check(text):
    profanity = pd.read_csv('bad-words.csv')
    profanity = np.array(profanity)

    words = keywords(text)

    for word in words:
        word = word.lower()
        if word in profanity:
            return False

    return True
