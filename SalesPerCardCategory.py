# -*- coding: utf-8 -*-
"""
Created on Fri Jul 19 12:41:37 2019

@author: marina.tosic
"""

from wepair.plugins.plugin import Plugin
import pandas as pd
from ...globals import COLNAMES_PE
from os.path import join
import pickle
import plotly.io as pio
from reportlab.platypus import Paragraph, Image, Table, TableStyle
from ...utils.report import Report
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

CARD_CATEGORY = COLNAMES_PE['Card Category']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
PAYMENT_METHOD = COLNAMES_PE['Payment Method']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']
TRANSACTION_IS_RETURN = COLNAMES_PE['Is return']
TRANSACTION_REF_ID = COLNAMES_PE['Transaction Reference ID']
TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']



class SalesPerCardCategory(Plugin):

    def __init__(self, plugin_folder, id, options = None):
        self.plugin_name = "Sales Per Card Category"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle']

    def process(self, *args, **kwargs):
        #initialize sales_per_card_category variable

        sales_per_card_category = {'has_data': False}

        logger.debug(kwargs)
        

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin Sales Per Card Category: Transaction data Missing')
            return sales_per_card_category

        args = list(args)
        transactions = args[0]

        necessary_keys = [CARD_CATEGORY, AMOUNT_IN_EUR, PAYMENT_METHOD, TRANSACTION_REF_ID, TRANSACTION_IS_CAPTURE,
                          TRANSACTION_IS_RETURN]

        if not all(key in transactions.columns for key in necessary_keys):
            return sales_per_card_category

        sales_per_card_category = {'has_data': True}

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

        sales_per_card_category['time_period'] = text

        # Extract the data of interest
        transactions = transactions[transactions[PAYMENT_METHOD] == 'CARD']
        transactions = transactions[[CARD_CATEGORY, AMOUNT_IN_EUR, TRANSACTION_REF_ID, TRANSACTION_IS_CAPTURE,
                                     TRANSACTION_IS_RETURN]]


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

        # Compute the gross sales per card category
        # ------------------------------------------------
        if len(gross_sales_txs) > 0:
            gross_sales = gross_sales_txs[[CARD_CATEGORY, AMOUNT_IN_EUR]].copy()
            gross_sales[CARD_CATEGORY].fillna('Not available', inplace=True)
            gross_sales[CARD_CATEGORY].replace(to_replace='nan', value='Not available', inplace=True)
            gross_sales[CARD_CATEGORY].replace(to_replace='UnspecifiedCard', value='Unspecified Card', inplace=True)
            gross_sales = gross_sales.groupby([CARD_CATEGORY]).sum()
            gross_sales.reset_index(inplace=True)
            sales_per_card_category.update({
                'gross_sales': gross_sales[AMOUNT_IN_EUR].tolist(),
                'gross_sales_card_category': gross_sales[CARD_CATEGORY].tolist()
            })
            del gross_sales

        # Compute the sales returns per card category
        # ------------------------------------------------
        if len(sales_returns_txs) > 0:
            sales_returns = sales_returns_txs[[CARD_CATEGORY, AMOUNT_IN_EUR]].copy()
            sales_returns[CARD_CATEGORY].fillna('Not available', inplace=True)
            sales_returns[CARD_CATEGORY].replace(to_replace='nan', value='Not available', inplace=True)
            sales_returns[CARD_CATEGORY].replace(to_replace='UnspecifiedCard', value='Unspecified Card', inplace=True)
            sales_returns = sales_returns.groupby([CARD_CATEGORY]).sum()
            sales_returns.reset_index(inplace=True)
            sales_per_card_category.update({
                'sales_returns': sales_returns[AMOUNT_IN_EUR].tolist(),
                'sales_returns_card_category': sales_returns[CARD_CATEGORY].tolist()
            })
            del sales_returns

        # Compute the net sales per card category
        # ------------------------------------------------
        if len(net_sales_txs) > 0:
            net_sales = net_sales_txs[[CARD_CATEGORY, AMOUNT_IN_EUR]].copy()
            net_sales[CARD_CATEGORY].fillna('Not available', inplace=True)
            net_sales[CARD_CATEGORY].replace(to_replace='nan', value='Not available', inplace=True)
            net_sales[CARD_CATEGORY].replace(to_replace='UnspecifiedCard', value='Unspecified Card', inplace=True)
            net_sales = net_sales.groupby([CARD_CATEGORY]).sum()
            net_sales.reset_index(inplace=True)
            sales_per_card_category.update({
                'net_sales': net_sales[AMOUNT_IN_EUR].tolist(),
                'net_sales_card_category': net_sales[CARD_CATEGORY].tolist()
            })
            del net_sales

        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(sales_per_card_category, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return sales_per_card_category


#part for plotting the output
    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        # same color per type of payment pls
        id_color_dict = {}
        palettes_colors = kwargs['cmap']['palettes']['wirecard'].copy()
        #check if the values are selected
        for data_source in ['gross_sales', 'sales_returns', 'net_sales']:
            for val in data[data_source + '_card_category']:
                if val not in id_color_dict:
                    if not palettes_colors:
                        raise ValueError('There are more items to be plotted in the pie than colors available: increase your WR palette')
                    id_color_dict[val] = palettes_colors[0]
                    palettes_colors.pop(0)

        for data_source in ['gross_sales', 'sales_returns', 'net_sales']:
            fig = {
                "data": [
                    {
                        "values": [f"{(x*100)/sum(data[data_source]):.4f}" for x in data[data_source]],
                        "labels": data[data_source + '_card_category'],
                        "name": "Card Category",
                        "hole": .75,
                        "type": "pie",
                        "sort": False,
                        "rotation": 90,
                        "textinfo": "percent",
                        "textposition": "outside",
                        "direction": "counterclockwise",
                        "marker": {
                            "colors": [id_color_dict[x] for x in data[data_source + '_card_category']],
                            "line": {
                                "width": 0,
                                "color": "#FFFFFF"
                            }
                        },
                        "textfont": {
                            "size": 32,
                            "color": "#000000"
                        }

                    }],
                "layout": {
                    "yaxis": {
                        "tickformat": ".3f"
                    },
                    "annotations": [],
                    "height": 1000,
                    "width": 1000,
                    "showlegend": True,
                    "margin": {
                        "t": 10,
                        "l": 150,
                        "r": 150,
                    },
                    "legend": {
                        "y": 0,
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
            pio.write_image(fig, join(self.plot_output_folder, data_source + '_per_card_category.png'))

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
            Report.draw_text_right(doc=report, text='DISTRIBUTION OF CARD CATEGORIES FOR PURCHASES AND RETURNS',
                                   style=styles['Heading2-White'])

        sales_per_card_category = Image(join(self.plot_output_folder, 'gross_sales_per_card_category.png'),
                                          width=img_width,
                                          height=img_height)
        returns_per_card_category = Image(join(self.plot_output_folder, 'sales_returns_per_card_category.png'),
                                            width=img_width,
                                            height=img_height)
        gross_sales_text = Paragraph('Gross Sales',
                                     style=styles['Heading3-NightBlue-Center'])

        net_sales_text = Paragraph('Returns',
                                   style=styles['Heading3-NightBlue-Center'])

        data_table = [(gross_sales_text, net_sales_text),
                      (sales_per_card_category, returns_per_card_category)]
        table = Table(data_table, colWidths=img_width, rowHeights=[15, img_height])

        table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), "CENTER"),
                                   ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

        Report.draw_table_left(doc=report, table=table)