# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 08:17:11 2019

@author: marina.tosic
"""
from wepair.plugins.plugin import Plugin
from ...globals import COLNAMES_PE
from os.path import join
import pandas as pd
import pickle
import inspect
from reportlab.platypus import Image
import plotly.io as pio
from ...utils.report import Report
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
CONSUMER_CITY = COLNAMES_PE['City (Consumer Address)']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
TRANSACTION_REF_ID = COLNAMES_PE['Transaction Reference ID']


class SalesPerCustomerCity(Plugin):

    def __init__(self, plugin_folder, id, options = None):
        self.plugin_name = "Sales Per Customer City"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle']

    def process(self, *args, **kwargs):
        sales_per_customer_city = {'has_data': False}

        args = list(args)

        args = list(args)
        logger.debug(kwargs)

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin Sales Per Customer City: Transaction data Missing')
            return sales_per_customer_city

        necessary_keys = [CONSUMER_CITY, AMOUNT_IN_EUR, TRANSACTION_REF_ID, TRANSACTION_IS_CAPTURE, TRANSACTION_IS_RETURN]

        transactions = args[0]

        if not all(key in transactions.columns for key in necessary_keys):
            return sales_per_customer_city

        sales_per_customer_city = {'has_data': True}

        # Extract the data of interest
        columns_to_keep = [TRANSACTION_DATE, CONSUMER_CITY, AMOUNT_IN_EUR, TRANSACTION_REF_ID, TRANSACTION_IS_CAPTURE,
                           TRANSACTION_IS_RETURN]
        if TRANSACTION_DATE not in transactions.columns:
            logger.warning('{fct_name}: There is no column TRANSACTION_DATE. '
                            'Plotting results for the net sales will not be possible.'
                            .format(fct_name=inspect.stack()[0][3]))
            columns_to_keep.remove(TRANSACTION_DATE)
        transactions = transactions[columns_to_keep]
        
        #this part of code can be done somewhere else maybe
        # Split the transaction set into gross sales and sales returns
        #copying the data where the transaction is capture
        gross_sales_txs = transactions[transactions[TRANSACTION_IS_CAPTURE]].copy()
        #grouping by transaction ref_id and summing amount_in_eur
        gross_sales_txs['new_amount'] = gross_sales_txs.groupby(TRANSACTION_REF_ID)[AMOUNT_IN_EUR].transform('sum')
        #leaving the unique records
        gross_sales_txs = gross_sales_txs.drop_duplicates(subset=[TRANSACTION_REF_ID], keep='first') \
            .drop(AMOUNT_IN_EUR, axis=1) \
            .rename(columns={'new_amount': AMOUNT_IN_EUR})
        #copying return transactions
        sales_returns_txs = transactions[transactions[TRANSACTION_IS_RETURN]].copy()
        #creating again new variable and calculating the sum of the amount in eur per transactionr ref_id
        sales_returns_txs['new_amount'] = sales_returns_txs.groupby(TRANSACTION_REF_ID)[AMOUNT_IN_EUR].transform('sum')
        sales_returns_txs = sales_returns_txs.drop_duplicates(subset=[TRANSACTION_REF_ID], keep='first') \
            .drop(AMOUNT_IN_EUR, axis=1) \
            .rename(columns={'new_amount': AMOUNT_IN_EUR})

        net_sales_txs = pd.DataFrame()
        #checking if there is a data within the datasets
        if len(gross_sales_txs) > 0 and len(sales_returns_txs) > 0:
        #then merge this two datasets
            net_sales_txs = pd.merge(gross_sales_txs, sales_returns_txs[[TRANSACTION_REF_ID, AMOUNT_IN_EUR]],
                                     on=TRANSACTION_REF_ID, how='left')
            #if its empty, then fill with 0 
            net_sales_txs.fillna(0, inplace=True)
            #calculate the net sales by suptracting the left from right datasource
            net_sales_txs[AMOUNT_IN_EUR] = net_sales_txs[AMOUNT_IN_EUR + '_x'] - net_sales_txs[AMOUNT_IN_EUR + '_y']
            net_sales_txs.drop([AMOUNT_IN_EUR + '_x', AMOUNT_IN_EUR + '_y'], axis=1, inplace=True)

        # Compute the gross sales per customer city
        # ------------------------------------------------
        logger.debug('{fct_name}: Computing the gross sales per customer city'.format(fct_name=inspect.stack()[0][3]))
        if len(gross_sales_txs) > 0:
            #first check if gross_sales_has_data variable has data
            sales_per_customer_city['gross_sales_has_data'] = True
            #create a new datasource with only two variables
            gross_sales = gross_sales_txs[[CONSUMER_CITY, AMOUNT_IN_EUR]].copy()
            #replace the Nan values with the Unknow
            gross_sales[CONSUMER_CITY].replace(to_replace='Nan', value='Unknown', inplace=True)
            #group all the sales by consumer city
            gross_sales = gross_sales.groupby([CONSUMER_CITY]).sum()
            #reset the index
            gross_sales.reset_index(inplace=True)
            #sort values
            gross_sales.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            #create a subset which will contain the records which do not have unknown consumer city
            gross_sales_no_unknown = gross_sales[gross_sales[CONSUMER_CITY] != 'Unknown'].copy()
            #sort this subset
            gross_sales_no_unknown.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            #update the names of the variables within the dataset
            sales_per_customer_city.update({
                'gross_sales': gross_sales[AMOUNT_IN_EUR].tolist(),
                'gross_sales_city_name': gross_sales[CONSUMER_CITY].tolist(),
                'gross_sales_no_unknown': gross_sales_no_unknown[AMOUNT_IN_EUR].tolist(),
                'gross_sales_city_name_no_unknown': gross_sales_no_unknown[CONSUMER_CITY].tolist()
            })
            del gross_sales

        # Compute the sales returns per customer city
        # ------------------------------------------------
        logger.debug('{fct_name}: Computing the sales returns per customer city'.format(fct_name=inspect.stack()[0][3]))
        if len(sales_returns_txs) > 0:
            sales_per_customer_city['sales_returns_has_data'] = True
            sales_returns = sales_returns_txs[[CONSUMER_CITY, AMOUNT_IN_EUR]].copy()
            sales_returns[CONSUMER_CITY].replace(to_replace='Nan', value='Unknown', inplace=True)
            sales_returns = sales_returns.groupby([CONSUMER_CITY]).sum()
            sales_returns.reset_index(inplace=True)
            sales_returns.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            sales_returns_no_unknown = sales_returns[sales_returns[CONSUMER_CITY] != 'Unknown'].copy()
            sales_returns_no_unknown.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            sales_per_customer_city.update({
                'sales_returns': sales_returns[AMOUNT_IN_EUR].tolist(),
                'sales_returns_city_name': sales_returns[CONSUMER_CITY].tolist(),
                'sales_returns_no_unknown': sales_returns_no_unknown[AMOUNT_IN_EUR].tolist(),
                'sales_returns_city_name_no_unknown': sales_returns_no_unknown[CONSUMER_CITY].tolist()
            })
            del sales_returns

        # Compute the net sales per customer city
        # ------------------------------------------------
        logger.debug('{fct_name}: Computing the net sales per customer city'.format(fct_name=inspect.stack()[0][3]))
        if len(net_sales_txs) > 0:
            sales_per_customer_city['net_sales_has_data'] = True
            #selecting only the variables which are important for the creation of the net sales subset
            net_sales = net_sales_txs[[CONSUMER_CITY, AMOUNT_IN_EUR]].copy()
            net_sales[CONSUMER_CITY].replace(to_replace='Nan', value='Unknown', inplace=True)
            net_sales = net_sales.groupby([CONSUMER_CITY]).sum()
            #the data is renamed in place (it returns nothing)
            net_sales.reset_index(inplace=True)
            net_sales.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            net_sales_no_unknown = net_sales[net_sales[CONSUMER_CITY] != 'Unknown'].copy()
            net_sales_no_unknown.sort_values(by=[AMOUNT_IN_EUR], ascending=False, inplace=True)
            # Sort the list of net sales according to the sorted list of gross sales
            gross_city_list = sales_per_customer_city['gross_sales_city_name_no_unknown']
            net_city_list = net_sales_no_unknown[CONSUMER_CITY].tolist()
            idx = list([gross_city_list.index(city) for city in net_city_list if city in gross_city_list])
            net_list = list([x for _, x in sorted(zip(idx, net_sales_no_unknown[AMOUNT_IN_EUR].tolist()),
                                                  key=lambda pair: pair[0])])
            sales_per_customer_city.update({'net_sales_no_unknown': net_list})
            del net_sales

        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(sales_per_customer_city, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return sales_per_customer_city

    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        output_png_filename = join(self.plot_output_folder, 'sales_per_customer_city.png')

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "h",
                    "x": data['gross_sales_no_unknown'][:5],
                    "y": data['gross_sales_city_name_no_unknown'][:5],
                    "text": list(map(lambda x: '{:0,.0f}€'.format(x), data['gross_sales_no_unknown'][:5])),
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
                    "x": data['net_sales_no_unknown'][:5],
                    "y": data['gross_sales_city_name_no_unknown'][:5],
                    "text": list(map(lambda x: '{:0,.0f}€'.format(x), data['net_sales_no_unknown'][:5])),
                    "textposition": "outside",
                    "textfont": {
                        "color": kwargs['cmap']['colors']['night blue'],
                        "size": 32
                    },
                    "name": "Net Sales",
                    "marker": {
                        "color": kwargs['cmap']['colors']['accent1']
                    },
                    "cliponaxis": False
                }
            ],
            "layout": {
                'paper_bgcolor':'rgba(0,0,0,0)',
                'plot_bgcolor':'rgba(0,0,0,0)',
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
                    "y": 0.0,
                    "x": 0.6
                },
                "margin": {
                    "pad": 10,
                    "t": 0,
                    "b": 20,
                    "l": 300,
                    "r": 200
                },
                "height": 480,
                "width": 2000
            }
        }
        pio.write_image(fig, output_png_filename, format='png')

    def report(self, report, styles, *args, **kwargs):

        if 'printTitle' not in kwargs['options']:
            kwargs['options']['printTitle'] = True
        if 'printDescription' not in kwargs['options']:
            kwargs['options']['printDescription'] = True

        if kwargs['options']['printTitle']:
            """report.append(Paragraph('Top 5 customer cities based on gross sales', style=styles['Heading3-NightBlue']))
            report.append(Paragraph('Note that customer cities are known only for guaranteed invoices and cards',
                                    style=styles['Heading3-NightBlue']))
        report.append(Spacer(1, 10))"""

        img = Image(join(self.plot_output_folder, 'sales_per_customer_city.png'),
                    width=500,
                    height=120,
                    hAlign='LEFT')
        Report.draw_images_in_grid(report, [img], row_number=3, total_rows=3)

        Report.draw_text_left(report,'Customer cities based on gross sales',
                              styles['Heading3-NightBlue'], 25, 215)


