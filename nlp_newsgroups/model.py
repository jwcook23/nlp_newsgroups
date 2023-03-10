from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import NMF, MiniBatchNMF, LatentDirichletAllocation
import pandas as pd
import numpy as np

from nlp_newsgroups import performance

class model():

    def __init__(self, token_pattern, max_df, min_df, stop_words, num_features, ngram_range, topic_num, topic_approach):

        self.model_params = {
            'token_pattern': token_pattern,
            'max_df': max_df,
            'min_df': min_df,
            'stop_words': stop_words,
            'num_features': num_features,
            'ngram_range': ngram_range,
            'topic_num': topic_num,
            'topic_approach': topic_approach
        }


    @performance.timing
    def get_ngram(self, text):

        self.ngram = {}

        self.ngram['vectorizer'] = CountVectorizer(
            max_df=self.model_params['max_df'], min_df=self.model_params['min_df'], max_features=self.model_params['num_features'], 
            stop_words=self.model_params['stop_words'].tolist(), ngram_range=self.model_params['ngram_range'],
            token_pattern=self.model_params['token_pattern']
        )

        self.ngram['features'] = self.ngram['vectorizer'].fit_transform(text)

        self.ngram['terms'] = pd.Series(self.ngram['vectorizer'].get_feature_names_out())

        self.ngram['summary'] = pd.DataFrame({
            'terms': self.ngram['terms'],
            'term_count': np.asarray(self.ngram['features'].sum(axis=0)).ravel(),
            'document_count': np.asarray((self.ngram['features']>0).sum(axis=0)).ravel()
        })
        self.ngram['summary'] = self.ngram['summary'].sort_values('term_count', ascending=False)


    def assign_topic(self, topic_model, features):

        distribution = topic_model.transform(features)
        distribution = pd.DataFrame.from_records(distribution, columns=self.topic['name'])
        distribution.index.name = 'Document'
        distribution = distribution.melt(var_name='Topic', value_name='Confidence', ignore_index=False)
        distribution = distribution.sort_values(by=['Topic', 'Confidence'], ascending=[True, False])
        rank = distribution.groupby('Document')['Confidence'].rank(ascending=False).astype('int64')
        distribution['Rank'] = rank

        return distribution


    @performance.timing
    def get_topics(self, text):

        self.topic = {}

        if self.model_params['topic_approach'] in ['Non-negative Matrix Factorization', 'MiniBatch Non-negative Matrix Factorization']:
            vectorizer = 'tfidf'
        else:
            vectorizer = 'tf'
        self.get_topic_vectorizer(text, vectorizer)


        if self.model_params['topic_approach'] == 'Non-negative Matrix Factorization':
            self.topic['model'] = NMF(
                n_components=self.model_params['topic_num'], random_state=1, init="nndsvda", beta_loss="frobenius",
                alpha_W=0.00005, alpha_H=0.00005, l1_ratio=1
            ).fit(self.topic['features'])

        elif self.model_params['topic_approach'] == 'MiniBatch Non-negative Matrix Factorization':
            self.topic['model'] = MiniBatchNMF(
                n_components=self.model_params['topic_num'], random_state=1, init="nndsvda", beta_loss="frobenius",
                alpha_W=0.00005, alpha_H=0.00005, l1_ratio=0.5, batch_size=128
            ).fit(self.topic['features'])

        elif self.model_params['topic_approach'] == 'Latent Dirichlet Allocation':
            self.topic['model'] = LatentDirichletAllocation(
                n_components=self.model_params['topic_num'], max_iter=5, learning_method="online",
                learning_offset=50.0, random_state=0,
            ).fit(self.topic['features'])

        self.topic['summary'] = pd.DataFrame()
        self.topic['name'] = []
        for topic_num, topic_weight in enumerate(self.topic['model'].components_):
            
            summary = pd.DataFrame({
                'Topic': [None]*self.model_params['num_features'],
                'Term': self.topic['terms'],
                'Weight': topic_weight
            })
            summary = summary.sort_values('Weight', ascending=False)
            summary['Rank'] = range(0,len(summary))
            name = f'Unnamed # {topic_num}'

            summary['Topic'] = name
            self.topic['name'] += [name]
            self.topic['summary'] = pd.concat([self.topic['summary'], summary])

        self.topic['Distribution'] = self.assign_topic(self.topic['model'], self.topic['features'])


    @performance.timing
    def get_topic_vectorizer(self, text, vectorizer):

        if vectorizer == 'tfidf':
            self.topic['vectorizer'] = TfidfVectorizer(
                max_df=self.model_params['max_df'], min_df=self.model_params['min_df'], max_features=self.model_params['num_features'], 
                stop_words=self.model_params['stop_words'].tolist(), token_pattern=self.model_params['token_pattern']
            )
        elif vectorizer == 'tf':
            self.topic['vectorizer'] = CountVectorizer(
                max_df=self.model_params['max_df'], min_df=self.model_params['min_df'], max_features=self.model_params['num_features'], 
                stop_words=self.model_params['stop_words'].tolist(), token_pattern=self.model_params['token_pattern']
            )    

        self.topic['features'] = self.topic['vectorizer'].fit_transform(text)

        self.topic['terms'] = pd.Series(self.topic['vectorizer'].get_feature_names_out())
        