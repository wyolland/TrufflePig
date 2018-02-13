import logging
import os

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.externals import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report
from sklearn.base import BaseEstimator

from gensim.models.lsimodel import LsiModel
from gensim import corpora
from gensim.matutils import corpus2dense


logger = logging.getLogger(__name__)


FEATURES = ['body_length', 'num_paragraphs', 'num_paragraphs',
            'num_words', 'unique_words', 'unique_ratio',
            'num_spelling_errors', 'chars_per_word', 'words_per_paragraph',
            'errors_per_word', 'average_sentence_length', 'sentence_length_variance']

TARGETS = ['reward', 'votes']

FILENAME_TEMPLATE = 'truffle_pipeline__{time}.gz'

class TopicModel(BaseEstimator):
    def __init__(self, no_below, no_above, num_topics):
        self.num_topics = num_topics
        self.no_below = no_below
        self.no_above = no_above
        self.lsi = None
        self.disctionary = None

    def to_corpus(self, tokens):
        return [self.dictionary.doc2bow(text) for text in tokens]

    def train(self, tokens):
        self.dictionary = corpora.Dictionary(tokens)
        self.dictionary.filter_extremes(self.no_below, self.no_above)
        corpus = self.to_corpus(tokens)
        self.lsi = LsiModel(corpus, num_topics=self.num_topics)

    def project(self, tokens):
        corpus = self.to_corpus(tokens)
        return self.lsi[corpus]

    def project_dense(self, tokens):
        projection = self.project(tokens)
        result = corpus2dense(projection, self.num_topics).T
        return result

    def fit(self, data, y=None):
        self.train(data.tokens)
        return self

    def transform(self, data):
        return self.project_dense(data.tokens)


class FeatureSelector(BaseEstimator):
    def __init__(self, features):
        self.features = features

    def fit(self, X=None, y=None):
        return self

    def transform(self, data):
        return data.loc[:, self.features]


def create_pipeline(topic_kwargs, regressor_kwargs, features=FEATURES):
    feature_generation = FeatureUnion(
        transformer_list=[
            ('topic_model', TopicModel(**topic_kwargs)),
            ('feature_selection', FeatureSelector(features))
        ]
    )

    pipeline = Pipeline(steps=[
            ('feature_generation', feature_generation),
            ('regressor', RandomForestRegressor(**regressor_kwargs))
        ]
    )

    return pipeline


def train_pipeline(post_frame, **kwargs):
    targets = kwargs.get('targets', TARGETS)

    logger.info('Training pipeline...')
    target_frame = post_frame.loc[:, targets]

    pipeline = create_pipeline(**kwargs)
    pipeline.fit(post_frame, target_frame)

    score = pipeline.score(post_frame, target_frame)
    logger.info('...Done! Training score {}'.format(score))

    return pipeline


def cross_validate(post_frame, param_grid,
                   train_size=0.8, n_jobs=3,
                   cv=3, refit=True, verbose=1, **kwargs):

    targets = kwargs.get('targets', TARGETS)

    train_frame, test_frame = train_test_split(post_frame,
                                               train_size=train_size)

    pipeline = create_pipeline(**kwargs)

    grid_search = GridSearchCV(pipeline, param_grid, n_jobs=n_jobs,
                               cv=cv, refit=refit, verbose=verbose)
    logger.info('Starting Grid Search')
    grid_search.fit(train_frame, train_frame.loc[:, targets])

    logger.info("\nGrid scores on development set:\n")
    means = grid_search.cv_results_['mean_test_score']
    stds = grid_search.cv_results_['std_test_score']
    for mean, std, params in zip(means, stds, grid_search.cv_results_['params']):
        logger.info("{:0.3f} (+/-{:0.03f}) for {}".format(mean, std * 2, params))

    score = grid_search.score(test_frame, test_frame.loc[:, targets])

    logger.info("FINAL TEST Score {} \n of best estimator:\n\n{}".format(score,
                                        grid_search.best_estimator_.get_params()))


def load_or_train_pipeline(post_frame, directory, current_datetime=None,
                           overwrite=False, store=True, **kwargs):
    if current_datetime is None:
        current_datetime = pd.datetime.utcnow()
    else:
        current_datetime = pd.to_datetime(current_datetime)

    if not os.path.isdir(directory):
        os.makedirs(directory)
    filename = FILENAME_TEMPLATE.format(time=current_datetime.strftime('%Y-%U'))

    filename = os.path.join(directory,filename)
    if os.path.isfile(filename) and not overwrite:
        logger.info('Found file {} will load it'.format(filename))
        pipeline = joblib.load(filename)
    else:
        logger.info('File {} not found, will start training'.format(filename))
        pipeline = train_pipeline(post_frame, **kwargs)
        if store:
            logger.info('Storing file {} to disk'.format(filename))
            joblib.dump(pipeline, filename, compress=8)
    return pipeline