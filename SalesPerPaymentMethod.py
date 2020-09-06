# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 10:22:46 2019

@author: marina.tosic
"""

from wepair.plugins.plugin import Plugin
import pandas as pd
from ...globals import COLNAMES_PE
from os.path import join
import plotly.io as pio
import pickle
from reportlab.platypus import Paragraph, Image, Table, TableStyle
from ...utils.report import Report
from wepair.utils_common.log import Log
from wepair.utils_common.tools import Tools

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

PAYMENT_METHOD = COLNAMES_PE['Payment Method']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
TRANSACTION_REF_ID = COLNAMES_PE['Transaction Reference ID']
TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']


class SalesPerPaymentMethod(Plugin):

    def __init__(self, plugin_folder, id, options=None):
        self.plugin_name = "Sales Per Payment Method"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle']

    def process(self, *args, **kwargs):
        sales_per_payment_method = {'has_data': False}

        logger.debug(kwargs)

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin Sales Per Payment Method: Transaction data Missing')
            return sales_per_payment_method

        args = list(args)
        transactions = args[0]

        necessary_keys = [PAYMENT_METHOD, AMOUNT_IN_EUR, TRANSACTION_REF_ID, TRANSACTION_IS_CAPTURE,
                          TRANSACTION_IS_RETURN]

        if not all(key in transactions.columns for key in necessary_keys):
            return sales_per_payment_method

        sales_per_payment_method = {'has_data': True}

        # Obtaining the first and last date of the transcational data to print the time window

        period_start = transactions[TRANSACTION_DATE].min()
        period_end = transactions[TRANSACTION_DATE].max()

        begin_year = int(period_start.strftime('%Y'))
        end_year = int(period_end.strftime('%Y'))

        if begin_year == end_year:
            earliest_date = period_start.strftime('%B')
            latest_date = period_end.strftime('%B')
            text = earliest_date + " to " + latest_date + " of "+str(end_year)
        else:
            earliest_date = period_start.strftime('%B %Y')
            latest_date = period_end.strftime('%B %Y')
            text = earliest_date + " to " + latest_date

        sales_per_payment_method['time_period'] = text
        tt = Tools.get_time_period(transactions)
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
            net_sales_txs[AMOUNT_IN_EUR] = net_sales_txs[AMOUNT_IN_EUR + '_x'] - net_sales_txs[AMOUNT_IN_EUR + '_y']
            net_sales_txs.drop([AMOUNT_IN_EUR + '_x', AMOUNT_IN_EUR + '_y'], axis=1, inplace=True)

        gross_sales_txs = gross_sales_txs[[PAYMENT_METHOD, AMOUNT_IN_EUR]]
        sales_returns_txs = sales_returns_txs[[PAYMENT_METHOD, AMOUNT_IN_EUR]]
        net_sales_txs = net_sales_txs[[PAYMENT_METHOD, AMOUNT_IN_EUR]]

        # Compute the gross sales per payment method
        # ------------------------------------------------
        if len(gross_sales_txs) > 0:
            gross_sales = gross_sales_txs[[PAYMENT_METHOD, AMOUNT_IN_EUR]].copy()
            gross_sales[PAYMENT_METHOD].fillna('other', inplace=True)
            gross_sales = gross_sales.groupby([PAYMENT_METHOD]).sum()
            gross_sales.reset_index(inplace=True)
            # total = gross_sales[AMOUNT_IN_EUR].sum()
            sales_per_payment_method.update({
                'gross_sales': gross_sales[AMOUNT_IN_EUR].tolist(),
                'gross_sales_payment_methods': gross_sales[PAYMENT_METHOD].tolist()
            })
            del gross_sales

        # Compute the sales returns per payment method
        # ------------------------------------------------
        if len(sales_returns_txs) > 0:
            sales_returns = sales_returns_txs[[PAYMENT_METHOD, AMOUNT_IN_EUR]].copy()
            sales_returns[PAYMENT_METHOD].fillna('other', inplace=True)
            
            sales_returns = sales_returns.groupby([PAYMENT_METHOD]).sum()
            
            sales_returns.reset_index(inplace=True)
         #update to list?    
            sales_per_payment_method.update({
                'sales_returns': sales_returns[AMOUNT_IN_EUR].tolist(),
                'sales_returns_payment_methods': sales_returns[PAYMENT_METHOD].tolist()
            })
            del sales_returns

        # Compute the net sales per payment method
        # ------------------------------------------------
        if len(net_sales_txs) > 0:
            net_sales = net_sales_txs[[PAYMENT_METHOD, AMOUNT_IN_EUR]].copy()
            net_sales[PAYMENT_METHOD].fillna('other', inplace=True)
            #group by net sales payment methods
            net_sales = net_sales.groupby([PAYMENT_METHOD]).sum()
            #inplace=true?
            net_sales.reset_index(inplace=True)
            #updating names of the variables 
            sales_per_payment_method.update({
                'net_sales': net_sales[AMOUNT_IN_EUR].tolist(),
                'net_sales_payment_methods': net_sales[PAYMENT_METHOD].tolist()
            })
            del net_sales

        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(sales_per_payment_method, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return sales_per_payment_method

    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        # same color per type of payment pls
        id_color_dict = {}
        palettes_colors = kwargs['cmap']['palettes']['wirecard'].copy()
        for data_source in ['gross_sales', 'sales_returns', 'net_sales']:
            for val in data[data_source + '_payment_methods']:
                if val not in id_color_dict:
                    if not palettes_colors:
                        raise ValueError('There are more items to be plotted in the pie than colors available: '
                                         'increase your WD palette')
                    id_color_dict[val] = palettes_colors[0]
                    palettes_colors.pop(0)

        for data_source in ['gross_sales', 'sales_returns', 'net_sales']:
            fig = {
                "data": [
                    {
                        "values": [f"{(x*100)/sum(data[data_source]):.4f}" for x in data[data_source]],
                        "labels": data[data_source + '_payment_methods'],
                        "hole": .75,
                        "type": "pie",
                        "sort": False,
                        "rotation": 90,
                        "textinfo": "percent",
                        "textposition": "outside",
                        "direction": "counterclockwise",
                        "marker": {
                            "colors": [id_color_dict[x] for x in data[data_source + '_payment_methods']],
                            "line": {
                                "width": 0,
                                "color": "#FFFFFF"
                            }
                        },
                        "textfont": {
                            "size": 32,
                            "color": kwargs['cmap']['colors']['black']
                        }
                    }
                ],
                "layout": {
                    "annotations": [],
                    "height": 1000,
                    "width": 1000,
                    "showlegend": True,
                    "margin": {
                        "t": 35,
                        "l": 150,
                        "r": 150,
                    },
                    "legend": {
                        "y": -0.1,
                        "x": 0.5,
                        "xanchor": "center",
                        "yanchor": "top",
                        "orientation": "h",
                        "traceorder": "normal",
                        "font": {
                            "size": 30
                        }
                    }
                }
            }
            pio.write_image(fig, join(self.plot_output_folder, data_source + '_per_payment_method.png'))

    def report(self, report, styles, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        img_height = 250
        img_width = 250

        if 'printTitle' not in kwargs['options']:
            kwargs['options']['printTitle'] = True
        if 'printDescription' not in kwargs['options']:
            kwargs['options']['printDescription'] = True

        if kwargs['options']['printTitle']:
            Report.draw_text_right(doc=report, text='PAYMENT METHODS USED FOR PURCHASES AND RETURNS',
                                   style=styles['Heading2-White'])

        sales_per_payment_methods = Image(join(self.plot_output_folder, 'gross_sales_per_payment_method.png'),
                                          width=img_width,
                                          height=img_height)
        returns_per_payment_methods = Image(join(self.plot_output_folder, 'sales_returns_per_payment_method.png'),
                                            width=img_width,
                                            height=img_height)

        gross_sales_text = Paragraph('Gross Sales',
                                    style=styles['Heading3-NightBlue-Center'])

        net_sales_text = Paragraph('Returns',
                                   style=styles['Heading3-NightBlue-Center'])

        data_table = [(gross_sales_text, net_sales_text),
            (sales_per_payment_methods, returns_per_payment_methods)]

        table = Table(data_table, colWidths=img_width, rowHeights=[25, img_height])

        table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), "CENTER"),
                                   ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

        Report.draw_table_left(doc=report, table=table)


