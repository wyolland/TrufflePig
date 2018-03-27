from steem.amount import Amount
import trufflepig.bchain.postdata as tbpd
import logging


logger = logging.getLogger(__name__)



def compute_total_sbd(upvote_payments):
    sbd = 0
    steem = 0
    for (author, permalink), payments in upvote_payments.items():
        for payment in payments.values():
            amount = Amount(payment['amount'])
            value = amount.amount
            asset = amount.asset
            if asset == 'SBD':
                sbd += value
            elif asset == 'STEEM':
                steem += value
    return sbd, steem


def create_trending_post(post_frame, upvote_payments, poster, topN_permalink,
                         overview_permalink, current_datetime):
    total_paid_sbd, total_paid_steem = compute_total_sbd(upvote_payments)

    logger.info('People spend {} SBD and {} Steem on Bid Bots the last 24 '
                'hours.'.format(total_paid_sbd, total_paid_steem))

    no_bid_bots_frame = post_frame.loc[post_frame.bought_votes == 0, :].copy()
    no_bid_bots_frame.sort_values('reward', inplace=True, ascending=False)

    logger.info('Voted Posts {} out of {}'.format(len(post_frame) - len(no_bid_bots_frame),
                                                  len(post_frame)))

    tbpd.post_top_trending_list(no_bid_bots_frame, poster, current_datetime,
                                overview_permalink=overview_permalink,
                                trufflepicks_permalink=topN_permalink,
                                steem_amount=total_paid_steem,
                                sbd_amount=total_paid_sbd)
