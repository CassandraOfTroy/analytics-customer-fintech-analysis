# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 12:55:03 2019

@author: marina.tosic
"""

from wepair.plugins.plugin import Plugin
from ...globals import COLNAMES_PE
from os.path import join
import pandas as pd
import pickle
import inspect
from reportlab.platypus import Spacer, Image
from ...utils.report import Report
import plotly.io as pio
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
SHOP_NAME = COLNAMES_PE['Merchant Account Short Name']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
TRANSACTION_REF_ID = COLNAMES_PE['Transaction Reference ID']
SHOP_COUNTRY_CODE_ISO2 = 'ISO2'
SHOP_COUNTRY_NAME = 'Country Name'
ORG_UNIT = COLNAMES_PE['Organizational Unit']
MERCHANT_NAME = COLNAMES_PE['Merchant Short Name']


class SalesTopRank(Plugin):

    @staticmethod
    def get_shop_country(name):
        try:
            return str(name).split(' ')[1]
        except IndexError:
            return str(name)

    def __init__(self, plugin_folder, id, options = None):
        self.plugin_name = "Sales Top Rank"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle']

    def process(self, *args, **kwargs):

        sales_per_shop = {'has_data': False}

        args = list(args)
        logger.debug(kwargs)

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin Sales Top Ranking: Transaction data Missing')
            return sales_per_shop

        necessary_keys = [SHOP_NAME, ORG_UNIT, MERCHANT_NAME, AMOUNT_IN_EUR, TRANSACTION_REF_ID, TRANSACTION_IS_CAPTURE,
                          TRANSACTION_IS_RETURN]

        transactions = args[0]
        if self.options['filter'] == 'account name':
            group_filter = SHOP_NAME
        elif self.options['filter'] == 'org unit':
            group_filter = ORG_UNIT
        elif self.options['filter'] == 'merchant name':
            group_filter = MERCHANT_NAME
        else:
            logger.warning('unknown filter option')
            return sales_per_shop
        if not all(key in transactions.columns for key in necessary_keys):
            return sales_per_shop

        sales_per_shop = {'has_data': True}

        # Extract the data of interest
        columns_to_keep = [TRANSACTION_DATE, SHOP_NAME, ORG_UNIT, MERCHANT_NAME, AMOUNT_IN_EUR, TRANSACTION_REF_ID,
                           TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]
        if TRANSACTION_DATE not in transactions.columns:
            logger.warning('{fct_name}: There is no column TRANSACTION_DATE. '
                            'Plotting results for the net sales will not be possible.'
                            .format(fct_name=inspect.stack()[0][3]))
            columns_to_keep.remove(TRANSACTION_DATE)
        transactions = transactions[columns_to_keep]

        # Split the transaction set into gross sales and sales returns
        gross_sales_txs = transactions[transactions[TRANSACTION_IS_CAPTURE]].copy()
        gross_sales_txs['new_amount'] = gross_sales_txs.groupby(TRANSACTION_REF_ID)[AMOUNT_IN_EUR].transform('sum')
        gross_sales_txs = gross_sales_txs.drop_duplicates(subset=[TRANSACTION_REF_ID], keep='first') \
            .drop(AMOUNT_IN_EUR, axis=1) \
            .rename(columns={'new_amount': AMOUNT_IN_EUR})

        sales_returns_txs = transactions[transactions[TRANSACTION_IS_RETURN]].copy()
        sales_returns_txs['new_amount'] = sales_returns_txs.groupby(TRANSACTION_REF_ID)[AMOUNT_IN_EUR].transform('sum')
        sales_returns_txs = sales_returns_txs.drop_duplicates(subset=[TRANSACTION_REF_ID], keep='first') \
            .drop(AMOUNT_IN_EUR, axis=1) \
            .rename(columns={'new_amount': AMOUNT_IN_EUR})

        net_sales_txs = pd.DataFrame()
        if len(gross_sales_txs) > 0 and len(sales_returns_txs) > 0:
            net_sales_txs = pd.merge(gross_sales_txs, sales_returns_txs[[TRANSACTION_REF_ID, AMOUNT_IN_EUR]],
                                     on=TRANSACTION_REF_ID, how='left')
            net_sales_txs.fillna(0, inplace=True)
            net_sales_txs[AMOUNT_IN_EUR] = net_sales_txs[AMOUNT_IN_EUR + '_x'] - \
                abs(net_sales_txs[AMOUNT_IN_EUR + '_y'])
            # net_sales_txs[AMOUNT_IN_EUR] = net_sales_txs[AMOUNT_IN_EUR + '_y']
            net_sales_txs.drop([AMOUNT_IN_EUR + '_x', AMOUNT_IN_EUR + '_y'], axis=1, inplace=True)

        # Compute the gross sales per shop country
        # ------------------------------------------------
        if len(gross_sales_txs) > 0:
            sales_per_shop['gross_sales_has_data'] = True
            #creating the new data
            gross_sales = gross_sales_txs[[group_filter, AMOUNT_IN_EUR]].copy()
            gross_sales[group_filter].fillna('Unknown', inplace=True)
            #summing gross sales by group filter
            gross_sales = gross_sales.groupby([group_filter]).sum()
            gross_sales.reset_index(inplace=True)
            gross_sales.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            sales_per_shop.update({
                'gross_sales_filter': gross_sales[group_filter].tolist(),
                'gross_sales': gross_sales[AMOUNT_IN_EUR].tolist()
            })
            del gross_sales

        # Compute the sales returns per shop country
        # ------------------------------------------------
        if len(sales_returns_txs) > 0:
            sales_per_shop['sales_returns_has_data'] = True
            sales_returns = sales_returns_txs[[group_filter, AMOUNT_IN_EUR]].copy()
            sales_returns[group_filter].fillna('Unknown', inplace=True)
            sales_returns = sales_returns.groupby([group_filter]).sum()
            sales_returns.reset_index(inplace=True)
            sales_returns.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            sales_per_shop.update({
                'sales_returns_filter': sales_returns[group_filter].tolist(),
                'sales_returns': sales_returns[AMOUNT_IN_EUR].tolist()
            })
            del sales_returns

        # Compute the net sales per shop country
        # ------------------------------------------------
        if len(net_sales_txs) > 0:
            sales_per_shop['net_sales_has_data'] = True
            net_sales = net_sales_txs[[group_filter, AMOUNT_IN_EUR]].copy()
            net_sales[group_filter].fillna('Unknown', inplace=True)
            net_sales = net_sales.groupby([group_filter]).sum()
            net_sales.reset_index(inplace=True)
            net_sales.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)

            # Sort the list of net sales according to the sorted list of gross sales
            gross_filter_list = sales_per_shop['gross_sales_filter']
            net_filter_list = net_sales[group_filter].tolist()
            idx = [gross_filter_list.index(country) for country in net_filter_list if country in gross_filter_list]
            net_list = [x for _, x in sorted(zip(idx, net_sales[AMOUNT_IN_EUR].tolist()), key=lambda pair: pair[0])]
            sales_per_shop.update({
                'net_sales': net_list
            })
            del net_sales

        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(sales_per_shop, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return sales_per_shop

    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        output_png_filename = join(self.plot_output_folder, 'sales_top_rank.png')

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "h",
                    "x": data['gross_sales'][:5],
                    "y": data['gross_sales_filter'][:5],
                    "text": list(map(lambda x: '{:0,.0f}€'.format(x), data['gross_sales'][:5])),
                    "textposition": "outside",
                    "textfont": {
                        "color": kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    },
                    "name": "Gross Sales",
                    "marker": {
                        "color": kwargs['cmap']['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "h",
                    "x": data['net_sales'][:5],
                    "y": data['gross_sales_filter'][:5],
                    "text": list(map(lambda x: '{:0,.0f}€'.format(x), data['net_sales'][:5])),
                    "textposition": "outside",
                    "textfont": {
                        "color": kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    },
                    "name": "Net Sales",
                    "marker": {
                        "color": kwargs['cmap']['colors']['aquamarine']
                    },
                    "cliponaxis": False
                }
            ],
            "layout": {
                "barmode": "group",
                "xaxis": {
                    "type": "linear",
                    "autorange": True,
                    "side": 'bottom',
                    "separatethousands": True,
                    "visible": True,
                    "showticklabels": False,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "type": "category",
                    "automargin": True,
                    "autorange": "reversed",
                    "tickfont": {
                        "color": kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    }
                },
                "autosize": False,
                "bargroupgap": 0.2,
                "bargap": 0.3,
                "legend": {
                    "font": {
                        "color": kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    },
                    "xanchor": "left",
                    "yanchor": "bottom",
                    "orientation": "h",
                    "y": -0.1,
                    "x": 0.8
                },
                "margin": {
                    "pad": 10,
                    "t": 0,
                    "b": 20,
                    "l": 300,
                    "r": 200
                },
                "height": 800,
                "width": 2000
            }
        }
        pio.write_image(fig, output_png_filename, format='png')

    def report(self, report, styles, *args, **kwargs):

        Report.draw_text_right(doc=report, text='TOP RANKING', style=styles['Heading2-White'])

        Report.draw_text_right(doc=report, text='Top 5 selling countries based on gross sales', style=styles['Heading3-White'])

        img = Image(join(self.plot_output_folder, 'sales_top_rank.png'),
                    width=450,
                    height=180,
                    hAlign='LEFT')

        Report.draw_image_left(doc=report, image=img)
