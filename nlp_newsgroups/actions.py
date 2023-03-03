import re
from operator import itemgetter

import pandas as pd

class actions():

    def __init__(self):

        pass

    def set_status(self, message):

        # BUG: emit status message before callbacks complete
        self.status_message.text = message


    def recalculate_model(self, event):

        # message = "Recalculating Models! This may take a few minutes."
        # self.popup_alert(message)

        input_params = {key: val.value for key,val in self.model_inputs.items()}
        
        input_params['stop_words'] = self.model_params['stop_words']+[input_params['stop_words'].strip().lower()]

        change_params = [key for key,val in input_params.items() if val!= self.model_params[key]]
        change_params = [self.model_inputs[key].title for key in change_params]
        change_params = ', '.join(change_params)

        if change_params:

            # message = f"Recalculating model with new parameters for: {change_params}"
            # self.set_status(message)

            self.model_inputs['stop_words'].value = ""

            self.model_cache(input_params)


    def selected_reset(self, event):

        self.default_samples()
        self.default_selections()


    def default_samples(self):

        self.title['sample'].text ='Example Documents'
        self.sample_number.title = 'Document Sample #: make selection'
        self.sample_legend.text = ''
        self.sample_document.text = ''
        self.sample_number.value = 0
        self.sample_number.high = 1
        self.sample_text = None


    def default_selections(self, ignore=None):

        self.sample_number.value = 0

        reset = list(self.source.keys())
        if ignore is not None:
            reset.remove(ignore)

        for source in reset:
            self.source[source].selected.indices = []


    def set_samples(self, sample_title, text, important_terms):

        self.title['sample'].text = f'Example Documents:<br>{sample_title}'
        self.sample_legend.text = '<u>Legend:</u><br><strong>Imporant Terms</strong><br><s>Stop Words</s>'
        self.sample_number.title = f'Document Sample #: {len(text)} total'
        self.sample_number.high = len(text)-1
        self.sample_text = text
        self.sample_important_terms = important_terms

        self.selected_sample(None, None, self.sample_number.value)


    def selected_sample(self, attr, old, new):

        if self.sample_text is not None:

            text = self.sample_text.iloc[new]

            pattern = self.model_params['token_pattern']
            pattern = '[^'+pattern+']'
            tokens = re.sub(pattern, ' ', text)

            pattern = self.sample_important_terms
            pattern = pattern.str.replace(' ', r'\s+', regex=True)
            pattern = '|'.join(r'\b'+pattern+r'\b')
            important_terms = re.finditer(pattern, tokens, flags=re.IGNORECASE)

            pattern = pd.Series(self.model_params['stop_words'])
            pattern = pattern.str.replace(' ', r'\s+', regex=True)
            pattern = '|'.join(r'\b'+pattern+r'\b')
            stopword_terms = re.finditer(pattern, tokens, flags=re.IGNORECASE)

            text = list(text)
            for match in important_terms:
                idx_start = match.start()
                idx_end = match.end()-1
                text[idx_start] = f'<text="3"><strong>{text[idx_start]}'
                text[idx_end] = f'{text[idx_end]}</text></strong>'
            for match in stopword_terms:
                idx_start = match.start()
                idx_end = match.end()-1
                text[idx_start] = f'<s>{text[idx_start]}'
                text[idx_end] = f'{text[idx_end]}</s>'
            text = ''.join(text)

            self.sample_document.text = text


    def selected_ngram(self, attr, old, new):

        if len(new) == 0:
            self.default_samples()
            return
        
        self.default_selections(ignore='ngram')

        sample_title = self.figure['ngram'].title.text
        terms = self.source['ngram'].data['Terms'].iloc[new]

        document_idx = self.ngram['features'][:, terms.index].nonzero()[0]
        important_terms = terms

        text = self.data_input[document_idx]

        self.set_samples(sample_title, text, important_terms)


    def get_topic_prediction(self, event):

        self.default_selections()

        text = pd.Series([self.topic['predict']['input'].value])

        features = self.topic['vectorizer'].transform(text)

        distribution = self.assign_topic(self.topic['model'], features)

        self.topic['predict']['renderer'].data_source.data = distribution.to_dict(orient='list')

        # TODO: show distribution of term importance
        predicted_topic = distribution.loc[distribution['Confidence']>0, 'Topic']
        important_terms = self.topic['summary'].loc[
            (self.topic['summary']['Topic'].isin(predicted_topic)) & (self.topic['summary']['Weight']>0)
        ]
        self.set_samples('Topic Prediction', text, important_terms['Term'])


    def selected_topic(self, attr, old, new):

        if len(new) == 0:
            self.default_samples()
            return
        
        self.default_selections(ignore='topics')

        sample_title = self.figure['topics'].title.text

        topics_number = self.source['topics'].data['Topic'].iloc[new]

        # TODO: include confidence in a plot somehow
        topics = self.topic['Distribution'][
            (self.topic['Distribution']['Topic'].isin(topics_number)) & (self.topic['Distribution']['Rank']==1)
        ]

        # TODO: include weight in a plot somehow
        document_idx = topics.index
        important_terms = self.topic['summary'].loc[
            (self.topic['summary']['Topic'].isin(topics['Topic'])) & (self.topic['summary']['Weight']>0),
            'Term'
        ]

        text = self.data_input[document_idx]

        self.set_samples(sample_title, text, important_terms)