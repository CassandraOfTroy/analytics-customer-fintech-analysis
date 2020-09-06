from wepair.plugins.plugin import Plugin
import pandas as pd
import numpy as np
from dateutil.relativedelta import *
from ...globals import COLNAMES_PE
from ...utils.location import Location
from ...utils.customer_tools import Feature, remove_all_features, add_feature
from sklearn.cluster import MiniBatchKMeans
#for calculating customers' recency and frequency 
from lifetimes import BetaGeoFitter, GammaGammaFitter
from itertools import product
from os.path import join, isfile
import pickle
import matplotlib.pyplot as plt
from reportlab.platypus import Paragraph, Spacer, Image, Table, PageBreak
from reportlab.lib import colors
import plotly.io as pio
import plotly.graph_objs as go
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
CUSTOMER_NAME = COLNAMES_PE['Card Holder Name']
CUSTOMER_ID = COLNAMES_PE['Customer Unique ID']
CUSTOMER_EMAIL = COLNAMES_PE['Email (Consumer)']
SHOP_COUNTRY = COLNAMES_PE['Merchant Country']
CUSTOMER_CITY = COLNAMES_PE['City (Consumer Address)']
SHOP_NAME = COLNAMES_PE['Merchant Account Short Name']
CUSTOMER_RFM_SEGMENT = COLNAMES_PE['Customer RFM Segment']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']

CHURN_T_HORIZON = 365.0
N_CLUSTERS = 5
N_BEST_PREDICTED_CUSTOMERS = 10
KMEANS_RANDOM_INITIAL_STATE = 1


class CustomerSgement(Plugin):

    @staticmethod
    def _plot_bubble_chart(data, filename, cmap):
        bubble_chart_df = pd.DataFrame()
        bubble_chart_df['Frequency'] = data['F_avg']
        bubble_chart_df['Recency'] = data['R_avg']
        bubble_chart_df['Monetary Value in €'] = [int(x) for x in data['M_avg_sum']]
        bubble_chart_df['Customer Count'] = data['customer_count']

        color_list = [[0.0, '#63B2FF'], [0.1, cmap['colors']['night blue']], [1.0, '#000000']]

        fig = {
            'data': [
                {
                    'type': 'scatter',
                    'mode': 'markers+text',
                    'x': bubble_chart_df['Recency'],
                    'y': bubble_chart_df['Frequency'],
                    'text': [x+1 for x in range(N_CLUSTERS)],
                    'textposition': 'bottom center',
                    'textfont': {
                      'size': 20
                    },
                    'marker': {
                        'size': bubble_chart_df['Customer Count'],
                        'color': bubble_chart_df['Monetary Value in €'],
                        'sizemode': 'diameter',
                        'sizemin': 20,
                        'sizeref': max(bubble_chart_df['Customer Count'])/100.0,
                        'symbol': 'circle',
                        'colorscale': color_list
                    }
                }
            ],
            'layout': {
                'xaxis': {
                    'title': 'Recency',
                    'zeroline': False,
                    'showline': True,
                    "tickfont": {
                        "size": 20,
                    },
                    "titlefont": {
                        "size": 20,
                    }
                },
                'yaxis': {
                    'title': 'Frequency',
                    'showline': True,
                    'zeroline': False,
                    "tickfont": {
                        "size": 20,
                    },
                    "titlefont": {
                        "size": 20,
                    }
                },
                "height": 720,
                "width": 1080

            }
        }
        pio.write_image(fig, filename, format='png')

    @staticmethod
    def _plot_clusters_evolution(data, clusters_evolution_filename, cmap):

        traces = []
        for i in range(N_CLUSTERS):
            trace = go.Bar(
                x=data['evolution'][i]['x'],
                y=[k/1000000.0 for k in data['evolution'][i]['y']],
                name='Segment ' + str(i+1),
                marker=dict(
                    color=cmap['palettes']['ek1'][i + 2]
                )
            )
            i += 1
            traces.append(trace)

        layout = go.Layout(
            barmode='stack',
            width=1024,
            height=768,
            margin={
                "t": 0,
                "b": 200,
                "l": 120
            },
            font={
                "size": 20
            },
            xaxis={
                "type": "category",
                "autorange": True,
                "side": 'bottom',
                "visible": True,
                "tickangle": -45,
                "showticklabels": True,
                "showgrid": False,
                "zeroline": True,
                "zerolinewidth": .1,
                "zerolinecolor": "#444",
                "ticklen": 5,
                "tickwidth": 1

            },
            yaxis={
                "type": "linear",
                "automargin": True,
                "tickformat": "3,",
                "ticksuffix": 'M€'
            },
            legend={
                "borderwidth": 0,
                "orientation": "h",
                "traceorder": "normal",
                "y": -0.3,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top",
                "font": {
                    "size": 20
                }
            }

        )
        fig = go.Figure(data=traces, layout=layout)
        pio.write_image(fig, clusters_evolution_filename, format='png')

    @staticmethod
    def _plot_clusters_per_country(data, clusters_per_country_filename, cmap):

        traces = []
        for i in range(N_CLUSTERS):
            trace = go.Bar(
                x=data['country_distribution'][i]['country_name'],
                y=data['country_distribution'][i]['n_customers'],
                name='Segment ' + str(i + 1),
                marker=dict(
                    color=cmap['palettes']['ek1'][i + 2]
                )
            )
            i += 1
            traces.append(trace)

        layout = go.Layout(
            barmode='stack',
            width=1200,
            height=900,
            font={
                "size": 20
            },
            margin={
                "t": 0,
                "b": 200,
                "l": 120
            },
            xaxis={
                "type": "category",
                "autorange": True,
                "side": 'bottom',
                "visible": True,
                "tickangle": -45,
                "showticklabels": True,
                "showgrid": False,
                "zeroline": True,
                "zerolinewidth": .1,
                "zerolinecolor": "#444",
                "ticklen": 5,
                "tickwidth": 1

            },
            yaxis={
                "type": "linear",
                "automargin": True,
                "tickformat": "3,"
            },
            legend={
                "borderwidth": 0,
                "orientation": "v",
                "x": .9,
                "y": .9,
                "xanchor": "right",
                "yanchor": "top",
                    }

        )
        fig = go.Figure(data=traces, layout=layout)
        pio.write_image(fig, clusters_per_country_filename, format='png', scale=2)
        '''
        sns.set()
        sns.set_style("white")
        columns = ['Segments'] + data['country_distribution'][0]['country_name']

        rows = list()
        for i in range(N_CLUSTERS):
            rows.append(['Segment ' + str(i + 1)] + data['country_distribution'][i]['n_customers'])

        clusters_per_country_df = pd.DataFrame(data=rows, columns=columns)

        fig, ax = plt.subplots()
        clusters_per_country_df.set_index('Segments').T.plot(kind='bar', stacked=True, ax=ax, rot=45, figsize=(15, 12))
        ax.yaxis.grid(True)
        ax.set_yticklabels(["{:}k".format(int(x / 1000)) for x in ax.get_yticks()])
        sns.despine(left=True)
        plt.savefig(clusters_per_country_filename, bbox_inches='tight', dpi=300)
        '''

    def __init__(self, plugin_folder, id, options=None):
        self.plugin_name = "Customer rfm"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle', 'customers.pickle']

    def process(self, *args, **kwargs):

        customer_rfm = {'has_data': False}
        logger.debug(kwargs)

        location = Location(self.options['assets'])

        if len(args) != 2:
            logger.warning('Fatal Error: Data Input Source Missing')
            return customer_rfm
        args = list(args)
        transactions = args[0]
        customers = args[1]
