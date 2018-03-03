import logging
import time

from steem.post import Post

import trufflepig.bchain.posts as tfbp
import trufflepig.bchain.getdata as tfgd


logger = logging.getLogger(__name__)


I_WAS_HERE = 'Huh? Seems like already voted on this post, thanks for calling anyway!'

YOU_DID_NOT_MAKE_IT = """I am sorry, I cannot evaluate your post. This can have several reasons, for example, it may not be long enough, it's not in English, has been filtered, etc."""


def post_on_call(sorted_post_frame, account, steem, topN_link,
                 exclusion_set=tfgd.EXCLUSION_VOTERS_SET,
                 sleep_time=20.1):

    weight = min(100 / len(sorted_post_frame), 10)

    for kdx, (_, row) in enumerate(sorted_post_frame.iterrows()):
        try:
            comment = Post('@{}/{}'.format(row.comment_author,
                                           row.comment_permalink), steem)
            comment.commit.no_broadcast = steem.commit.no_broadcast
            # Wait a bit Steemit nodes hate comments in quick succession
            time.sleep(sleep_time)
            if row.passed and not tfgd.exclude_if_voted_by(row.active_votes, exclusion_set):
                if not tfgd.exclude_if_voted_by(row.active_votes, {account}):

                    logger.info('Voting and commenting on https://steemit.com/@{author}/{permalink}'
                                    ''.format(author=row.author, permalink=row.permalink))
                    reply = tfbp.on_call_comment(reward=row.predicted_reward,
                                                 author=row.comment_author,
                                                 votes=row.predicted_votes,
                                                 topN_link=topN_link)

                    post = Post('@{}/{}'.format(row.author, row.permalink), steem)
                    # to pass around the no broadcast setting otherwise it is lost
                    # see https://github.com/steemit/steem-python/issues/155
                    post.commit.no_broadcast = steem.commit.no_broadcast

                    # We cannot use this post.upvote(weight=weight, voter=account)
                    # because we need to vote on archived posts as a flag!
                    post.commit.vote(post.identifier, weight, account=account)
                else:
                    reply = I_WAS_HERE
            else:
                reply = YOU_DID_NOT_MAKE_IT

            logger.info('Replying to https://steemit.com/@{author}/{permalink} '
                        'with {answer}...'.format(author=row.comment_author,
                                               permalink=row.comment_permalink,
                                               answer=reply[:64]))
            comment.reply(body=reply, author=account)

        except Exception as e:
            logger.exception('Something went wrong with row {}'.format(row))