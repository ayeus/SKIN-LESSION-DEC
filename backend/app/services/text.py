import re
import math
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report, silhouette_score

def tokens(s): return re.findall(r'\b\w+\b',s.lower())

def documents(df,p):
    col=p.get('text_column','text')
    if col not in df or df[col].isna().any(): raise ValueError('Map a nonmissing text column')
    docs=df[col].astype(str).map(lambda s:re.sub(r'\s+',' ',s).strip()).tolist()
    if len(docs)<3 or any(not x for x in docs): raise ValueError('At least three nonempty documents required')
    return docs

def analyze(df,p):
    docs=documents(df,p); task=p.get('task','cluster')
    if task in ('classify','disambiguate'):
        label=p.get('label_column','label')
        if label not in df or df[label].isna().any(): raise ValueError('Genuine nonmissing labels are required')
        y=df[label].astype(str)
        if y.nunique()<2 or y.value_counts().min()<2: raise ValueError('Each of at least two labels needs two or more examples')
        group=p.get('group_column')
        if group:
            if group not in df or df[group].isna().any(): raise ValueError('Valid patient/document group required')
            train,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(docs,y,df[group]))
        else:
            train,test=train_test_split(np.arange(len(docs)),test_size=.25,random_state=42,stratify=y)
        if set(y.iloc[train])!=set(y): raise ValueError('Training split lacks a class; provide more independent groups')
        model=make_pipeline(TfidfVectorizer(max_features=10000,ngram_range=(1,2)),LogisticRegression(max_iter=1000,random_state=42))
        model.fit([docs[i] for i in train],y.iloc[train]); pred=model.predict([docs[i] for i in test])
        contextual={}
        if task=='disambiguate':
            query=p.get('query','').strip()
            if not query: raise ValueError('Provide the ambiguous term within its actual clinical context as query')
            probabilities=model.predict_proba([query])[0]
            contextual={'sense_candidates':sorted([{'sense':str(label),'uncalibrated_score':float(score)} for label,score in zip(model[-1].classes_,probabilities)],key=lambda v:-v['uncalibrated_score']),
                'resolution':'Research ranking only; no certainty threshold is validated. Human review required.'}
        return {**contextual,'method':'TF-IDF + logistic regression','evaluation':classification_report(y.iloc[test],pred,output_dict=True,zero_division=0),
            'test_indices':test.tolist(),'predicted_labels':pred.tolist(),'train_rows':len(train),
            'limitation':'Held-out research baseline. Without patient grouping repeated-note leakage cannot be excluded.'}
    vectorizer=TfidfVectorizer(max_features=10000,ngram_range=(1,2)); x=vectorizer.fit_transform(docs)
    if task=='cluster':
        k=int(p.get('clusters',2))
        if not 2<=k<len(docs): raise ValueError('Cluster count must be between 2 and document count minus one')
        method=p.get('method','kmeans')
        if method=='hierarchical':
            if len(docs)>1000: raise ValueError('Hierarchical clustering limited to 1000 documents')
            labels=AgglomerativeClustering(n_clusters=k).fit_predict(x.toarray())
        elif method=='kmeans': labels=KMeans(n_clusters=k,random_state=42,n_init=10).fit_predict(x)
        else: raise ValueError('Choose kmeans or hierarchical')
        if len(set(labels))<2 or len(set(labels))>=len(docs): raise ValueError('Degenerate clusters; choose distinct documents or fewer clusters')
        terms=vectorizer.get_feature_names_out()
        top={str(c):terms[np.asarray(x[labels==c].mean(axis=0)).ravel().argsort()[-10:][::-1]].tolist() for c in set(labels)}
        return {'assignments':labels.tolist(),'top_terms':top,'silhouette_cosine':float(silhouette_score(x,labels,metric='cosine')),'limitation':'Clusters are exploratory document groups, not validated diagnoses.'}
    if task=='search':
        query=p.get('query','').strip()
        if not query: raise ValueError('Provide search query')
        algorithm=p.get('method','bm25')
        if algorithm=='tfidf': scores=(x@vectorizer.transform([query]).T).toarray().ravel()
        elif algorithm=='bm25':
            corpus=[tokens(s) for s in docs]; avg=np.mean([len(s) for s in corpus]); scores=np.zeros(len(docs))
            for term in set(tokens(query)):
                freq=sum(term in s for s in corpus); idf=math.log(1+(len(docs)-freq+.5)/(freq+.5))
                for i,doc in enumerate(corpus):
                    tf=Counter(doc)[term]; scores[i]+=idf*tf*2.5/(tf+1.5*(.25+.75*len(doc)/avg))
        else: raise ValueError('Choose bm25 or tfidf')
        ranking=[{'document_index':int(i),'score':float(scores[i]),'text':docs[i]} for i in np.argsort(-scores)[:20] if scores[i]>0]
        return {'method':algorithm,'results':ranking,'explanation':'Scores indicate lexical relevance, not clinical truth. BM25 uses k1=1.5, b=0.75.',
            'disambiguation':{'status':'unresolved','reason':'No context-labeled terminology model supplied. Ambiguous abbreviations remain unresolved.'}}
    if task=='ner': return clinical_entities(docs)
    raise ValueError('Unsupported text task')


def clinical_entities(docs):
    """Owner-provided local clinical model; model card and license required."""
    import os
    import json
    from pathlib import Path
    path=os.getenv('DERMA_NER_MODEL')
    if not path: raise ValueError('BLOCKED: supply a licensed clinical NER model and model card')
    root=Path(path)
    card=root/'research-model-card.json'
    if not card.is_file(): raise ValueError('Clinical model requires research-model-card.json')
    metadata=json.loads(card.read_text())
    if not all(metadata.get(k) for k in ('source','license','intended_use','limitations')): raise ValueError('Model card requires source, license, intended_use and limitations')
    import spacy
    nlp=spacy.load(root)
    if 'ner' not in nlp.pipe_names: raise ValueError('Configured pipeline has no NER component')
    results=[]
    for doc in nlp.pipe(docs,batch_size=16):
        entities=[]
        for ent in doc.ents:
            negation=getattr(ent._,'negex',None) if ent.has_extension('negex') else None
            entities.append({'text':ent.text,'start':ent.start_char,'end':ent.end_char,'label':ent.label_,
                'negated':negation,'uncertainty':'Not resolved unless validated by the supplied pipeline'})
        results.append({'text':doc.text,'entities':entities})
    return {'documents':results,'model_card':metadata,'limitation':'Entity recognition does not verify clinical facts. Negation is unknown unless provided by the configured model; no medical validation is inferred.'}