#why are only these necessary keys? 
        necessary_keys = [TRANSACTION_DATE, AMOUNT_IN_EUR, CUSTOMER_NAME, CUSTOMER_ID, TRANSACTION_IS_RETURN,
                          TRANSACTION_IS_CAPTURE]
        if not all(key in transactions.columns for key in necessary_keys):
            return customer_rfm

        customer_rfm = pd.DataFrame()

        # ------------------------------------------------------------------------------------------------------------------
        # Initialization
        # ------------------------------------------------------------------------------------------------------------------

        list_columns = [TRANSACTION_DATE, AMOUNT_IN_EUR, CUSTOMER_ID, CUSTOMER_NAME, TRANSACTION_IS_RETURN,
                        TRANSACTION_IS_CAPTURE]
        for col in [CUSTOMER_EMAIL, CUSTOMER_CITY, SHOP_COUNTRY, SHOP_NAME]:
            if col in transactions.columns:
                list_columns.append(col)

        txs = transactions[transactions[TRANSACTION_IS_CAPTURE]][list_columns].copy()
        cust = customers.copy()
        temp = transactions[transactions[TRANSACTION_IS_CAPTURE]][[CUSTOMER_ID, TRANSACTION_DATE]].groupby(CUSTOMER_ID)[TRANSACTION_DATE].nsmallest(2).groupby(level=CUSTOMER_ID).last()
       
        #merging the two data frames
        pd.merge(cust, temp.to_frame('second_transaction_date'), on=CUSTOMER_ID)
        #creating new variable which will have exact number of days between 2 purchases that customer made
        cust['time_between_first_second_purchase'] = cust['second_transaction_date'] - cust['first_transaction_date']
        cust['time_between_first_second_purchase'] = cust['time_between_first_second_purchase'].apply(lambda x: x.days)
        last_transaction_date = txs[TRANSACTION_DATE].max()
        first_transaction_date = txs[TRANSACTION_DATE].min()
        
        one_year_ago = last_transaction_date - relativedelta(months=12)

