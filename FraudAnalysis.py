# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 15:44:50 2019

@author: marina.tosic
"""

from os.path import join, isfile, dirname
import pandas as pd
import numpy as np
import inspect
import pickle
from ..plugin import Plugin
from ...globals import COLNAMES_PE, COLNAMES_FRAUD
from reportlab.platypus import Paragraph, Image, Table
from reportlab.lib import colors
import plotly.io as pio
from datetime import datetime
from ...utils.report import Report
from wepair.utils_common.log import Log

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

# Constants: define the column names
TRANSACTION_DATE = COLNAMES_PE['Transaction Creation Date and Time']
AMOUNT_IN_EUR = COLNAMES_PE['Amount in EUR']
CARD_BRAND = COLNAMES_PE['Card Brand']
TRANSACTION_IS_CAPTURE = COLNAMES_PE['Is capture']

# SAFE and TCP40
FRAUD_TRANSACTION_DATE = COLNAMES_FRAUD['Transaction Date']
FRAUD_AMOUNT = COLNAMES_FRAUD['Amount']
FRAUD_DATA_SOURCE = COLNAMES_FRAUD['Data Source']


class FraudAnalysis(Plugin):

    @staticmethod
    def compute_fraud_ratio(row):
        if row['n_txs'] == 0:
            return np.nan
        return row['n_frauds'] / row['n_txs']

    def plot_number_frauds_per_month(self, data, cmap):

        output_png_filename = join(self.plot_output_folder, 'fraud_n.png')

        df = pd.DataFrame()

        df['Visa'] = pd.Series(data['VISA_monthly_n_frauds'])

        df['MasterCard'] = pd.Series(data['MASTERCARD_monthly_n_frauds'])

        df['Months'] = pd.Series(data['VISA_months'])

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "v",
                    "x":  df['Months'].tolist(),
                    "y": df['Visa'].tolist(),
                    "name": "VISA",
                    "marker": {
                        "color":  cmap['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": df['Months'].tolist(),
                    "y":  df['MasterCard'].tolist(),
                    "name": "MASTERCARD",
                    "marker": {
                        "color":  cmap['colors']['accent1']
                    },
                    "cliponaxis": False
                },
            ],
            "layout": {
                "barmode": "stack",
                "xaxis": {
                    "type": "category",
                    "autorange": True,
                    "side": 'bottom',
                    "tickangle": -30,
                    "visible": True,
                    "tickwidth": 1,
                    "showticklabels": True,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "title": "Number of Fraudulent Transactions",
                    "anchor": 'free',
                    "type": "linear",
                    "automargin": True
                },
                "autosize": True,
                "bargroupgap": 0.2,
                "bargap": 0.3,
                "legend": {
                    "traceorder" : "normal",
                    "font": {
                        "color":  cmap['colors']['night blue'],
                    },
                    "xanchor": "center",
                    "yanchor": "bottom",
                    "orientation": "h",
                    "y": -0.28,
                    "x": 0.5
                },
                "height": 1000,
                "width": 1000
            }
        }

        pio.write_image(fig, output_png_filename, format='png', scale=4)

    def plot_amount_fraud_per_month(self, data, cmap):

        output_png_filename = join(self.plot_output_folder, 'fraud_amt.png')

        df = pd.DataFrame()

        df['Visa'] = pd.Series(data['VISA_monthly_amt_fraud'])

        df['MasterCard'] = pd.Series(data['MASTERCARD_monthly_amt_fraud'])

        df['Months'] = pd.Series(data['VISA_months'])

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "v",
                    "x":  df['Months'].tolist(),
                    "y": df['Visa'].tolist(),
                    "name": "VISA",
                    "marker": {
                        "color":  cmap['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": df['Months'].tolist(),
                    "y":  df['MasterCard'].tolist(),
                    "name": "MASTERCARD",
                    "marker": {
                        "color":  cmap['colors']['accent1']
                    },
                    "cliponaxis": False
                },
            ],
            "layout": {
                "barmode": "stack",
                "xaxis": {
                    "type": "category",
                    "autorange": True,
                    "side": 'bottom',
                    "tickangle": -30,
                    "visible": True,
                    "tickwidth": 1,
                    "showticklabels": True,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "title":"Fraud Amount in Euro",
                    "anchor": 'free',
                    "type": "linear",
                    "tickformat": '3,',
                    "tickprefix": '€'
                },
                "autosize": True,
                "bargroupgap": 0.2,
                "bargap": 0.3,
                "legend": {
                    "traceorder" : "normal",
                    "font": {
                        "color":  cmap['colors']['night blue'],
                    },
                    "xanchor": "center",
                    "yanchor": "bottom",
                    "orientation": "h",
                    "y": -0.28,
                    "x": 0.5
                },
                "height": 1000,
                "width": 1000
            }
        }

        pio.write_image(fig, output_png_filename, format='png', scale=4)

    def plot_fraud_ratio_per_month(self, data, cmap):

        output_png_filename = join(self.plot_output_folder, 'fraud_ratio.png')

        df = pd.DataFrame()

        df['Visa'] = pd.Series(data['VISA_monthly_fraud_ratio'])

        df['MasterCard'] = pd.Series(data['MASTERCARD_monthly_fraud_ratio'])

        df['Months'] = pd.Series(data['VISA_months'])

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "v",
                    "x":  df['Months'].tolist(),
                    "y": df['Visa'].tolist(),
                    "name": "VISA",
                    "marker": {
                        "color":  cmap['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": df['Months'].tolist(),
                    "y":  df['MasterCard'].tolist(),
                    "name": "MASTERCARD",
                    "marker": {
                        "color":  cmap['colors']['accent1']
                    },
                    "cliponaxis": False
                },
            ],
            "layout": {
                "barmode": "group",
                "xaxis": {
                    "type": "category",
                    "autorange": True,
                    "side": 'bottom',
                    "tickangle": -30,
                    "visible": True,
                    "tickwidth": 1,
                    "showticklabels": True,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "title":"Fraud ratio",
                    "anchor": 'free',
                    "type": "linear",
                    "automargin": True,
                    "tickformat": ',.2%'
                },
                "autosize": True,
                "bargroupgap": 0.2,
                "bargap": 0.3,
                "legend": {
                    "traceorder" : "normal",
                    "font": {
                        "color":  cmap['colors']['night blue'],
                    },
                    "xanchor": "center",
                    "yanchor": "bottom",
                    "orientation": "h",
                    "y": -0.28,
                    "x": 0.5
                },
                "height": 1000,
                "width": 1000
            }
        }

        pio.write_image(fig, output_png_filename, format='png', scale=4)

    def __init__(self, plugin_folder, id, options=None):

        super().__init__(plugin_folder, id, options)
        self.plugin_name = "Fraud monthly analysis"

        self.required_input_data = ['tx.pickle', 'tx_fraud.pickle']

    def process(self, *args, **kwargs):
        fraud_dict = {'has_data': False}

        args = list(args)
        if len(args) < 2:
            logger.warning('Fatal Error : Missing Arguments')
            return fraud_dict

        transactions = args[0]
        fraud_transactions = args[1]
        # Check that all the required columns are present
        necessary_keys = [FRAUD_TRANSACTION_DATE, FRAUD_AMOUNT]
        if not all(key in fraud_transactions.columns for key in necessary_keys):
            logger.warning('Necessary keys are missing: {keys}'
                            .format(keys=[key for key in necessary_keys if key not in fraud_transactions.columns]))
            return fraud_dict

        fraud_dict = {'has_data': True}

        # --------------------------------------------------------------------
        # Compute start and end dates
        # --------------------------------------------------------------------
        
        
        fraud_dict['start_date'] = transactions[TRANSACTION_DATE].min()
        fraud_dict['end_date'] =transactions[TRANSACTION_DATE].max()


        #fraud_transactions.drop_duplicates(keep="first", inplace=True)
        
#this is only a KPI for counting the VISA frauds - literaly a fraud analysis
        # For VISA (TC40)
        frauds_visa = fraud_transactions[fraud_transactions[FRAUD_DATA_SOURCE] == 'TC40'][
            [FRAUD_TRANSACTION_DATE, FRAUD_AMOUNT]].copy()
        frauds_visa = frauds_visa.resample('M', on=FRAUD_TRANSACTION_DATE) \
            .agg([sum, 'size']) \
            .reset_index(drop=False)
        frauds_visa.columns = [FRAUD_TRANSACTION_DATE, 'amt_fraud', 'n_frauds']

        #print(frauds_visa)

        txs_visa = transactions[(transactions[CARD_BRAND] == 'Visa') & (transactions[TRANSACTION_IS_CAPTURE])][
            [TRANSACTION_DATE, AMOUNT_IN_EUR]]

        txs_visa = txs_visa[txs_visa[TRANSACTION_DATE] <= frauds_visa[FRAUD_TRANSACTION_DATE].max()]

        txs_visa = txs_visa.resample('M', on=TRANSACTION_DATE) \
            .agg([sum, 'size']) \
            .reset_index(drop=False)
        txs_visa.columns = [TRANSACTION_DATE, 'amt_txs', 'n_txs']

        results_visa = pd.merge(txs_visa, frauds_visa, left_on=TRANSACTION_DATE, right_on=FRAUD_TRANSACTION_DATE,
                                how='inner')
        results_visa.drop(FRAUD_TRANSACTION_DATE, axis=1, inplace=True)
        results_visa.fillna(0, inplace=True)
        results_visa['fraud_ratio'] = results_visa.apply(self.compute_fraud_ratio, axis=1)

        #print(results_visa)

        # For MasterCard (SAFE)
        frauds_mc = fraud_transactions[fraud_transactions[FRAUD_DATA_SOURCE] == 'SAFE'][
            [FRAUD_TRANSACTION_DATE, FRAUD_AMOUNT]].copy()
        frauds_mc = frauds_mc.resample('M', on=FRAUD_TRANSACTION_DATE) \
            .agg([sum, 'size']) \
            .reset_index(drop=False)
        frauds_mc.columns = [FRAUD_TRANSACTION_DATE, 'amt_fraud', 'n_frauds']

        #print(frauds_mc)

        txs_mc = transactions[(transactions[CARD_BRAND] == 'Master Card') & (transactions[TRANSACTION_IS_CAPTURE])][
            [TRANSACTION_DATE, AMOUNT_IN_EUR]]

        txs_mc = txs_mc[txs_mc[TRANSACTION_DATE] <= frauds_mc[FRAUD_TRANSACTION_DATE].max()]

        txs_mc = txs_mc.resample('M', on=TRANSACTION_DATE) \
            .agg([sum, 'size']) \
            .reset_index(drop=False)
        txs_mc.columns = [TRANSACTION_DATE, 'amt_txs', 'n_txs']

        results_mc = pd.merge(txs_mc, frauds_mc, left_on=TRANSACTION_DATE, right_on=FRAUD_TRANSACTION_DATE, how='inner')
        results_mc.drop(FRAUD_TRANSACTION_DATE, axis=1, inplace=True)
        results_mc.fillna(0, inplace=True)
        results_mc['fraud_ratio'] = results_mc.apply(self.compute_fraud_ratio, axis=1)

        #print(results_mc)

        visa_n_frauds = results_visa['n_frauds'].sum()
        visa_amt_frauds = results_visa['amt_fraud'].sum()
        visa_n_txs = results_visa['n_txs'].sum()
        visa_fraud_ratio = np.nan
        if visa_n_txs > 0:
            visa_fraud_ratio = visa_n_frauds / visa_n_txs

        mc_n_frauds = results_mc['n_frauds'].sum()
        mc_amt_frauds = results_mc['amt_fraud'].sum()
        mc_n_txs = results_mc['n_txs'].sum()
        mc_fraud_ratio = np.nan
        if mc_n_txs > 0:
            mc_fraud_ratio = mc_n_frauds / mc_n_txs

        fraud_dict.update({
            'VISA_months': results_visa[TRANSACTION_DATE].apply(lambda x: x.strftime('%b-%y')).tolist(),
            'VISA_monthly_n_frauds': results_visa['n_frauds'].tolist(),
            'VISA_monthly_amt_fraud': results_visa['amt_fraud'].tolist(),
            'VISA_monthly_fraud_ratio': results_visa['fraud_ratio'].tolist(),
            'MASTERCARD_months': results_mc[TRANSACTION_DATE].apply(lambda x: x.strftime('%b-%y')).tolist(),
            'MASTERCARD_monthly_n_frauds': results_mc['n_frauds'].tolist(),
            'MASTERCARD_monthly_amt_fraud': results_mc['amt_fraud'].tolist(),
            'MASTERCARD_monthly_fraud_ratio': results_mc['fraud_ratio'].tolist(),
            'VISA_n_frauds': visa_n_frauds,
            'VISA_amt_frauds': visa_amt_frauds,
            'VISA_fraud_ratio': visa_fraud_ratio,
            'MASTERCARD_n_frauds': mc_n_frauds,
            'MASTERCARD_amt_frauds': mc_amt_frauds,
            'MASTERCARD_fraud_ratio': mc_fraud_ratio
        })

        with open(self.process_output_file, "wb") as pickle_out:
            pickle.dump(fraud_dict, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return fraud_dict

    def plot(self, *args, **kwargs):

        assert isfile(
            self.process_output_file),\
            'Fatal Error: The file {filename} is missing.Function {plugin_name}cannot run.'\
            .format(filename=self.process_output_file, plugin_name=self.plugin_name)

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        self.plot_number_frauds_per_month(data, kwargs['cmap'])

        self.plot_amount_fraud_per_month(data, kwargs['cmap'])

        self.plot_fraud_ratio_per_month(data, kwargs['cmap'])

    def report(self, report, styles, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        Report.draw_text_right(doc=report, text='FRAUD ANALYSIS', style=styles['Heading2-White'])

        Report.draw_text_right(doc=report, text='Key Indicators', style=styles['Heading3-White'])

        # KPIs for VISA
        img = Image(join(dirname(inspect.getfile(inspect.currentframe())), self.options['assets'], 'visa_logo.png'),
                    width=60,
                    height=20)
        txt_visa_fraud = Paragraph('Number of fraudulent transactions<br/>Monetary value of fraudulent '
                                   'transactions',
                                   style=styles['Normal'])
        kpi_visa_fraud = Paragraph('{n_frauds:,.0f}<br/>{amt_fraud:,.0f} €'
                                   .format(n_frauds=data['VISA_n_frauds'],
                                           amt_fraud=data['VISA_amt_frauds']),
                                   style=styles['Normal'])

        Report.draw_text_right(doc=report, text='Important Note:', style=styles['Footer-White'], bias=-50)

        Report.draw_text_right(doc=report,
                               text='Data for Fraudulent Transactions (TC40 and SAFE files) are being ' \
                                    'received only in the following month for the whole previous month. ' \
                                    'Therefore these transactions can be displayed only with ' \
                                    'a certain delay in time.', style=styles['Footer-White'], bias=-35)

        # list containing all tables to be reported
        list_tables = []
        colwidths = (85, 240, 80)

        # append the visa's table
        list_tables.append(Table(data=[(img, txt_visa_fraud, kpi_visa_fraud)], colWidths=colwidths, rowHeights=60, hAlign='CENTER'))

        # KPIs for MASTERCARD
        img = Image(join(dirname(inspect.getfile(inspect.currentframe())),  self.options['assets'], 'mc_logo.png'),
                    width=40,
                    height=30)

        txt_mastercard_fraud = Paragraph('Number of fraudulent transactions<br/>Monetary value of fraudulent '
                                   'transactions',
                                   style=styles['Normal'])
        kpi_mastercard_fraud = Paragraph('{n_frauds:,.0f}<br/>{amt_frauds:,.0f} €'
                                   .format(n_frauds=data['MASTERCARD_n_frauds'],
                                           amt_frauds=data['MASTERCARD_amt_frauds']),
                                   style=styles['Normal'])

        # append the mastercard's table
        list_tables.append(Table([(img, txt_mastercard_fraud, kpi_mastercard_fraud)], colWidths=colwidths, rowHeights=60, hAlign='CENTER'))

        txt_total_fraud = Paragraph('<b>Total number of fraudulent transactions<br/>Total monetary value of fraudulent '
                                   'transactions</b>',
                                   style=styles['Normal'])
        kpi_total_fraud = Paragraph('{n_frauds:,.0f}<br/>{amt_frauds:,.0f} €'
                                   .format(n_frauds=data['MASTERCARD_n_frauds']+data['VISA_n_frauds'],
                                           amt_frauds=data['MASTERCARD_amt_frauds']+data['VISA_amt_frauds']),
                                   style=styles['Normal'])

        # append a summary table
        list_tables.append(Table([('', txt_total_fraud, kpi_total_fraud)], colWidths=colwidths, rowHeights=60, hAlign='CENTER'))

        for ind, delta in enumerate([350, 250, 150]):
            list_tables[ind].setStyle(
            [
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'TOP'),
                ('VALIGN', (1, 0), (1, 0), 'TOP'),
                ('VALIGN', (2, 0), (2, 0), 'TOP'),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.grey)])

            Report.draw_table_left(doc=report, table=list_tables[ind], coordinates=(100, delta))

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(doc=report, text='FRAUD ANALYSIS', style=styles['Heading2-White'])

        Report.draw_text_right(doc=report, text='Monthly Analysis: Number of fraudulent transactions per month '
                                                'for Visa and Mastercard', style=styles['Heading3-White'])

        Report.draw_text_right(doc=report, text='Important Note:', style=styles['Footer-White'], bias=-50)

        Report.draw_text_right(doc=report,
                               text='Data for Fraudulent Transactions (TC40 and SAFE files) are being ' \
                                    'received only in the following month for the whole previous month. ' \
                                    'Therefore these transactions can be displayed only with ' \
                                    'a certain delay in time.', style=styles['Footer-White'], bias=-35)

        img = Image(join(self.plot_output_folder, 'fraud_n.png'),
                    width=550,
                    height=400)

        Report.draw_image_left(doc=report, image=img)

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(doc=report, text='FRAUD ANALYSIS', style=styles['Heading2-White'])

        Report.draw_text_right(doc=report, text='Monthly Analysis: Monetary value of fraudulent transactions '
                                                'per month for Visa and Mastercard', style=styles['Heading3-White'])

        Report.draw_text_right(doc=report, text='Important Note:', style=styles['Footer-White'], bias=-50)

        Report.draw_text_right(doc=report,
                               text='Data for Fraudulent Transactions (TC40 and SAFE files) are being ' \
                                    'received only in the following month for the whole previous month. ' \
                                    'Therefore these transactions can be displayed only with ' \
                                    'a certain delay in time.', style=styles['Footer-White'], bias=-35)


        img = Image(join(self.plot_output_folder, 'fraud_amt.png'),
                    width=550,
                    height=400)

        Report.draw_image_left(doc=report, image=img)

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(doc=report, text='FRAUD ANALYSIS', style=styles['Heading2-White'])

        Report.draw_text_right(doc=report, text='Monthly Analysis: Percentage of fraudulent transactions per month '
                                                'for Visa and Mastercard', style=styles['Heading3-White'])

        Report.draw_text_right(doc=report, text='Important Note:', style=styles['Footer-White'], bias=-50)

        Report.draw_text_right(doc=report,
                               text='Data for Fraudulent Transactions (TC40 and SAFE files) are being ' \
                                    'received only in the following month for the whole previous month. ' \
                                    'Therefore these transactions can be displayed only with ' \
                                    'a certain delay in time.', style=styles['Footer-White'], bias=-35)
        img = Image(join(self.plot_output_folder, 'fraud_ratio.png'),
                    width=550,
                    height=400)

        Report.draw_image_left(doc=report, image=img)
