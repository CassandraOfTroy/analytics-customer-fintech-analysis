# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 15:06:32 2019

@author: marina.tosic
"""

from wepair.plugins.plugin import Plugin
import pandas as pd
import numpy as np
from os.path import join
import pickle
from datetime import *
from ...globals import COLNAMES_PE
from lifetimes import BetaGeoFitter, GammaGammaFitter
from sklearn import preprocessing
from sklearn_pandas import DataFrameMapper
from ...utils.location import Location
from ...utils.time_window import TimeWindow
from ...utils.customer_tools import Feature, identify_customers, add_feature, flatten_column_values
from reportlab.platypus import Paragraph, Spacer, Table
from reportlab.lib import colors
from wepair.utils_common.log import Log
from ...utils.report import Report

# log
logger = Log(__name__).get_logger()


SHOP_NAME = COLNAMES_PE['Merchant Account Short Name']
SHOP_COUNTRY = COLNAMES_PE['Merchant Country']
TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
CUSTOMER_NAME = COLNAMES_PE['Card Holder Name']
CUSTOMER_CARD_EXPIRY_DATE = COLNAMES_PE['Card Expiry Date']
CUSTOMER_PAN = COLNAMES_PE['Card Number (PAN)']
CUSTOMER_ID = COLNAMES_PE['Customer Unique ID']
CUSTOMER_EMAIL = COLNAMES_PE['Email (Consumer)']
CUSTOMER_COUNTRY = COLNAMES_PE['Country (Consumer Address)']
CUSTOMER_CITY = COLNAMES_PE['City (Consumer Address)']
CARD_CATEGORY = COLNAMES_PE['Card Category']
CARD_BRAND = COLNAMES_PE['Card Brand']
PAYMENT_METHOD = COLNAMES_PE['Payment Method']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
ORG_UNIT = COLNAMES_PE['Organizational Unit']
MERCHANT_NAME = COLNAMES_PE['Merchant Short Name']
MAX_DEPTH_OF_DECISION_TREE = 2
MAX_N_FEATURES_OF_DECISION_TREE = 3


class CustomerRCLandBenchmarking(Plugin):

    @staticmethod
    def get_shop_country(name):
        try:
            return str(name).split(' ')[1]
        except IndexError:
            return str(name)

    @staticmethod
    def get_customer_features(transactions):
        # Normalize the set of features to be used in the analysis
        mapping_list = [(['n_transactions'], preprocessing.StandardScaler()),
                        (['monetary_value'], preprocessing.StandardScaler()),
                        (['avg_n_days_between_purchases'], preprocessing.StandardScaler()),
                        (['n_days_since_last_purchase'], preprocessing.StandardScaler()),
                        ('is_periodic_buyer', None)]
        if CARD_CATEGORY in transactions.columns:
            for category in transactions[CARD_CATEGORY].unique():
                if str(category).lower() != 'nan':
                    mapping_list.append(([str(category).lower().replace(' ', '_')], preprocessing.StandardScaler()))
        if CARD_BRAND in transactions.columns:
            for brand in transactions[CARD_BRAND].unique():
                if str(brand).lower() != 'nan':
                    mapping_list.append(([str(brand).lower().replace(' ', '_')], preprocessing.StandardScaler()))
        if PAYMENT_METHOD in transactions.columns:
            for method in transactions[PAYMENT_METHOD].unique():
                if str(method).lower() != 'nan':
                    mapping_list.append(([str(method).lower().replace(' ', '_')], preprocessing.StandardScaler()))
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in weekdays:
            mapping_list.append((['weekday_' + day], preprocessing.StandardScaler()))
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        for month in months:
            mapping_list.append((['transaction_date_month_' + month], preprocessing.StandardScaler()))
        day_period = ['morning', 'noon', 'afternoon', 'evening', 'night']
        for period in day_period:
            mapping_list.append((['dayperiod_' + period], preprocessing.StandardScaler()))
        # month_period = ['jun_jul', 'dec_jan', 'other']
        # for period in month_period:
        #    mapping_list.append((['month_period_' + period], preprocessing.StandardScaler()))
        mapper = DataFrameMapper(mapping_list)
        mapper_y = DataFrameMapper([('retention_status', preprocessing.LabelEncoder())])
        list_features = []
        for name in mapping_list:
            if isinstance(name[0], list):
                list_features.append(name[0][0])
            else:
                list_features.append(name[0])
        return mapper, mapper_y, list_features

    @staticmethod
    def get_elegant_feature_names(features):
        dict_feature_names = {
            'n_transactions': 'Number of purchases',
            'monetary_value': 'Average basket',
            'avg_n_days_between_purchases': 'Avg. number of days between purchases',
            'n_days_since_last_purchase': 'Number of days since last purchase',
            'is_periodic_buyer': 'Customer has a periodic purchase behavior',
            'weekday_monday': 'Number of purchases on Monday',
            'weekday_tuesday': 'Number of purchases on Tuesday',
            'weekday_wednesday': 'Number of purchases on Wednesday',
            'weekday_thursday': 'Number of purchases on Thursday',
            'weekday_friday': 'Number of purchases on Friday',
            'weekday_saturday': 'Number of purchases on Saturday',
            'weekday_sunday': 'Number of purchases on Sunday',
            'transaction_date_month_jan': 'Number of purchases in January',
            'transaction_date_month_feb': 'Number of purchases in February',
            'transaction_date_month_mar': 'Number of purchases in March',
            'transaction_date_month_apr': 'Number of purchases in April',
            'transaction_date_month_may': 'Number of purchases in May',
            'transaction_date_month_jun': 'Number of purchases in June',
            'transaction_date_month_jul': 'Number of purchases in July',
            'transaction_date_month_aug': 'Number of purchases in August',
            'transaction_date_month_sep': 'Number of purchases in September',
            'transaction_date_month_oct': 'Number of purchases in October',
            'transaction_date_month_nov': 'Number of purchases in November',
            'transaction_date_month_dec': 'Number of purchases in December',
            'day_period_morning': 'Number of purchases in the morning (6am to 10am)',
            'day_period_noon': 'Number of purchases around midday (10am to 2pm)',
            'day_period_afternoon': 'Number of purchases in the afternoon (2pm to 6pm)',
            'day_period_evening': 'Number of purchases in the evening (6pm to 10pm)',
            'day_period_night': 'Number of purchases during the night (10pm to 6am)'
            # 'month_period_jun_jul': 'Number of purchases in June-July',
            # 'month_period_dec_jan': 'Number of purchases in Dec-Jan',
            # 'month_period_other': 'Number of purchases out of special periods'
        }
        names = []
        for feature in features:
            if feature in dict_feature_names:
                names.append(dict_feature_names[feature])
            else:
                names.append('Number of purchases with ' + feature.replace('_', ' ').title())
        return names

    @staticmethod
    def is_customer_active(cust):
        return cust['predicted_p_alive'] >= .3

    @staticmethod
    def is_customer_churning(cust):
        return (cust['predicted_p_alive'] >= .3) and (cust['predicted_p_alive'] <= .5)

    @staticmethod
    def is_periodic_buyer(cust):
        return cust['n_transactions'] > 3 \
               & (cust['std_n_days_between_purchases'] <= 0.5 * cust['avg_n_days_between_purchases'])


    def get_retention_status(self, cust):
        if self.is_customer_active(cust):
            if self.is_customer_churning(cust):
                return 'churning'
            else:
                return 'retained'
        else:
            return 'lost'

    def __init__(self, plugin_folder, id, options=None):
        self.plugin_name = "Customer RCL and benchmarking"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle']

    @staticmethod
    def get_weekdays(days):
        if len(days) > 0:
            return [d.weekday() for d in days]
        else:
            return []

    @staticmethod
    def get_list(items):
        return list(items)

    @staticmethod
    def get_period_of_day(hour):
        if 6 <= hour < 10:
            return 0
        elif 10 <= hour < 14:
            return 1
        elif 14 <= hour < 18:
            return 2
        elif 18 <= hour < 22:
            return 3
        else:
            return 4

    def get_period_of_days(self, days):
        if len(days) > 0:
            return [self.get_period_of_day(d.hour) for d in days]
        else:
            return []

    @staticmethod
    def get_month_of_year(dates):
        if len(dates) > 0:
            return [_date.month - 1 for _date in dates]
        else:
            return []

    def process(self, *args, **kwargs):

        results = {'has_data': False}
        args = list(args)
        logger.debug(kwargs)
#checking if the filters are chosen
        if not kwargs or 'options' not in kwargs:
            logger.warning('Fatal Error: Plugin Customer RCL: Options missing')
            return results
        if any(key not in kwargs['options'] for key in ['benchmark_time_window', 'target_time_window']):
            logger.warning('Fatal Error: Plugin Customer RCL: required option missing: '
                            'benchmark_time_window or target_time_window')
            return results
        if any(key not in kwargs['options']['benchmark_time_window'] for key in ['start_point', 'end_point']):
            logger.warning('Fatal Error: Plugin Customer RCL: benchmark_time_window not defined properly')
            return results
        if any(key not in kwargs['options']['target_time_window'] for key in ['start_point', 'end_point']):
            logger.warning('Fatal Error: Plugin Customer RCL: target_time_window not defined properly')
            return results
        if any('type' not in point for point in [kwargs['options']['target_time_window']['start_point'],
                                                 kwargs['options']['target_time_window']['end_point'],
                                                 kwargs['options']['benchmark_time_window']['start_point'],
                                                 kwargs['options']['benchmark_time_window']['end_point']]):
            logger.warning('Fatal Error: Plugin Customer RCL: type property missing in time window definition')
            return results
        for time_window in ['target_time_window', 'benchmark_time_window']:
            for point in ['start_point', 'end_point']:
                if kwargs['options'][time_window][point]['type'] == 'relative' and \
                        any(key not in kwargs['options'][time_window][point] for key in
                            ['reference', 'offset', 'unit']):
                    logger.warning('Fatal Error: Plugin Customer RCL: missing properties for relative time window')
                    return results

        for time_window in ['target_time_window', 'benchmark_time_window']:
            for point in ['start_point', 'end_point']:
                if kwargs['options'][time_window][point]['type'] == 'absolute' and \
                        'datetime' not in kwargs['options'][time_window][point]:
                    logger.warning(
                        'Fatal Error: Plugin Customer RCL: missing datetime property for absolte time window')
                    return results

        location = Location(self.options['assets'])

        if len(args) != 1:
            logger.warning('Fatal Error: Plugin Customer RCL: Transaction data Missing')
            return results

        args = list(args)
        transactions = args[0]

        necessary_keys = [SHOP_NAME, TRANSACTION_DATE, AMOUNT_IN_EUR, CUSTOMER_NAME, CUSTOMER_ID, CARD_CATEGORY,
                          TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]

        if self.options['filter'] == 'account name':
            group_filter = SHOP_NAME
        elif self.options['filter'] == 'org unit':
            group_filter = ORG_UNIT
        elif self.options['filter'] == 'merchant name':
            group_filter = MERCHANT_NAME
        elif self.options['filter'] == 'shop country':
            group_filter = SHOP_COUNTRY
        else:
            logger.warning('unknown filter option')
            return results
        if not all(key in transactions.columns for key in necessary_keys):
            return results

        # -------------------------------------------------------------------------------------------------------------
        # Initialization and basic tests
        # -------------------------------------------------------------------------------------------------------------
#why initialization here? 
        list_columns = necessary_keys
        dtypes = {
            SHOP_NAME: np.str,
            TRANSACTION_DATE: np.str,
            AMOUNT_IN_EUR: np.float,
            CUSTOMER_NAME: np.str,
            CUSTOMER_ID: np.str
        }
        for col in [CUSTOMER_EMAIL, CUSTOMER_CITY, CUSTOMER_COUNTRY, CUSTOMER_CARD_EXPIRY_DATE, CUSTOMER_PAN,
                    CARD_BRAND,
                    PAYMENT_METHOD]:
            if col in transactions.columns:
                list_columns.append(col)
                dtypes[col] = np.str

        # Extract and transform the required transactions for the computations
        transactions = transactions[transactions[TRANSACTION_IS_CAPTURE]][list_columns].copy()

        if group_filter == SHOP_COUNTRY:
            if SHOP_NAME in transactions.columns:
                transactions[SHOP_COUNTRY] = transactions[SHOP_NAME].apply(self.get_shop_country)
            else:
                transactions[SHOP_NAME] = 'Not defined'
                transactions[SHOP_COUNTRY] = 'Unknown'

        logger.debug('list of shop names = {names}'.format(names=transactions[SHOP_NAME].unique()))
        logger.debug('list of filter values = {values}'.format(values=transactions[group_filter].unique()))

        # -------------------------------------------------------------------------------------------------------------
        # Start the analysis
        # -------------------------------------------------------------------------------------------------------------

        if group_filter == SHOP_COUNTRY:
            # Sort the country code by alphabetical order of their name
            _temp_filter_values = pd.Series(transactions[SHOP_COUNTRY].unique())\
                .apply(location.get_country_name).tolist()
            list_of_filter_values = [x
                                     for _, x in sorted(zip(_temp_filter_values, transactions[SHOP_COUNTRY].unique()))]
            list_of_filter_labels = [location.get_country_name(country_code) for country_code in list_of_filter_values]
            list_of_filter_values.append('ALL')
            list_of_filter_labels.append('All countries')
        else:
            _temp_filter_values = pd.Series(transactions[group_filter].unique()).tolist()
            list_of_filter_values = [x
                                     for _, x in sorted(zip(_temp_filter_values, transactions[group_filter].unique()))]
            list_of_filter_labels = [elem for elem in list_of_filter_values]
            list_of_filter_values.append('ALL')
            list_of_filter_labels.append('All ' + self.options['filter'] + 's')

        mapper, mapper_y, list_features = self.get_customer_features(transactions)

        # time_window_1_begin = pd.to_datetime(last_transaction_date - relativedelta(months=int(args[1])))
        # time_window_1_end = pd.to_datetime(last_transaction_date - relativedelta(months=int(args[2])))
        # time_window_2_begin = pd.to_datetime(last_transaction_date - relativedelta(months=int(args[3])))
        # time_window_2_end = pd.to_datetime(last_transaction_date - relativedelta(months=int(args[4])))

        # logger.debug('time_window_1_begin = {}'.format(time_window_1_begin))
        # logger.debug('time_window_1_end = {}'.format(time_window_1_end))
        # logger.debug('time_window_2_begin = {}'.format(time_window_2_begin))
        # logger.debug('time_window_2_end = {}'.format(time_window_2_end))

        time_window_1 = TimeWindow.get_time_window(kwargs['options']['benchmark_time_window'])
        time_window_2 = TimeWindow.get_time_window(kwargs['options']['target_time_window'])
        logger.warning(time_window_1)
        logger.warning(time_window_2)

        results = {
            'has_data': True,
            'n_filter_values': transactions[group_filter].nunique(),
            'filter_value': list_of_filter_values,
            'filter_label': list_of_filter_labels,
            'per_filter_analysis': dict(),
            'graphs': dict()
        }


        for time_window_idx, time_window in enumerate([time_window_1, time_window_2]):

            per_filter_analysis = {
                'period_start': 0,
                'period_end': 0,
                'n_transactions': list(),
                'revenue_this_month': list(),
                'market_share': list(),
                'n_customers': list(),
                'n_onetime_customers': list(),
                'pct_onetime_customers': list(),
                'total_spending_onetime_customers': list(),
                'clv_onetime_customers': list(),
                'pclv_onetime_customers': list(),
                'n_repeating_customers': list(),
                'pct_repeating_customers': list(),
                'total_spending_repeating_customers': list(),
                'clv_repeating_customers': list(),
                'pclv_repeating_customers': list(),
                'n_active_customers': list(),
                'pct_active_customers': list(),
                'total_spending_active_customers': list(),
                'clv_active_customers': list(),
                'pclv_active_customers': list(),
                'n_lost_customers': list(),
                'pct_lost_customers': list(),
                'total_spending_lost_customers': list(),
                'clv_lost_customers': list(),
                'pclv_lost_customers': list(),
                'n_churning_customers': list(),
                'pct_churning_customers': list(),
                'total_spending_churning_customers': list(),
                'clv_churning_customers': list(),
                'pclv_churning_customers': list(),
                'n_retained_customers': list(),
                'pct_retained_customers': list(),
                'total_spending_retained_customers': list(),
                'clv_retained_customers': list(),
                'pclv_retained_customers': list(),
                'decision_tree_filename': list(),
                'decision_tree_accuracy': list(),
                'feature_importances': dict()
            }

            time_filtered_transactions = transactions[transactions[TRANSACTION_DATE] <= time_window[1]]

            total_revenue_this_month = time_filtered_transactions[
                time_filtered_transactions[TRANSACTION_DATE] >= time_window[0]
                ][AMOUNT_IN_EUR].sum()

            per_filter_analysis['period_start'] = time_window[0].strftime('%Y-%m-%d %H:%M:%S')
            per_filter_analysis['period_end'] = time_window[1].strftime('%Y-%m-%d %H:%M:%S')

            logger.debug('Time begin: {time}'.format(time=time_window[0].strftime('%Y-%m-%d %H:%M:%S')))
            logger.debug('Time end: {time}'.format(time=time_window[1].strftime('%Y-%m-%d %H:%M:%S')))
            logger.debug('total_revenue_this_month: {revenue}'.format(revenue=total_revenue_this_month))
            
            #to get an index of an element while iterating over a list (or diferent type of python objects), use enumerate
            for idx_filter_value, filter_value in enumerate(list_of_filter_values):

                logger.debug('Now processing the customers for the filter value: {value}'
                              .format(value=filter_value))
                if filter_value != 'ALL':
                    txs = time_filtered_transactions[time_filtered_transactions[group_filter] == filter_value]
                else:
                    txs = time_filtered_transactions
                n_transactions_in_the_country_this_month = len(txs[txs[TRANSACTION_DATE] >= time_window[0]])
                per_filter_analysis['n_transactions'].append(n_transactions_in_the_country_this_month)
                revenue_in_the_country_this_month = txs[txs[TRANSACTION_DATE] >= time_window[0]][AMOUNT_IN_EUR].sum()
                per_filter_analysis['revenue_this_month'].append(revenue_in_the_country_this_month)
                if total_revenue_this_month > 0:
                    per_filter_analysis['market_share'].append(
                        revenue_in_the_country_this_month / total_revenue_this_month)
                else:
                    per_filter_analysis['market_share'].append(0)
                per_filter_analysis['feature_importances'][idx_filter_value] = {
                    'name': list(),
                    'importance': list(),
                    'std': list()
                }

                if revenue_in_the_country_this_month == 0:
                    print("No revenue for this time period and this filter -> continue")
                    per_filter_analysis['n_transactions'].append(0)
                    per_filter_analysis['revenue_this_month'].append(0)
                    per_filter_analysis['market_share'].append(0)
                    per_filter_analysis['n_customers'].append(0)
                    per_filter_analysis['n_onetime_customers'].append(0)
                    per_filter_analysis['pct_onetime_customers'].append(0)
                    per_filter_analysis['total_spending_onetime_customers'].append(0)
                    per_filter_analysis['clv_onetime_customers'].append(0)
                    per_filter_analysis['pclv_onetime_customers'].append(0)
                    per_filter_analysis['n_repeating_customers'].append(0)
                    per_filter_analysis['pct_repeating_customers'].append(0)
                    per_filter_analysis['total_spending_repeating_customers'].append(0)
                    per_filter_analysis['clv_repeating_customers'].append(0)
                    per_filter_analysis['pclv_repeating_customers'].append(0)
                    per_filter_analysis['n_active_customers'].append(0)
                    per_filter_analysis['pct_active_customers'].append(0)
                    per_filter_analysis['clv_active_customers'].append(0)
                    per_filter_analysis['pclv_active_customers'].append(0)
                    per_filter_analysis['total_spending_active_customers'].append(0)
                    per_filter_analysis['n_lost_customers'].append(0)
                    per_filter_analysis['pct_lost_customers'].append(0)
                    per_filter_analysis['clv_lost_customers'].append(0)
                    per_filter_analysis['pclv_lost_customers'].append(0)
                    per_filter_analysis['total_spending_lost_customers'].append(0)
                    per_filter_analysis['n_churning_customers'].append(0)
                    per_filter_analysis['pct_churning_customers'].append(0)
                    per_filter_analysis['clv_churning_customers'].append(0)
                    per_filter_analysis['pclv_churning_customers'].append(0)
                    per_filter_analysis['total_spending_churning_customers'].append(0)
                    per_filter_analysis['n_retained_customers'].append(0)
                    per_filter_analysis['pct_retained_customers'].append(0)
                    per_filter_analysis['clv_retained_customers'].append(0)
                    per_filter_analysis['pclv_retained_customers'].append(0)
                    per_filter_analysis['total_spending_retained_customers'].append(0)
                    features_names = sorted(self.get_elegant_feature_names(list_features))
                    for feature in features_names:
                        per_filter_analysis['feature_importances'][idx_filter_value]['name'].append(feature)
                        per_filter_analysis['feature_importances'][idx_filter_value]['importance'].append(0)
                        per_filter_analysis['feature_importances'][idx_filter_value]['std'].append(0)
                    per_filter_analysis['decision_tree_filename'].append('')
                    per_filter_analysis['decision_tree_accuracy'].append(0)
                    continue

                logger.debug('Identify the customers')
                customers, txs = identify_customers(txs)
                logger.debug('Add the customer features')
                customers = add_feature(customers, txs, Feature.ALL, end_period=time_window[1])
                n_customers = len(customers)

                if n_customers == 0:
                    print("No customers -> continue")
                    per_filter_analysis['n_transactions'].append(0)
                    per_filter_analysis['revenue_this_month'].append(0)
                    per_filter_analysis['market_share'].append(0)
                    per_filter_analysis['n_customers'].append(0)
                    per_filter_analysis['n_onetime_customers'].append(0)
                    per_filter_analysis['pct_onetime_customers'].append(0)
                    per_filter_analysis['total_spending_onetime_customers'].append(0)
                    per_filter_analysis['clv_onetime_customers'].append(0)
                    per_filter_analysis['pclv_onetime_customers'].append(0)
                    per_filter_analysis['n_repeating_customers'].append(0)
                    per_filter_analysis['pct_repeating_customers'].append(0)
                    per_filter_analysis['total_spending_repeating_customers'].append(0)
                    per_filter_analysis['clv_repeating_customers'].append(0)
                    per_filter_analysis['pclv_repeating_customers'].append(0)
                    per_filter_analysis['n_active_customers'].append(0)
                    per_filter_analysis['pct_active_customers'].append(0)
                    per_filter_analysis['clv_active_customers'].append(0)
                    per_filter_analysis['pclv_active_customers'].append(0)
                    per_filter_analysis['total_spending_active_customers'].append(0)
                    per_filter_analysis['n_lost_customers'].append(0)
                    per_filter_analysis['pct_lost_customers'].append(0)
                    per_filter_analysis['clv_lost_customers'].append(0)
                    per_filter_analysis['pclv_lost_customers'].append(0)
                    per_filter_analysis['total_spending_lost_customers'].append(0)
                    per_filter_analysis['n_churning_customers'].append(0)
                    per_filter_analysis['pct_churning_customers'].append(0)
                    per_filter_analysis['clv_churning_customers'].append(0)
                    per_filter_analysis['pclv_churning_customers'].append(0)
                    per_filter_analysis['total_spending_churning_customers'].append(0)
                    per_filter_analysis['n_retained_customers'].append(0)
                    per_filter_analysis['pct_retained_customers'].append(0)
                    per_filter_analysis['clv_retained_customers'].append(0)
                    per_filter_analysis['pclv_retained_customers'].append(0)
                    per_filter_analysis['total_spending_retained_customers'].append(0)
                    features_names = sorted(self.get_elegant_feature_names(list_features))
                    for feature in features_names:
                        per_filter_analysis['feature_importances'][idx_filter_value]['name'].append(feature)
                        per_filter_analysis['feature_importances'][idx_filter_value]['importance'].append(0)
                        per_filter_analysis['feature_importances'][idx_filter_value]['std'].append(0)
                    per_filter_analysis['decision_tree_filename'].append('')
                    per_filter_analysis['decision_tree_accuracy'].append(0)
                    continue

                per_filter_analysis['n_customers'].append(n_customers)

                # -----------------------------------------------------------------------------------------------------
                # Identify card categories and brand
                # -----------------------------------------------------------------------------------------------------

                temp = txs.groupby(CUSTOMER_ID).agg({
                    CARD_CATEGORY: self.get_list,
                    CARD_BRAND: self.get_list,
                    PAYMENT_METHOD: self.get_list
                })
                temp.reset_index(inplace=True)
                customers = pd.merge(customers, temp, on=CUSTOMER_ID, how='left')
                del temp
                customers = flatten_column_values(customers,
                                                  CARD_CATEGORY,
                                                  list_values=transactions[CARD_CATEGORY].unique())
                customers = flatten_column_values(customers,
                                                  CARD_BRAND,
                                                  list_values=transactions[CARD_BRAND].unique())
                customers = flatten_column_values(customers,
                                                  PAYMENT_METHOD,
                                                  list_values=transactions[PAYMENT_METHOD].unique())

                # Flatten the transaction weekdays
                temp = txs.groupby(CUSTOMER_ID).agg({TRANSACTION_DATE: self.get_weekdays})
                temp.rename(columns={TRANSACTION_DATE: 'weekdays'}, inplace=True)
                temp.reset_index(inplace=True)
                customers = pd.merge(customers, temp, on=CUSTOMER_ID, how='left')
                del temp
                #count for each weekday
                for i, day in enumerate(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                    customers['weekday_' + day] = customers['weekdays'].apply(lambda days: days.count(i))
                customers.drop('weekdays', axis=1, inplace=True)

                # Flatten the transaction months
                temp = txs.groupby(CUSTOMER_ID).agg({TRANSACTION_DATE: self.get_month_of_year})
                temp.rename(columns={TRANSACTION_DATE: 'transaction_date_month'}, inplace=True)
                temp.reset_index(inplace=True)
                customers = pd.merge(customers, temp, on=CUSTOMER_ID, how='left')
                del temp
                for i, month in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul',
                                           'aug', 'sep', 'oct', 'nov', 'dec']):
                    customers['transaction_date_month_' + month] = customers['transaction_date_month'].apply(
                        lambda months: months.count(i))
                customers.drop('transaction_date_month', axis=1, inplace=True)

                # Flatten the transaction period of days

                temp = txs.groupby(CUSTOMER_ID).agg({TRANSACTION_DATE: self.get_period_of_days})
                temp.rename(columns={TRANSACTION_DATE: 'dayperiod'}, inplace=True)
                temp.reset_index(inplace=True)
                customers = pd.merge(customers, temp, on=CUSTOMER_ID, how='left')
                del temp

                for i, period in enumerate(['morning', 'noon', 'afternoon', 'evening', 'night']):
                    customers['dayperiod_' + period] = customers['dayperiod'].apply(lambda days: days.count(i))
                customers.drop('dayperiod', axis=1, inplace=True)


                customers['is_periodic_buyer'] = None
                if n_customers > 0:
                    customers['is_periodic_buyer'] = customers.apply(self.is_periodic_buyer, axis=1)

                # Fit a BGF model
                bgf = BetaGeoFitter(penalizer_coef=0.0)
                bgf.fit(customers['frequency'], customers['recency'], customers['T'], maxiter=10000, tol=1e-6,
                        verbose=True)
                logger.debug(bgf)
                # r, alpha, a, b = bgf._unload_params('r', 'alpha', 'a', 'b')
                customers['predicted_p_alive'] = bgf.conditional_probability_alive(customers['frequency'],
                                                                                   customers['recency'],
                                                                                   customers['T'])
                customers['predicted_F'] = bgf.conditional_expected_number_of_purchases_up_to_time(365,
                                                                                                   customers[
                                                                                                       'frequency'],
                                                                                                   customers['recency'],
                                                                                                   customers['T'])
                customers['predicted_F'].fillna(0, inplace=True)
                customers['predicted_F_rounded'] = None
                customers['is_active'] = None
                customers['is_churning'] = None
                if n_customers > 0:
                    customers['predicted_F_rounded'] = customers['predicted_F'].apply(lambda x: round(x))
                    customers['is_active'] = customers.apply(self.is_customer_active, axis=1)
                    customers['is_churning'] = customers.apply(self.is_customer_churning, axis=1)

                # ----------------------------------------------------------------------------------------------------
                # Count the one-time customers and the repeating customers
                # ----------------------------------------------------------------------------------------------------

                onetime_cust = customers[customers['n_transactions'] == 1].index.values
                repeat_cust = customers[customers['n_transactions'] > 1].index.values

                logger.debug(customers.loc[repeat_cust, ['monetary_value', 'frequency']].corr())
                # fitting gg model
                ggf = GammaGammaFitter(penalizer_coef=0)
                ggf.fit(customers.loc[repeat_cust, 'frequency'], customers.loc[repeat_cust, 'monetary_value'],
                        verbose=True)
                logger.debug(ggf)

                p, q, v = ggf._unload_params('p', 'q', 'v')
                customers['predicted_M_avg'] = (p * v) / (q - 1)
                customers.loc[
                    customers['n_transactions'] > 1, 'predicted_M_avg'] = ggf.conditional_expected_average_profit(
                    customers.loc[repeat_cust, 'frequency'],
                    customers.loc[repeat_cust, 'monetary_value'])
                customers['CLV'] = customers['predicted_F'] * customers['predicted_M_avg']
                customers['pCLV'] = customers['predicted_p_alive'] * customers['predicted_F'] * customers[
                    'predicted_M_avg']

                customers['retention_status'] = None
                if n_customers > 0:
                    customers['retention_status'] = customers.apply(self.get_retention_status, axis=1)

                n_onetime_customers = len(onetime_cust)
                n_repeating_customers = len(repeat_cust)

                per_filter_analysis['n_onetime_customers'].append(n_onetime_customers)
                if n_customers > 0:
                    per_filter_analysis['pct_onetime_customers'].append(n_onetime_customers / n_customers)
                else:
                    per_filter_analysis['pct_onetime_customers'].append(0)
                per_filter_analysis['clv_onetime_customers'].append(customers.loc[onetime_cust, 'CLV'].sum())
                per_filter_analysis['pclv_onetime_customers'].append(customers.loc[onetime_cust, 'pCLV'].sum())
                per_filter_analysis['total_spending_onetime_customers'].append(
                    customers.loc[onetime_cust, 'total_spending'].sum())

                per_filter_analysis['n_repeating_customers'].append(n_repeating_customers)
                if n_customers > 0:
                    per_filter_analysis['pct_repeating_customers'].append(n_repeating_customers / n_customers)
                else:
                    per_filter_analysis['pct_repeating_customers'].append(0)
                per_filter_analysis['clv_repeating_customers'].append(customers.loc[repeat_cust, 'CLV'].sum())
                per_filter_analysis['pclv_repeating_customers'].append(customers.loc[repeat_cust, 'pCLV'].sum())
                per_filter_analysis['total_spending_repeating_customers'].append(
                    customers.loc[repeat_cust, 'total_spending'].sum())

                if n_repeating_customers == 0:
                    per_filter_analysis['n_active_customers'].append(0)
                    per_filter_analysis['pct_active_customers'].append(0)
                    per_filter_analysis['clv_active_customers'].append(0)
                    per_filter_analysis['pclv_active_customers'].append(0)
                    per_filter_analysis['total_spending_active_customers'].append(0)
                    per_filter_analysis['n_lost_customers'].append(0)
                    per_filter_analysis['pct_lost_customers'].append(0)
                    per_filter_analysis['clv_lost_customers'].append(0)
                    per_filter_analysis['pclv_lost_customers'].append(0)
                    per_filter_analysis['total_spending_lost_customers'].append(0)
                    per_filter_analysis['n_churning_customers'].append(0)
                    per_filter_analysis['pct_churning_customers'].append(0)
                    per_filter_analysis['clv_churning_customers'].append(0)
                    per_filter_analysis['pclv_churning_customers'].append(0)
                    per_filter_analysis['total_spending_churning_customers'].append(0)
                    per_filter_analysis['n_retained_customers'].append(0)
                    per_filter_analysis['pct_retained_customers'].append(0)
                    per_filter_analysis['clv_retained_customers'].append(0)
                    per_filter_analysis['pclv_retained_customers'].append(0)
                    per_filter_analysis['total_spending_retained_customers'].append(0)
                    features_names = sorted(self.get_elegant_feature_names(list_features))
                    for feature in features_names:
                        per_filter_analysis['feature_importances'][idx_filter_value]['name'].append(feature)
                        per_filter_analysis['feature_importances'][idx_filter_value]['importance'].append(0)
                        per_filter_analysis['feature_importances'][idx_filter_value]['std'].append(0)
                    per_filter_analysis['decision_tree_filename'].append('')
                    per_filter_analysis['decision_tree_accuracy'].append(0)
                    continue

                # -----------------------------------------------------------------------------------------------------
                # Deal with repeateing customers
                # -----------------------------------------------------------------------------------------------------

                active_cust = customers[(customers['n_transactions'] > 1) & customers['is_active']].index.values
                n_active_customers = len(active_cust)
                lost_cust = customers[(customers['n_transactions'] > 1) & (~customers['is_active'])].index.values
                n_lost_customers = len(lost_cust)

                per_filter_analysis['n_active_customers'].append(n_active_customers)
                if n_customers > 0:
                    per_filter_analysis['pct_active_customers'].append(n_active_customers / n_customers)
                else:
                    per_filter_analysis['pct_active_customers'].append(0)
                per_filter_analysis['clv_active_customers'].append(customers.loc[active_cust, 'CLV'].sum())
                per_filter_analysis['pclv_active_customers'].append(customers.loc[active_cust, 'pCLV'].sum())
                per_filter_analysis['total_spending_active_customers'].append(
                    customers.loc[active_cust, 'total_spending'].sum())

                per_filter_analysis['n_lost_customers'].append(n_lost_customers)
                if n_customers > 0:
                    per_filter_analysis['pct_lost_customers'].append(n_lost_customers / n_customers)
                else:
                    per_filter_analysis['pct_lost_customers'].append(0)
                per_filter_analysis['clv_lost_customers'].append(customers.loc[lost_cust, 'CLV'].sum())
                per_filter_analysis['pclv_lost_customers'].append(customers.loc[lost_cust, 'pCLV'].sum())
                per_filter_analysis['total_spending_lost_customers'].append(
                    customers.loc[lost_cust, 'total_spending'].sum())

                if n_active_customers == 0:
                    per_filter_analysis['n_churning_customers'].append(0)
                    per_filter_analysis['pct_churning_customers'].append(0)
                    per_filter_analysis['clv_churning_customers'].append(0)
                    per_filter_analysis['pclv_churning_customers'].append(0)
                    per_filter_analysis['total_spending_churning_customers'].append(0)
                    per_filter_analysis['n_retained_customers'].append(0)
                    per_filter_analysis['pct_retained_customers'].append(0)
                    per_filter_analysis['clv_retained_customers'].append(0)
                    per_filter_analysis['pclv_retained_customers'].append(0)
                    per_filter_analysis['total_spending_retained_customers'].append(0)
                    features_names = sorted(self.get_elegant_feature_names(list_features))
                    for feature in features_names:
                        per_filter_analysis['feature_importances'][idx_filter_value]['name'].append(feature)
                        per_filter_analysis['feature_importances'][idx_filter_value]['importance'].append(0)
                        per_filter_analysis['feature_importances'][idx_filter_value]['std'].append(0)
                    per_filter_analysis['decision_tree_filename'].append('')
                    per_filter_analysis['decision_tree_accuracy'].append(0)
                    continue

                customers.loc[active_cust, 'is_churning'] = customers.loc[active_cust, :] \
                    .apply(self.is_customer_churning, axis=1)
                churning_cust = customers[(customers['n_transactions'] > 1)
                                          & customers['is_active'] & customers['is_churning']].index.values
                n_churning_customers = len(churning_cust)
                retained_cust = customers[(customers['n_transactions'] > 1)
                                          & customers['is_active'] & (~customers['is_churning'])].index.values
                n_retained_customers = len(retained_cust)

                per_filter_analysis['n_churning_customers'].append(n_churning_customers)
                #calculating percentage of churning customers
                if n_customers > 0:
                    per_filter_analysis['pct_churning_customers'].append(n_churning_customers / n_customers)
                else:
                    per_filter_analysis['pct_churning_customers'].append(0)
                per_filter_analysis['clv_churning_customers'].append(customers.loc[churning_cust, 'CLV'].sum())
                per_filter_analysis['pclv_churning_customers'].append(customers.loc[churning_cust, 'pCLV'].sum())
                per_filter_analysis['total_spending_churning_customers'].append(
                    customers.loc[churning_cust, 'total_spending'].sum())

                #append number of retained customers 
                per_filter_analysis['n_retained_customers'].append(n_retained_customers)
                if n_customers > 0:
                    per_filter_analysis['pct_retained_customers'].append(n_retained_customers / n_customers)
                else:
                    per_filter_analysis['pct_retained_customers'].append(0)
                per_filter_analysis['clv_retained_customers'].append(customers.loc[retained_cust, 'CLV'].sum())
                per_filter_analysis['pclv_retained_customers'].append(customers.loc[retained_cust, 'pCLV'].sum())
                per_filter_analysis['total_spending_retained_customers'].append(
                    customers.loc[retained_cust, 'total_spending'].sum())

                logger.debug("Finished RCL Process for"+str(filter_value))

            results['per_filter_analysis']['time_window_' + str(time_window_idx)] = per_filter_analysis
        process_output_file = join(self.process_output_folder, 'out.pickle')
        logger.debug("Writing pickle")
        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(results, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return results

    def plot(self, *args, **kwargs):
        pass

    def report(self, report, styles, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')
        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        data_list = list()
        for i in range(data['n_filter_values'] + 1):

            shop_country_name = data['filter_label'][i]
            company_share_0 = 100 * data['per_filter_analysis']['time_window_0']['market_share'][i]
            company_share_1 = 100 * data['per_filter_analysis']['time_window_1']['market_share'][i]
            company_share_pct_change = np.nan
            if company_share_0 > 0:
                company_share_pct_change = 100 * (company_share_1 - company_share_0) / company_share_0

            n_transactions_0 = data['per_filter_analysis']['time_window_0']['n_transactions'][i]
            n_transactions_1 = data['per_filter_analysis']['time_window_1']['n_transactions'][i]
            n_transactions_pct_change = np.nan
            if n_transactions_0 > 0:
                n_transactions_pct_change = 100 * (n_transactions_1 - n_transactions_0) / n_transactions_0

            revenue_this_month_0 = int(data['per_filter_analysis']['time_window_0']['revenue_this_month'][i])
            revenue_this_month_1 = int(data['per_filter_analysis']['time_window_1']['revenue_this_month'][i])
            revenue_this_month_pct_change = np.nan
            if revenue_this_month_0 > 0:
                revenue_this_month_pct_change = 100 * (revenue_this_month_1 - revenue_this_month_0) / revenue_this_month_0

            pct_onetime_customers_0 = 100 * data['per_filter_analysis']['time_window_0']['pct_onetime_customers'][i]
            pct_onetime_customers_1 = 100 * data['per_filter_analysis']['time_window_1']['pct_onetime_customers'][i]
            pct_onetime_customers_pct_change = np.nan
            if pct_onetime_customers_0 > 0:
                pct_onetime_customers_pct_change = 100 * (pct_onetime_customers_1 - pct_onetime_customers_0) / pct_onetime_customers_0

            pct_retained_customers_0 = 100 * data['per_filter_analysis']['time_window_0']['pct_retained_customers'][i]
            pct_retained_customers_1 = 100 * data['per_filter_analysis']['time_window_1']['pct_retained_customers'][i]
            pct_retained_customers_pct_change = np.nan
            if pct_retained_customers_0 > 0:
                pct_retained_customers_pct_change = 100 * (pct_retained_customers_1 - pct_retained_customers_0) / pct_retained_customers_0

            pct_churning_customers_0 =  100 * data['per_filter_analysis']['time_window_0']['pct_churning_customers'][i]
            pct_churning_customers_1 =  100 * data['per_filter_analysis']['time_window_1']['pct_churning_customers'][i]
            pct_churning_customers_pct_change = np.nan
            if pct_churning_customers_0 > 0:
                pct_churning_customers_pct_change = 100 * (pct_churning_customers_1 - pct_churning_customers_0) / pct_churning_customers_0

            pct_lost_customers_0 = 100 * data['per_filter_analysis']['time_window_0']['pct_lost_customers'][i]
            pct_lost_customers_1 = 100 * data['per_filter_analysis']['time_window_1']['pct_lost_customers'][i]
            pct_lost_customers_pct_change = np.nan
            if pct_lost_customers_0 > 0:
                pct_lost_customers_pct_change = 100 * (pct_lost_customers_1 - pct_lost_customers_0) / pct_lost_customers_0

            data_list.append([Paragraph(shop_country_name.replace(" ", "<br/>"), style=styles['RCL_Table-White']),
                              Paragraph('{:.2f}%'.format(company_share_1), style=styles['RCL_Table-Night_Blue']) ,
                              Paragraph('{:.2f}%'.format(company_share_pct_change),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:,}'.format(n_transactions_1),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(n_transactions_pct_change),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:,}€'.format(revenue_this_month_1),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(revenue_this_month_pct_change),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_onetime_customers_1),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_onetime_customers_pct_change),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_retained_customers_1),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_retained_customers_pct_change),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_churning_customers_1),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_churning_customers_pct_change),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_lost_customers_1),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(pct_lost_customers_pct_change),
                                        style=styles['RCL_Table-Night_Blue'])
                              ])
        table_data = [[Paragraph('Shop<br/>countries', style=styles['RCL_Table-White']),
                       Paragraph('Company<br/>Share', style=styles['RCL_Table-White']),
                       Paragraph('\u0394', style=styles['RCL_Table-White']),
                       Paragraph('#<br/>Transactions', style=styles['RCL_Table-White']),
                       Paragraph('\u0394', style=styles['RCL_Table-White']),
                       Paragraph('Gross<br/>sales', style=styles['RCL_Table-White']),
                       Paragraph('\u0394', style=styles['RCL_Table-White']),
                       Paragraph('One-Time customers', style=styles['RCL_Table-White']),
                       '',
                       Paragraph('Retained customers', style=styles['RCL_Table-Green']), '',
                       Paragraph('Churning customers', style=styles['RCL_Table-Yellow']), '',
                       Paragraph('Lost customers', style=styles['RCL_Table-Red']), '']] + \
                     [['', '', '', '', '', '', '',
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('\u0394', style=styles['RCL_Table-White']),
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('\u0394', style=styles['RCL_Table-White']),
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('\u0394', style=styles['RCL_Table-White']),
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('\u0394', style=styles['RCL_Table-White'])]] + data_list

        col_widths = [40, 35, 30, 41, 30, 39, 30, 48, 30, 48, 30, 48, 32, 48, 34]
        t = Table(data=table_data, splitByRow=True, colWidths=col_widths)
        t.setStyle(
            [('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey), ('BOX', (1, 2), (-1, -1), 0.25, colors.lightgrey),
             ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)), ('SPAN', (2, 0), (2, 1)), ('SPAN', (3, 0), (3, 1)),
             ('SPAN', (4, 0), (4, 1)), ('SPAN', (5, 0), (5, 1)), ('SPAN', (6, 0), (6, 1)),
             ('SPAN', (7, 0), (8, 0)), ('SPAN', (9, 0), (10, 0)), ('SPAN', (11, 0), (12, 0)),
             ('SPAN', (13, 0), (14, 0)), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('NOSPLIT', (0, -1), (0, -1)),
             ('INNERGRID', (0, 0), (-1, 1), 0.25, colors.white),
             ('BACKGROUND', (0, 0), (6, 1), kwargs['cmap']['colors']['night blue']),
             ('BACKGROUND', (7, 1), (-1, 1), kwargs['cmap']['colors']['night blue']),
             ('BACKGROUND', (7, 0), (8, 0), kwargs['cmap']['colors']['accent1']),
             ('BACKGROUND', (9, 0), (10, 0), '#c6efce'),
             ('BACKGROUND', (11, 0), (12, 0), '#fffda6'),
             ('BACKGROUND', (-2, 0), (-1, 0), kwargs['cmap']['colors']['accent5']),
             ('BACKGROUND', (0, 2), (0, -1), kwargs['cmap']['colors']['night blue'])
             ])

        Report.draw_text_right(report, 'COUNTRY BENCHMARKING', styles['Heading2-White'])

        Report.draw_text_right(report, 'Time Period Comparison: {0} against {1}'.format(
            datetime.strptime(data['per_filter_analysis']['time_window_1']['period_start'],
                              '%Y-%m-%d %H:%M:%S').strftime('%B %Y'),
            datetime.strptime(data['per_filter_analysis']['time_window_0']['period_end'],
                              '%Y-%m-%d %H:%M:%S').strftime('%B %Y')), styles['Heading3-White'])

        Report.draw_text_right(doc=report,
                                text='This table shows a comparison of different country shops values from one period ' \
                                     'against an earlier one.<br/><br/>' \
                                     'The first and second column show respectively the market share in each country ' \
                                     'at the end of the second period and the difference to the first one.<br/><br/> ' \
                                     'The third and fourth column show the number of executed transactions per ' \
                                     'country during the second period and the difference to the first one.<br/><br/>'
                                     'The fifth and sixth column show respectively the amount of gross sales achieved per ' \
                                     'country during the second period and the difference to the first one. <br/><br/>' \
                                     'In the next columns, the customers have been divided into four categories: <br/>' \
                                     '- One-time customers<br/>' \
                                     '- Retained customers<br/>' \
                                     '- Churning customers<br/>' \
                                     '- Lost customers<br/>', style=styles['Normal-White'])

        Report.draw_table_left(doc=report, table=t)

        data_list = list()
        for i in range(data['n_filter_values'] + 1):
            data_list.append([Paragraph(data['filter_label'][i].replace(" ", "\n"), style=styles['RCL_Table-White']),
                              Paragraph('{:,}'.format(data['per_filter_analysis']['time_window_1']['n_customers'][i]),
                                        style=styles['RCL_Table-Night_Blue']),
                              Paragraph('{:.2f}%'.format(
                                  100 * data['per_filter_analysis']['time_window_1']['pct_onetime_customers'][i]),
                                  style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:,}€'.format(
                                  int(data['per_filter_analysis']['time_window_1']
                                      ['total_spending_onetime_customers'][i])), style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:.2f}%'.format(
                                  100 * data['per_filter_analysis']['time_window_1']['pct_retained_customers'][i]),
                                  style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:,}€'.format(
                                  int(data['per_filter_analysis']['time_window_1']
                                  ['total_spending_retained_customers'][i])
                                  ), style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:,}€'.format(
                                  int(data['per_filter_analysis']['time_window_1']['pclv_retained_customers'][i])),
                                  style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:.2f}%'.format(
                                  100 * data['per_filter_analysis']['time_window_1']['pct_churning_customers'][i]),
                                  style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:,}€'.format(
                                  int(data['per_filter_analysis']['time_window_1']
                                      ['total_spending_churning_customers'][i])
                              ), style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:,}€'.format(
                                  int(data['per_filter_analysis']['time_window_1']['pclv_churning_customers'][i])),
                                  style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:.2f}%'.format(
                                  100 * data['per_filter_analysis']['time_window_1']['pct_lost_customers'][i]),
                                  style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:,}€'.format(
                                  int(data['per_filter_analysis']['time_window_1']
                                  ['total_spending_lost_customers'][i])), style=styles['RCL_Table-Night_Blue']),
                             Paragraph('{:,}€'.format(
                                  int(data['per_filter_analysis']['time_window_1']['pclv_lost_customers'][i])),
                                  style=styles['RCL_Table-Night_Blue'])
                              ])

        table_data = [[Paragraph('Shop<br/>countries', style=styles['RCL_Table-White']),
                       Paragraph('#<br/>Customers', style=styles['RCL_Table-White']),
                       Paragraph('One-Time customers', style=styles['RCL_Table-White']),
                       '',
                       Paragraph('Retained customers', style=styles['RCL_Table-Green']), '', '',
                       Paragraph('Churning customers', style=styles['RCL_Table-Yellow']), '', '',
                       Paragraph('Lost customers', style=styles['RCL_Table-Red']), '', '']] + \
                     [['', '',
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('Gross Sales', style=styles['RCL_Table-White']),
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('Gross Sales', style=styles['RCL_Table-White']),
                       Paragraph('Predicted', style=styles['RCL_Table-White']),
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('Gross Sales', style=styles['RCL_Table-White']),
                       Paragraph('Predicted', style=styles['RCL_Table-White']),
                       Paragraph('% of customers', style=styles['RCL_Table-White']),
                       Paragraph('Gross Sales', style=styles['RCL_Table-White']),
                       Paragraph('Predicted', style=styles['RCL_Table-White'])]] + data_list

        col_widths = [46, 46, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43, 43]
        t = Table(data=table_data, splitByRow=True, colWidths=col_widths)

        t.setStyle(
            [('INNERGRID', (0, 0), (-1, -1), 0.25, colors.lightgrey), ('BOX', (1, 2), (-1, -1), 0.25, colors.lightgrey),
             ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)), ('SPAN', (2, 0), (3, 0)), ('SPAN', (4, 0), (6, 0)),
             ('SPAN', (7, 0), (9, 0)), ('SPAN', (10, 0), (12, 0)),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('BACKGROUND', (0, 2), (0, -1), kwargs['cmap']['colors']['night blue']),
             ('INNERGRID', (0, 2), (0, -1), 0.25, colors.white),
             ('BACKGROUND', (0, 1), (-1, 1), kwargs['cmap']['colors']['night blue']),
             ('INNERGRID', (0, 1), (-1, 1), 0.25, colors.white),
             ('BACKGROUND', (0, 0), (1, 0), kwargs['cmap']['colors']['night blue']),
             ('INNERGRID', (0, 0), (1, 0), 0.25, colors.white),
             ('BACKGROUND', (2, 0), (3, 0), kwargs['cmap']['colors']['accent1']),
             ('BACKGROUND', (4, 0), (6, 0), '#c6efce'),
             ('BACKGROUND', (7, 0), (9, 0), '#fffda6'),
             ('BACKGROUND', (10, 0), (12, 0), kwargs['cmap']['colors']['accent5']),
             ('NOSPLIT', (0, -1), (0, -1)), ('FONTSIZE', (0, 0), (-1, -1), 5)])

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(report, 'CUSTOMER SEGMENTATION PER COUNTRY', styles['Heading2-White'])

        start_month = datetime.strptime(data['per_filter_analysis']['time_window_1']['period_start'],
                              '%Y-%m-%d %H:%M:%S').strftime('%b %Y')

        end_month = datetime.strptime(data['per_filter_analysis']['time_window_1']['period_end'],
                              '%Y-%m-%d %H:%M:%S').strftime('%b %Y')

        Report.draw_text_right(report, text='Time Period Analysis: ' + start_month + (' to ' + end_month if start_month != end_month else ''), style=styles['Heading3-White'])

        """Report.draw_text_right(report, '{0} to {1}'.format(
            datetime.strptime(data['per_filter_analysis']['time_window_1']['period_start'],
                              '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y'),
            datetime.strptime(data['per_filter_analysis']['time_window_1']['period_end'],
                              '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y')), style=styles['Heading4-White'])"""

        Report.draw_text_right(doc=report, text= 'This table shows customer categories for different country shops. '
                                                 'The first column shows the total number of customers in each country. <br/>'
                                                 'The customers have been divided into four categories: <br/>'
                                                 '- One-time customers<br/>' \
                                                 '- Retained customers<br/>' \
                                                 '- Churning customers<br/>' \
                                                 '- Lost customers<br/>'
                                                 'For each country, a percentage of customers in each of these '
                                                 'categories is shown, together with the gross sales that they '
                                                 'generated and the gross sales that they are expected to generate '
                                                 'in the next 365 days.', style=styles['Normal-White'])

        Report.draw_table_left(doc=report, table=t)
        data_list = list()
        data_list.append(['Features'] + [x.replace(" ", "\n") for x in data['filter_label']])
        feature_names = data['per_filter_analysis']['time_window_1']['feature_importances'][0]['name']
        for i in range(len(feature_names)):
            temp_list = list()
            temp_list.append(feature_names[i])
            for j in range(data['n_filter_values'] + 1):
                temp_list.append(
                    '{:.2f}%'.format(
                        100 * data['per_filter_analysis']['time_window_1']['feature_importances'][j]['importance'][i]))
            data_list.append(temp_list)

        table_data = data_list

        t = Table(data=table_data, splitByRow=True, repeatRows=1)

        t.setStyle(
            [('BACKGROUND', (1, 0), (-1, 0), '#06b89d'),
             ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
             ('BACKGROUND', (0, 0), (0, 0), '#002846'),
             ('INNERGRID', (0, 0), (-1, 0), 0.25, colors.white),
             ('INNERGRID', (0, 1), (-1, -1), 0.25, colors.lightgrey),
             ('BOX', (0, 1), (-1, -1), 0.25, colors.lightgrey),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('NOSPLIT', (0, -1), (0, -1)), ('FONTSIZE', (0, 0), (-1, -1), 4)])

        if False:
            report.append(Paragraph('Features Breakdown of every customer', style=styles['Heading3-NightBlue']))
            report.append(Spacer(1, 20))
            report.append(t)
            report.append(Spacer(1, 20))
            report.append(Paragraph('Various features are derived from the customers of each country '
                                    '(based on the country where they shop and not the country where they come from, '
                                    'which is not known for many customers). We then compute the correlation between each '
                                    'feature and the customer categorization (retaind, churning, or lost). The two most '
                                    'important features are highlighted in green and used for creating the decision trees '
                                    'of each country in the sheet ‘Customer categories’.',
                                    style=styles['Normal']))