#find the retained customers
        for i in range(1, 13):
            month_end = last_transaction_date - relativedelta(months=i - 1)
            month_begin = last_transaction_date - relativedelta(months=i)
            retained = cust[
                (cust['n_transactions'] > 1) & (cust['first_transaction_date'] > month_begin) & (
                            cust['n_days_since_last_purchase'] < 78)]
#list is a collection which is ordered and changeable...allows duplicate members
#to collect existing customers, new customers, returning customers and one-time customers
        n_qc_list = list()
        n_new_list = list()
        n_returning_list = list()
        n_one_time_list = list()
        
        today = first_transaction_date
        test_cust_df = cust.sample(frac=0.01)

        while today < last_transaction_date:
            #this is returning customer? 
            returning_ids = set(test_cust_df[test_cust_df['second_transaction_date'] <= today][CUSTOMER_ID].tolist())
            #figure what is qc_ids?
            qc_ids = set(test_cust_df[((test_cust_df['second_transaction_date'] > today) | (
                pd.isna(test_cust_df['second_transaction_date']))) & (
                                              test_cust_df['first_transaction_date'] <= today) & (
                                              (today - test_cust_df['first_transaction_date']).apply(
                                                  lambda x: x.days) > 41)][CUSTOMER_ID].tolist())
            #is this a new customer? 
            new_ids = set(test_cust_df[((test_cust_df['second_transaction_date'] > today) | (
                pd.isna(test_cust_df['second_transaction_date']))) & (
                                               test_cust_df['first_transaction_date'] <= today) & (
                                               (today - test_cust_df['first_transaction_date']).apply(
                                                   lambda x: x.days) <= 41)][CUSTOMER_ID].tolist())
            #this is only one-time customer?
            one_time_ids = set(test_cust_df[((test_cust_df['second_transaction_date'] > today) | (
                pd.isna(test_cust_df['second_transaction_date']))) & (test_cust_df['first_transaction_date'] <= today)][
                                   CUSTOMER_ID].tolist())
            n_qc_list.append(len(qc_ids))
            n_new_list.append(len(new_ids))
            n_one_time_list.append(len(one_time_ids))
            n_returning_list.append(len(returning_ids))
            today += relativedelta(days=1)
            print(today)

        plt.bar(range(len(n_new_list)), n_returning_list)
        list_sum = [n_new_list[i] + n_returning_list[i] for i in range(len(n_new_list))]
        plt.bar(range(len(n_new_list)), n_new_list, bottom=n_returning_list)
        plt.bar(range(len(n_new_list)), n_qc_list, bottom=list_sum)
        logger.debug('Time period for the segmentation: '
                      '{from_date} to {to_date}'.format(from_date=one_year_ago,
                                                        to_date=last_transaction_date))

        # ------------------------------------------------------------------------------------------------------------------
        # Frequency, Monetary, and churn probability prediction
        # ------------------------------------------------------------------------------------------------------------------
 
    #read about BetaGeoFitter: https://towardsdatascience.com/whats-a-customer-worth-8daf183f8a4f
    #read 2: 
        bgf = BetaGeoFitter(penalizer_coef=0.0)
        #to do this, first you have to calculate frequency anc recency
        #recency - number of days since their last purchase
        #frequency - number of purchases 
        bgf.fit(cust['frequency'], cust['recency'], cust['T'], maxiter=10000, tol=1e-6, verbose=True)
        print(bgf)

        cust['predicted_p_alive'] = bgf.conditional_probability_alive(cust['frequency'], cust['recency'], cust['T'])
        cust['predicted_F'] = bgf.conditional_expected_number_of_purchases_up_to_time(CHURN_T_HORIZON,
                                                                                      cust['frequency'],
                                                                                      cust['recency'],
                                                                                      cust['T'])

        repeat_cust = cust[cust['n_transactions'] > 1].index.values
        print(cust.loc[repeat_cust, ['monetary_value', 'frequency']].corr())
        
        #GammaGammaFitter
        #read about GammaGamma: https://medium.com/bolt-labs/understanding-the-customer-lifetime-value-with-data-science-c14dcafa0364
        
        ggf = GammaGammaFitter(penalizer_coef=0)
        ggf.fit(cust.loc[repeat_cust, 'frequency'], cust.loc[repeat_cust, 'monetary_value'], verbose=True)
        print(ggf)

        p, q, v = ggf._unload_params('p', 'q', 'v')
        cust['predicted_M_avg'] = (p * v) / (q - 1)
        
        cust.loc[cust['n_transactions'] > 1, 'predicted_M_avg'] = ggf.conditional_expected_average_profit(
            cust.loc[repeat_cust, 'frequency'],
            cust.loc[repeat_cust, 'monetary_value'])
        
        cust['CLV'] = cust['predicted_F'] * cust['predicted_M_avg']
        #I believe that this is a predicted value
        cust['pCLV'] = cust['predicted_p_alive'] * cust['predicted_F'] * cust['predicted_M_avg']

        # ------------------------------------------------------------------------------------------------------------------
        # Segmentation of last year cust
        # ------------------------------------------------------------------------------------------------------------------

        if txs[TRANSACTION_DATE].min() < one_year_ago:
            print('Re-compute the features for the cust from last year')
            transactions_last_year = txs[txs[TRANSACTION_DATE] >= one_year_ago]
            customers_last_year = cust[cust['last_transaction_date'] >= one_year_ago]
            # print('Columns are: ', customers_last_year.columns.values)
            customers_last_year = remove_all_features(customers_last_year)
            # print('Columns are now: ', customers_last_year.columns.values)
            customers_last_year = add_feature(customers_last_year, transactions_last_year,
                                                                      Feature.ALL,
                                                                      end_period=transactions_last_year[
                                                                          TRANSACTION_DATE].max())
        else:
            transactions_last_year = txs
            #appending cust values to the customers_last_year variable 
            customers_last_year = cust
            #creating new variables in the dataframe:
        customers_last_year['R'] = (customers_last_year['last_transaction_date'] - one_year_ago).apply(
            lambda x: int(x.total_seconds() / (24.0 * 60 * 60)))
        customers_last_year['F'] = customers_last_year['n_transactions']
        customers_last_year['M_sum'] = customers_last_year['total_spending']
        customers_last_year['M_avg'] = customers_last_year['avg_spending']

        customers_last_year['norm_R'] = (customers_last_year['R']
                                         - customers_last_year['R'].mean()) / customers_last_year['R'].std()
        customers_last_year['norm_F'] = (customers_last_year['F']
                                         - customers_last_year['F'].mean()) / customers_last_year['F'].std()
        customers_last_year['norm_M_sum'] = (customers_last_year['M_sum']
                                             - customers_last_year['M_sum'].mean()) / customers_last_year['M_sum'].std()

        kmeans = MiniBatchKMeans(n_clusters=N_CLUSTERS, init='k-means++', max_iter=1000, tol=1e-6, n_init=10,
                                 random_state=KMEANS_RANDOM_INITIAL_STATE, batch_size=1000, verbose=True)
        kmeans.fit(customers_last_year[['norm_R', 'norm_F', 'norm_M_sum']])
        customers_last_year[CUSTOMER_RFM_SEGMENT] = kmeans.labels_
        customers_last_year.drop(['norm_R', 'norm_F', 'norm_M_sum'], axis=1, inplace=True)

        # Saving the information about each segment
        customer_rfm['R_avg'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False).agg({'R': 'mean'})['R']

        customer_rfm['F_avg'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False).agg({'F': 'mean'})['F']

        customer_rfm['M_avg_sum'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False) \
            .agg({'M_sum': 'mean'})['M_sum']

        customer_rfm['M_avg_avg'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'M_avg': 'mean'})['M_avg']
        customer_rfm['recency_avg'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'recency': 'mean'})['recency']
        customer_rfm['frequency_avg'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'frequency': 'mean'})['frequency']
        customer_rfm['T_avg'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'T': 'mean'})['T']
        customer_rfm['monetary_value_avg'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'monetary_value': 'mean'})['monetary_value']
        customer_rfm['customer_count'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'R': 'count'})['R']
        customer_rfm['segment_revenue'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'M_sum': 'sum'})['M_sum']
        customer_rfm['predicted_revenue'] = customers_last_year.groupby(CUSTOMER_RFM_SEGMENT, sort=False)\
            .agg({'pCLV': 'sum'})['pCLV']

        # predicting future txs, p_alive and future monetary value for customer_rfm

        customer_rfm['predicted_F'] = 0.0
        customer_rfm['predicted_p_alive'] = 0.0
        customer_rfm['predicted_M_avg'] = 0.0
        for seg_idx in range(N_CLUSTERS):
            customer_rfm.loc[seg_idx, 'predicted_F'] = customers_last_year[
                customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx]['predicted_F'].mean()
            customer_rfm.loc[seg_idx, 'predicted_p_alive'] = customers_last_year[
                customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx]['predicted_p_alive'].mean()
            customer_rfm.loc[seg_idx, 'predicted_M_avg'] = customers_last_year[
                customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx]['predicted_M_avg'].mean(skipna=True)
            customer_rfm.loc[seg_idx, 'CLV'] = customers_last_year[
                customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx]['CLV'].sum(skipna=True)

        customer_rfm['predicted_FM'] = customer_rfm['predicted_F'] * customer_rfm['predicted_M_avg'] * \
            customer_rfm['customer_count']
        customer_rfm['predicted_pFM'] = customer_rfm['predicted_p_alive'] * customer_rfm['predicted_F'] * \
            customer_rfm['predicted_M_avg'] * customer_rfm['customer_count']

        # predicting future txs, p_alive and future monetary value for customer_rfm persona
        customer_rfm['predicted_F_persona'] = customer_rfm.apply(
            lambda r: bgf.conditional_expected_number_of_purchases_up_to_time(CHURN_T_HORIZON,
                                                                              int(np.rint(r['frequency_avg'])),
                                                                              r['recency_avg'],
                                                                              r['T_avg']),
            axis=1)
        customer_rfm['predicted_p_alive_persona'] = customer_rfm.apply(
            lambda r: float(bgf.conditional_probability_alive(int(np.rint(r['frequency_avg'])),
                                                              r['recency_avg'], r['T_avg'])), axis=1)
        customer_rfm['predicted_M_avg_persona'] = customer_rfm.apply(
            lambda r: ggf.conditional_expected_average_profit(int(np.rint(r['frequency_avg'])),
                                                              r['monetary_value_avg']),
            axis=1)

        customer_rfm['predicted_FM_persona'] = customer_rfm['predicted_F_persona'] * \
            customer_rfm['predicted_M_avg_persona'] * \
            customer_rfm['customer_count']

        customer_rfm['predicted_pFM_persona'] = customer_rfm['predicted_p_alive_persona'] * \
            customer_rfm['predicted_F_persona'] * \
            customer_rfm['predicted_M_avg_persona'] * \
            customer_rfm['customer_count']

        revenue = float("{0:.2f}".format(customer_rfm['segment_revenue'].sum()))

        # ------------------------------------------------------------------------------------------------------------------
        # Analyze the evolution of the customer_rfm
        # ------------------------------------------------------------------------------------------------------------------

        transactions_last_year = pd.merge(transactions_last_year,
                                          customers_last_year[[CUSTOMER_ID, CUSTOMER_RFM_SEGMENT]],
                                          on=CUSTOMER_ID, how='left')

        transactions_last_year['month_year'] = transactions_last_year[TRANSACTION_DATE].values.astype('datetime64[M]')
        transactions_last_year.drop([CUSTOMER_ID, TRANSACTION_DATE], axis=1, inplace=True)

        # calculating revenue for different customer_rfm for each month
        segments_evolution = transactions_last_year.groupby([CUSTOMER_RFM_SEGMENT, 'month_year'], sort=False) \
            .sum() \
            .reset_index() \
            .sort_values(by=[CUSTOMER_RFM_SEGMENT, 'month_year'], ascending=[True, True])
        del transactions_last_year

        # calculating all possible combinations of customer_rfm and months
        segments_date = pd.DataFrame(list(product(
            segments_evolution[CUSTOMER_RFM_SEGMENT].drop_duplicates().tolist(),
            segments_evolution['month_year'].drop_duplicates().tolist())),
            columns=[CUSTOMER_RFM_SEGMENT, 'month_year'])

        # performing outer join of above two dfs (data frames)
        segments_evolution = pd.merge(segments_evolution, segments_date,
                                      on=[CUSTOMER_RFM_SEGMENT, 'month_year'], how='outer') \
            .sort_values(by=[CUSTOMER_RFM_SEGMENT, 'month_year'], ascending=[True, True]) \
            .fillna(0)

        # ------------------------------------------------------------------------------------------------------------------
        # Best and worst cust
        # ------------------------------------------------------------------------------------------------------------------

        returning_customers_last_year = customers_last_year[customers_last_year['n_transactions'] > 1]
        best_customers_lastyear = returning_customers_last_year.sort_values('CLV', ascending=False) \
            .head(N_BEST_PREDICTED_CUSTOMERS)
        best_customers_lastyear = best_customers_lastyear.rename(columns={CUSTOMER_ID: 'customer_unique_ID'}) \
            .to_dict(orient='list')

        worst_customers_lastyear = returning_customers_last_year.sort_values('CLV', ascending=False) \
            .tail(N_BEST_PREDICTED_CUSTOMERS)
        worst_customers_lastyear = worst_customers_lastyear.rename(columns={CUSTOMER_ID: 'customer_unique_ID'}) \
            .to_dict(orient='list')

        # ------------------------------------------------------------------------------------------------------------------
        # Parameters for future cust
        # ------------------------------------------------------------------------------------------------------------------

        pred_new_customer_frequency = float(
            "{0:.2f}".format(bgf.expected_number_of_purchases_up_to_time(CHURN_T_HORIZON)))
        past_new_customer_monetary = float("{0:.2f}".format(cust.loc[repeat_cust, 'monetary_value'].mean()))
        pred_new_customer_monetary = float("{0:.2f}".format((p * v) / (q - 1)))

        # ------------------------------------------------------------------------------------------------------------------
        # Save customer emails for each segment
        # ------------------------------------------------------------------------------------------------------------------

        customer_rfm['customers_emails'] = ''
        if CUSTOMER_EMAIL in txs.columns:
            customers_last_year = pd.merge(customers_last_year, txs[[CUSTOMER_ID, CUSTOMER_EMAIL]], on=CUSTOMER_ID,
                                           how='left')
            customers_last_year.drop_duplicates(subset=CUSTOMER_ID, keep='first', inplace=True)
            for seg_idx in range(N_CLUSTERS):
                mailing_list = list(customers_last_year[
                                        customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx][CUSTOMER_EMAIL])
                mailing_list = [str(email) for email in mailing_list if str(email) != '' and str(email) != 'nan']
                customer_rfm.loc[seg_idx, 'customers_emails'] = '; '.join(mailing_list)

        # ------------------------------------------------------------------------------------------------------------------
        # Save cust countries for each segment
        # ------------------------------------------------------------------------------------------------------------------

        country_distribution = {'has_data': False}
        city_distribution = {'has_data': False}

        if SHOP_COUNTRY in txs.columns:
            country_distribution['has_data'] = True
            customers_last_year = pd.merge(customers_last_year, txs[[CUSTOMER_ID, SHOP_COUNTRY]],
                                           on=CUSTOMER_ID, how='left')
            customers_last_year.drop_duplicates(subset=CUSTOMER_ID, keep='first', inplace=True)
            customers_last_year[SHOP_COUNTRY].fillna('', inplace=True)
            customers_last_year['country_code'] = customers_last_year[SHOP_COUNTRY].apply(location.get_country_iso3)
            customers_last_year['country_name'] = customers_last_year[SHOP_COUNTRY].apply(location.get_country_name)

            country_names = customers_last_year['country_name'].unique().tolist()
            country_codes = customers_last_year['country_code'].unique().tolist()

            sum_n_cust = [0] * len(country_codes)
            sum_n_cust_pct = [0.0] * len(country_codes)
            include_emails = True if CUSTOMER_EMAIL in txs.columns else False

            for seg_idx in range(N_CLUSTERS):
                temp = customers_last_year[customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx][['country_code']] \
                    .groupby(by='country_code') \
                    .size() \
                    .reset_index() \
                    .rename(columns={0: 'n_customers'}) \
                    .set_index(keys='country_code', drop=True)
                list_n_cust = list()
                list_n_cust_pct = list()
                list_emails = list()
                list_n_emails = list()
                total_cust_in_seg = sum(temp['n_customers'].tolist())
                for idx, country in enumerate(country_codes):
                    n_cust = 0
                    n_cust_pct = 0.0
                    emails = ''
                    n_emails = 0
                    if country in temp.index:
                        n_cust = int(temp.loc[country, 'n_customers'])
                        n_cust_pct = 100.0 * (n_cust / total_cust_in_seg)
                        if include_emails:
                            emails = list(customers_last_year[(customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx) & (
                                    customers_last_year['country_code'] == country)][CUSTOMER_EMAIL].dropna())
                            emails = [email for email in emails if email != 'nan']
                            n_emails = len(emails)
                            emails = '; '.join(emails)
                    list_n_cust.append(n_cust)
                    list_n_cust_pct.append(n_cust_pct)
                    list_emails.append(emails)
                    list_n_emails.append(n_emails)
                    sum_n_cust[idx] += n_cust
                    sum_n_cust_pct[idx] += n_cust_pct

                country_distribution[seg_idx] = {
                    'n_customers': list_n_cust,
                    'n_customers_pct': list_n_cust_pct,
                    'country_code': country_codes,
                    'country_name': country_names,
                    'emails': list_emails,
                    'n_emails': list_n_emails
                }


            sorted_idx = [i for i, _ in sorted(enumerate(sum_n_cust), key=lambda n: n[1], reverse=True)]
            country_names = [x for _, x in sorted(enumerate(country_names), key=lambda l: sorted_idx.index(l[0]))]
            country_codes = [x for _, x in sorted(enumerate(country_codes), key=lambda l: sorted_idx.index(l[0]))]

            for seg_idx in range(N_CLUSTERS):
                country_distribution[seg_idx] = {
                    'n_customers': [x for _, x in sorted(enumerate(country_distribution[seg_idx]['n_customers']),
                                                         key=lambda l: sorted_idx.index(l[0]))],
                    'n_customers_pct': [x for _, x in
                                        sorted(enumerate(country_distribution[seg_idx]['n_customers_pct']),
                                               key=lambda l: sorted_idx.index(l[0]))],
                    'country_code': country_codes,
                    'country_name': country_names,
                    'emails': [x for _, x in sorted(enumerate(country_distribution[seg_idx]['emails']),
                                                    key=lambda l: sorted_idx.index(l[0]))],
                    'n_emails': [x for _, x in sorted(enumerate(country_distribution[seg_idx]['n_emails']),
                                                      key=lambda l: sorted_idx.index(l[0]))]
                }

            # ------------------------------------------------------------------------------------------------------------------
            # Save cust cities for each segment
            # ------------------------------------------------------------------------------------------------------------------

            if CUSTOMER_CITY in txs.columns:
                city_distribution['has_data'] = True
                customers_last_year = pd.merge(customers_last_year, txs[[CUSTOMER_ID, CUSTOMER_CITY]],
                                               on=CUSTOMER_ID, how='left')
                customers_last_year.drop_duplicates(subset=CUSTOMER_ID, keep='first', inplace=True)
                customers_last_year[CUSTOMER_CITY] = customers_last_year[CUSTOMER_CITY].apply(lambda x: x.title())
                customers_last_year[CUSTOMER_CITY].replace(to_replace='Nan', value='Unknown', inplace=True)
                customers_last_year['key'] = customers_last_year[CUSTOMER_CITY] + ' (' + \
                    customers_last_year['country_name'] + ')'
                for seg_idx in range(N_CLUSTERS):
                    temp = customers_last_year[customers_last_year[CUSTOMER_RFM_SEGMENT] == seg_idx][['key']] \
                        .groupby(by='key') \
                        .size() \
                        .reset_index() \
                        .rename(columns={0: 'n_customers'}) \
                        .sort_values(by='n_customers', ascending=False)
                    city_distribution[seg_idx] = {
                        'n_customers': temp['n_customers'].tolist(),
                        'city': temp['key'].tolist()
                    }

        # ------------------------------------------------------------------------------------------------------------------
        # Save the data to be returned
        # ------------------------------------------------------------------------------------------------------------------

        list_of_segment_index = customer_rfm.index.values.tolist()
        list_of_segment_index = [str(x + 1) for x in list_of_segment_index]

        customer_rfm = customer_rfm.to_dict(orient='list')
        customer_rfm['has_data'] = True
        customer_rfm['config'] = {
            'CHURN_T_HORIZON': CHURN_T_HORIZON,
            'N_CLUSTERS': N_CLUSTERS,
            'N_BEST_PREDICTED_CUSTOMERS': N_BEST_PREDICTED_CUSTOMERS
        }

        customer_rfm['period_start'] = one_year_ago.strftime('%B %d, %Y')
        customer_rfm['period_end'] = last_transaction_date.strftime('%B %d, %Y')
        customer_rfm['segment_index'] = list_of_segment_index
        customer_rfm['n_customers'] = int(customers_last_year['frequency'].count())
        customer_rfm['n_transactions'] = int(txs[txs[TRANSACTION_DATE] >= one_year_ago][CUSTOMER_ID].count())
        customer_rfm['revenue'] = int(revenue)
        customer_rfm['pred_new_customer_frequency'] = float(pred_new_customer_frequency)
        customer_rfm['past_new_customer_monetary'] = float(past_new_customer_monetary)
        customer_rfm['pred_new_customer_monetary'] = float(pred_new_customer_monetary)
        customer_rfm['best_customers_lastyear'] = best_customers_lastyear
        customer_rfm['worst_customers_lastyear'] = worst_customers_lastyear
        customer_rfm['evolution'] = dict()
        for i in range(N_CLUSTERS):
            customer_rfm['evolution'][i] = {
                'x': segments_evolution.loc[segments_evolution[CUSTOMER_RFM_SEGMENT] == i, 'month_year'].apply(
                    lambda x: x.strftime('%b-%y')).tolist(),
                'y': segments_evolution.loc[segments_evolution[CUSTOMER_RFM_SEGMENT] == i, AMOUNT_IN_EUR].tolist()
            }
        customer_rfm['country_distribution'] = country_distribution
        customer_rfm['city_distribution'] = city_distribution

        process_output_file = join(self.process_output_folder, 'out.pickle')
        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(customer_rfm, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return customer_rfm

    def plot(self, *args, **kwargs):

        rfm_bubble_chart_filename = join(self.plot_output_folder, 'rfm_bubble_chart.png')
        clusters_evolution_filename = join(self.plot_output_folder, 'clusters_evolution_chart.png')
        clusters_per_country_filename = join(self.plot_output_folder, 'clusters_per_country_chart.png')
        # Load the data
        input_data_file = join(self.process_output_folder, 'out.pickle')
        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)
        cmap = kwargs['cmap']

        self._plot_bubble_chart(data, rfm_bubble_chart_filename, cmap)
        self._plot_clusters_evolution(data, clusters_evolution_filename, cmap)
        self._plot_clusters_per_country(data, clusters_per_country_filename, cmap)

    def report(self, report, styles, *args, **kwargs):
        input_data_file = join(self.process_output_folder, 'out.pickle')
        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        data_list = list()
        for i in range(N_CLUSTERS):
            data_list.append([str(i+1), '{:,}'.format(data['customer_count'][i]),
                              '{:,}€'.format(int(data['segment_revenue'][i])),
                              '{:.2f}'.format(data['R_avg'][i]), '{:.2f}'.format(data['F_avg'][i]),
                              '{:.2f}'.format(data['predicted_F'][i]), '{:.2f}'.format(data['predicted_p_alive'][i]),
                              '{:,}€'.format(int(data['predicted_pFM'][i]))])

        table_data = [['Observed', '', '', '', '', 'Predicted', '', '']] + \
                     [['ID', '# customers', 'Gross sales', 'Avg. R', 'Avg. F', 'Avg. F',
                       'Prob. being active', 'Gross sales']] + data_list + \
                     [['Total', '{:,}'.format(sum(data['customer_count'])),
                       '{:,}€'.format(int(sum(data['segment_revenue']))), '', '',
                       '', '', '{:,}€'.format(int(sum(data['predicted_pFM'])))]]

        t = Table(table_data)
        t.setStyle([('BOX', (0, -1), (-1, -1), 0.25, colors.black), ('SPAN', (0, 0), (4, 0)), ('SPAN', (5, 0), (-1, 0)),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TEXTCOLOR', (0, 0), (4, 1), colors.white), ('BACKGROUND', (0, 0), (4, 1), '#002846'),
                    ('TEXTCOLOR', (5, 0), (-1, 1), colors.white), ('BACKGROUND', (5, 0), (-1, 1), '#00d2be'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey)])
        for x in ['rfm_bubble_chart.png', 'clusters_evolution_chart.png', 'clusters_per_country_chart.png']:
            if not isfile(join(self.plot_output_folder, x)):
                return

        report.append(Paragraph('CUSTOMER SEGMENTATION (FOR THE LAST 12 MONTHS)', style=styles['Heading2']))
        report.append(Paragraph('Customer clustering based on RFM', style=styles['Heading3-NightBlue']))
        img = Image(join(self.plot_output_folder, 'rfm_bubble_chart.png'),
                    width=500,
                    height=350)
        report.append(img)
        report.append(Spacer(1, 20))
        report.append(Paragraph('This chart groups the customers into 5 clusters based on three '
                                'criteria: (1) The number of days since their last purchase, (2) their number of '
                                'purchases, and (3) the amount that they have spent in total. This model is commonly '
                                'referred to as "RFM" - Recency/Frequency/Monetary Value model. Note that only the '
                                'customers who made a purchase in the last year are considered, so as to give an '
                                'up-to-date snapshot of the company\'s current situation. The x- and y-axis show the '
                                'recency and frequency, respectively. The 5 segments are represented by the 5 circles. '
                                'The circles are centered at the average recency and frequency of all the customers '
                                'that they contain. Their size is proportionate to their number of customers (smaller '
                                'means less customers). Note that only the purchases are considered in this graphic '
                                'and not the returns.',
                                style=styles['Normal']))
        report.append(PageBreak())
        report.append(Paragraph('RFM and predicted revenue', style=styles['Heading3-NightBlue']))
        # replace this spacer with the table
        report.append(t)
        report.append(Spacer(1, 20))
        report.append(Paragraph('This table details each customer segment: its number of '
                                'customers, the gross sales generated by all its customers and their average recency '
                                'and frequency. Then, it shows some predicted parameters for the next 365 days. These '
                                'predictions are calculated based on probabilistic Customer Lifetime Value (CLV) '
                                'modeling. CLV is basically the present value of future cash flows associated with a '
                                'customer. It is a prediction of all the value a business will derive from its '
                                'relationship with a customer. The predicted parameters include the expected average '
                                'number of transactions per customer in the next year (Avg. F), the expected average '
                                'probability of its customers to still be active in the next year, and the expected '
                                'revenue (gross sales).',
                                style=styles['Normal']))
        report.append(Spacer(1, 20))
        report.append(Paragraph('Evolution of the RFM clusters', style=styles['Heading3-NightBlue']))
        img = Image(join(self.plot_output_folder, 'clusters_evolution_chart.png'),
                    width=350,
                    height=300)
        report.append(img)
        report.append(Spacer(1, 20))
        report.append(Paragraph('This chart shows the monthly evolution of gross sales from '
                                'different segments. It can be noticed that some segments are declining over time, '
                                'some are present all the months and some segments are growing over time.',
                                style=styles['Normal']))
        report.append(Spacer(1, 20))
        report.append(Paragraph('Clusters shop country-wise overview', style=styles['Heading3-NightBlue']))
        img = Image(join(self.plot_output_folder, 'clusters_per_country_chart.png'),
                    width=500,
                    height=400)
        report.append(img)
        report.append(Spacer(1, 20))
        report.append(Paragraph('This chart shows for each country the contribution from '
                                'different segments towards the gross sales.', style=styles['Normal']))

