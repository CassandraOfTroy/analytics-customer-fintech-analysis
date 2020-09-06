# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 13:47:46 2019

@author: marina.tosic
"""

from ...globals import COLNAMES_PE, COLNAMES_CHARGEBACK
import pandas as pd
from os.path import join, dirname
import pickle
import inspect
from wepair.plugins.plugin import Plugin
import plotly.graph_objs as go
from reportlab.platypus import Paragraph, Table, Image
from reportlab.lib import colors
from ...utils.report import Report
import plotly.io as pio
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

# Chargebacks
CB_TRANSACTION_REF_ID = COLNAMES_CHARGEBACK['Transaction Reference ID']
CB_DATE = COLNAMES_CHARGEBACK['Chargeback Date']
CB_CURRENCY = COLNAMES_CHARGEBACK['Currency']
CB_AMOUNT = COLNAMES_CHARGEBACK['Amount']
CB_DISPUTE_STATUS = COLNAMES_CHARGEBACK['Dispute Status']
CB_CASE_STATUS = COLNAMES_CHARGEBACK['Case Status']
CB_REASON = COLNAMES_CHARGEBACK['Chargeback Reason']
CB_CARD_BRAND = COLNAMES_CHARGEBACK['Card Brand']
CB_SHOP_SHORT_NAME = COLNAMES_CHARGEBACK['Merchant Short Name']


class ChargebacksAnalysis(Plugin):

    def plot_chargebacks_overview(self, data, cmap):

        for data_source in ['VISA', 'MASTERCARD']:
            output_png_filename = join(self.plot_output_folder, data_source + '_chgbcks_overview.png')

            #####################################################################################
            # Creating  Overview Pie Chart
            #####################################################################################
            data[data_source + '_pie_reasons'] = list(map(lambda x: str(x)[:35] + '...' if len(str(x)) > 35 else str(x),
                                                          data[data_source + '_pie_reasons']))

            if data_source=='VISA':
                fig = {
                    "data": [
                        {
                            "values": data[data_source + '_pie_n_chargebacks'],
                            "labels": data[data_source + '_pie_reasons'],
                            "name": "Chargebacks Overview",
                            "sort": True,
                            "hole": .75,
                            "type": "pie",
                            "rotation": 90,
                            "textinfo": "percent",
                            "textposition": "outside",
                            "direction": "counterclockwise",
                            "marker": {
                                "colors": cmap["palettes"]["wirecard"],
                                "line": {
                                    "width": 0,
                                    "color": "#FFFFFF"
                                }
                            },
                            "textfont": {
                                "size": 30
                            }
                        }],
                    "layout": {
                        "annotations": [],
                        "height": 900,
                        "width": 1600,
                        "showlegend": True,
                        "margin": {
                            "t": 5,
                            "b": 5,
                            "l": 100,
                            "r": 0,
                        },
                        "legend": {
                            "x": 2.0,
                            "y": 0.6,
                            "xanchor": "right",
                            "yanchor": "top",
                            "orientation": "v",
                            "traceorder": "normal",
                            "font": {
                                "size": 30
                            }
                        },
                        # 'images': [{'source': "https://www.hardwareluxx.de/images/stories/logos-2015/visa.jpg",
                        #             'sizing': 'stretch', 'x': 'center', 'y': 'center',
                        #             'layer': 'above',
                        #             'sizex': 0.1, 'sizey': 0.1, 'opacity': 1
                        #             }]
                    }
                }
            else:
                fig = {
                    "data": [
                        {
                            "values": data[data_source + '_pie_n_chargebacks'],
                            "labels": data[data_source + '_pie_reasons'],
                            "name": "Chargebacks Overview",
                            "sort": True,
                            "hole": .75,
                            "type": "pie",
                            "rotation": 90,
                            "textinfo": "percent",
                            "textposition": "outside",
                            "direction": "counterclockwise",
                            "marker": {
                                "colors": cmap["palettes"]["wirecard"],
                                "line": {
                                    "width": 0,
                                    "color": "#FFFFFF"
                                }
                            },
                            "textfont": {
                                "size": 30
                            }
                        }],
                    "layout": {
                        "annotations": [],
                        "height": 900,
                        "width": 1600,
                        "showlegend": True,
                        "margin": {
                            "t": 5,
                            "b": 5,
                            "l": 100,
                            "r": 0,
                        },
                        "legend": {
                            "x": 2.1,
                            "y": 0.5,
                            "xanchor": "right",
                            "yanchor": "middle",
                            "orientation": "v",
                            "traceorder": "normal",
                            "font": {
                                "size": 30
                            }
                        }
                    }
                }
            pio.write_image(fig, join(self.plot_output_folder, output_png_filename), scale=2)

    def plot_chargebacks_monthly_analysis_overview(self, data, cmap):
        for data_source in ['VISA', 'MASTERCARD']:
            output_png_filename = join(self.plot_output_folder, data_source + '_chgbcks_distributions.png')
            time_series_data = data[data_source + '_series']
            traces = []

            for i in range(1, len(time_series_data.keys())-1):
                name = [time_series_data[i]['reason']][0]
                if len(name) > 35:
                    name = name[:35]+ '...'
                color_idx = i % len(cmap['palettes']['wirecard'])
                trace = go.Bar(
                    x=time_series_data['months'],
                    y=time_series_data[i]['n_chargebacks'],
                    name=name,
                    marker=dict(
                        color=cmap['palettes']['wirecard'][color_idx-1]
                    )
                )
                traces.append(trace)

            layout = go.Layout(
                showlegend=True,
                barmode='stack',
                margin={
                    "t": 0,
                    "b": 200
                },
                font={
                    "size": 32
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
                    "automargin": True
                },
                width=2250,
                height=1000,
                legend={
                    "borderwidth": 0,
                    "orientation": "v",
                    "x": 1.6,
                    "y": .99,
                    "xanchor": "right",
                    "yanchor": "top",
                    "font": {
                        "size": 32
                    },
                    "traceorder": "normal",
                }
            )
            fig = go.Figure(data=traces, layout=layout)
            pio.write_image(fig,  output_png_filename, scale=2)

    def plot_number_chargebacks_per_month(self, data, cmap):

        output_png_filename = join(self.plot_output_folder, 'chgbcks_number.png')

        # i goes from 1 to len-1 (0 is the month), the i's are the reasons
        visa_nb_chargebacks = [data['VISA_series'][i]['n_chargebacks']
                               for i in range(1, len(data['VISA_series'].keys()) - 1)]
        # visa_nb_chargebacks is a list of list. We need the element-wise addition of all its elements
        visa_nb_chargebacks = [sum(x) for x in zip(*[l for l in visa_nb_chargebacks])]

        # i goes from 1 to len-1 (0 is the month), the i's are the reasons
        mc_nb_chargebacks = [data['MASTERCARD_series'][i]['n_chargebacks']
                             for i in range(1, len(data['MASTERCARD_series'].keys()) - 1)]
        # mc_nb_chargebacks is a list of list. We need the element-wise addition of all its elements
        mc_nb_chargebacks = [sum(x) for x in zip(*[l for l in mc_nb_chargebacks])]

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": data['VISA_series']['months'],
                    "y": visa_nb_chargebacks,
                    "name": "VISA",
                    "marker": {
                        "color":  cmap['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": data['MASTERCARD_series']['months'],
                    "y": mc_nb_chargebacks,
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
                    "tickwidth":1,
                    "showticklabels": True,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "title" : "Number of Chargebacks",
                    "anchor": 'free',
                    "type": "linear",
                    "automargin": True
                },
                "autosize": True,
                "bargroupgap": 0.2,
                "bargap": 0.3,
                "legend": {
                    "traceorder": "normal",
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

    def plot_amount_chargebacks_per_month(self, data, cmap):

        output_png_filename = join(self.plot_output_folder, 'chgbcks_amount.png')

        # i goes from 1 to len-1 (0 is the month), the i's are the reasons
        visa_amt_chargebacks = [data['VISA_series'][i]['amt_chargebacks']
                               for i in range(1, len(data['VISA_series'].keys()) - 1)]
        # visa_nb_chargebacks is a list of list. We need the element-wise addition of all its elements
        visa_amt_chargebacks = [sum(x) for x in zip(*[l for l in visa_amt_chargebacks])]

        # i goes from 1 to len-1 (0 is the month), the i's are the reasons
        mc_amt_chargebacks = [data['MASTERCARD_series'][i]['amt_chargebacks']
                             for i in range(1, len(data['MASTERCARD_series'].keys()) - 1)]
        # mc_nb_chargebacks is a list of list. We need the element-wise addition of all its elements
        mc_amt_chargebacks = [sum(x) for x in zip(*[l for l in mc_amt_chargebacks])]

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": data['VISA_series']['months'],
                    "y": visa_amt_chargebacks,
                    "name": "VISA",
                    "marker": {
                        "color":  cmap['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": data['MASTERCARD_series']['months'],
                    "y": mc_amt_chargebacks,
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
                    "tickangle":-30,
                    "visible": True,
                    "tickwidth":1,
                    "showticklabels": True,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "title":"Chargebacks Amount in Euro",
                    "type": "linear",
                    "anchor": 'free',
                    "automargin": True,
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

    def plot_ratio_chargebacks_per_month(self, data, cmap):

        output_png_filename = join(self.plot_output_folder, 'chgbcks_ratio.png')

        # i goes from 1 to len-1 (0 is the month), the i's are the reasons
        visa_ratio_chargebacks = [data['VISA_series'][i]['chargeback_ratio']
                                for i in range(1, len(data['VISA_series'].keys()) - 1)]
        # visa_nb_chargebacks is a list of list. We need the element-wise addition of all its elements
        visa_ratio_chargebacks = [sum(x) for x in zip(*[l for l in visa_ratio_chargebacks])]

        # i goes from 1 to len-1 (0 is the month), the i's are the reasons
        mc_ratio_chargebacks = [data['MASTERCARD_series'][i]['chargeback_ratio']
                              for i in range(1, len(data['MASTERCARD_series'].keys()) - 1)]
        # mc_nb_chargebacks is a list of list. We need the element-wise addition of all its elements
        mc_ratio_chargebacks = [sum(x) for x in zip(*[l for l in mc_ratio_chargebacks])]

        fig = {
            "data": [
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": data['VISA_series']['months'],
                    "y": visa_ratio_chargebacks,
                    "name": "VISA",
                    "marker": {
                        "color":  cmap['colors']['night blue']
                    },
                    "cliponaxis": False
                },
                {
                    "type": "bar",
                    "orientation": "v",
                    "x": data['MASTERCARD_series']['months'],
                    "y": mc_ratio_chargebacks,
                    "name": "MASTERCARD",
                    "marker": {
                        "color": cmap['colors']['accent1']
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
                    "tickangle":-30,
                    "visible": True,
                    "tickwidth":1,
                    "showticklabels": True,
                    "showgrid": False,
                    "zeroline": True,
                    "zerolinewidth": .1,
                    "zerolinecolor": "#444"
                },
                "yaxis": {
                    "title":"Percentage ratio",
                    "type": "linear",
                    "anchor": 'free',
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
        self.plugin_name = "Chargebacks Analysis"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx.pickle', 'tx_chbck.pickle']

    def process(self, *args, **kwargs):

        key_indicators = {'has_data': False}

        args = list(args)
        logger.debug(kwargs)

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin Chargebacks KPIs: Transaction data Missing')
            return key_indicators

        transactions = args[0]
        # transactions = pd.read_pickle("C:\\Users\\vincent.nelis\\Desktop\\wepair_CK\\etl_output\\tx.pickle")

        if len(args) < 2:
            logger.warning('Fatal Error: Plugin Chargebacks KPIs: Chargeback Transaction data Missing')
            return key_indicators

        chargeback_transactions = args[1]
        # chargeback_transactions = pd.read_pickle("C:\\Users\\vincent.nelis\\Desktop\\wepair_CK\\etl_output\\tx_chbck.pickle")
        # chargeback_transactions .sort_values(CB_DATE, ascending=True, inplace=True)

        # Check that all the required columns are present
        necessary_keys = [CB_DATE, CB_CURRENCY, CB_AMOUNT, CB_DISPUTE_STATUS, CB_CASE_STATUS, CB_REASON, CB_CARD_BRAND,
                          CB_SHOP_SHORT_NAME]
                if not all(key in chargeback_transactions.columns for key in necessary_keys):
            logger.warning('{fct_name}: necessary keys are missing: {keys}'
                            .format(fct_name=inspect.stack()[0][3],
                                    keys=[key for key in necessary_keys if key not in chargeback_transactions.columns]))
            return key_indicators
#create new function for chargeback ratio calculation
        def compute_chargeback_ratio(row):
            if row['n_txs'] == 0:
                return 0
            return row['n_chargebacks'] / row['n_txs']

        key_indicators = {'has_data': True}
#cb_transaction_ref_id is a column
        if CB_TRANSACTION_REF_ID in chargeback_transactions.columns:
            logger.debug('{fct_name}: {n} duplicated reference tx ID in the chargebacks'
                          .format(fct_name=inspect.stack()[0][3],
                                  n=len(chargeback_transactions[chargeback_transactions
                                        .duplicated(subset=CB_TRANSACTION_REF_ID,
                                                    keep='first')])))
            chargeback_transactions.drop_duplicates(subset=CB_TRANSACTION_REF_ID, keep='first', inplace=True)

        # For VISA

        chargebacks_visa = chargeback_transactions[chargeback_transactions[CB_CARD_BRAND] == 'Visa'][
            [CB_DATE, CB_AMOUNT]].copy()

        # chargebacks_visa.sort_values(CB_DATE, ascending=True, inplace=True)

        key_indicators.update({
            'VISA_n_chargebacks': len(chargebacks_visa),
            'VISA_amt_chargebacks': chargebacks_visa[CB_AMOUNT].sum()
        })

        # For MasterCard
        chargebacks_mc = chargeback_transactions[chargeback_transactions[CB_CARD_BRAND] == 'Master Card'][
            [CB_DATE, CB_AMOUNT]].copy()

        key_indicators.update({
            'MASTERCARD_n_chargebacks': len(chargebacks_mc),
            'MASTERCARD_amt_chargebacks': chargebacks_mc[CB_AMOUNT].sum()
        })

        # --------------------------------------------------------------------
        # Compute start and end dates
        # --------------------------------------------------------------------
        key_indicators['start_date'] = transactions[TRANSACTION_DATE].min()
        key_indicators['end_date'] = transactions[TRANSACTION_DATE].max()

        # --------------------------------------------------------------------
        # Compute Monthly Bar Chart for VISA
        # --------------------------------------------------------------------

        txs_visa = transactions[(transactions[CARD_BRAND] == 'Visa') & (transactions[TRANSACTION_IS_CAPTURE])][
            [TRANSACTION_DATE, AMOUNT_IN_EUR]]

        txs_visa = txs_visa[txs_visa[TRANSACTION_DATE] <= chargeback_transactions[CB_DATE].max()]

        txs_visa = txs_visa.resample('M', on=TRANSACTION_DATE) \
            .agg([sum, 'size']) \
            .reset_index(drop=False)
        txs_visa.columns = [TRANSACTION_DATE, 'amt_txs', 'n_txs']

        chargebacks_visa = chargeback_transactions[chargeback_transactions[CB_CARD_BRAND] == 'Visa'][
            [CB_REASON, CB_DATE, CB_AMOUNT]].copy()

        # Remove the missing reasons
        chargebacks_visa = chargebacks_visa[chargebacks_visa[CB_REASON] != 'nan'].reset_index(drop=True)

        # Obtaining the reasons ordered by number of chargebacks (So that in the bar plots and pie plots they appear
        # in the same order)
        visa_reasons = list(chargebacks_visa.groupby(CB_REASON)
                            .agg('size')
                            .reset_index(drop=False)
                            .rename(columns={0: 'n_chargebacks'})
                            .sort_values(by='n_chargebacks', ascending=False)
                            .reset_index(drop=True)[CB_REASON].unique())

        key_indicators['VISA_series'] = {'months': txs_visa[TRANSACTION_DATE].apply(
            lambda x: x.strftime('%b-%y')).tolist()}

        for idx, reason in enumerate(['all'] + visa_reasons):
            key_indicators['VISA_series'][idx] = {'reason': reason}
            if reason != 'all':
                txs = chargebacks_visa[chargebacks_visa[CB_REASON] == reason][[CB_DATE, CB_AMOUNT]].copy()
            else:
                txs = chargebacks_visa[[CB_DATE, CB_AMOUNT]].copy()
            txs = txs.resample('M', on=CB_DATE).agg([sum, 'size']).reset_index(drop=False)
            txs.columns = [CB_DATE, 'amt_chargebacks', 'n_chargebacks']
            txs = pd.merge(txs_visa, txs, left_on=TRANSACTION_DATE, right_on=CB_DATE, how='left')
            txs.drop(CB_DATE, axis=1, inplace=True)
            txs.fillna(0, inplace=True)
            txs['chargeback_ratio'] = txs.apply(compute_chargeback_ratio, axis=1)
            key_indicators['VISA_series'][idx]['n_chargebacks'] = txs['n_chargebacks'].tolist()
            key_indicators['VISA_series'][idx]['amt_chargebacks'] = txs['amt_chargebacks'].tolist()
            key_indicators['VISA_series'][idx]['chargeback_ratio'] = txs['chargeback_ratio'].tolist()
            del txs

        # --------------------------------------------------------------------
        # Compute Monthly Bar Chart for MasterCard
        # --------------------------------------------------------------------

        txs_mc = transactions[(transactions[CARD_BRAND] == 'Master Card') & (transactions[TRANSACTION_IS_CAPTURE])][
            [TRANSACTION_DATE, AMOUNT_IN_EUR]]

        txs_mc = txs_mc[txs_mc[TRANSACTION_DATE] <= chargeback_transactions[CB_DATE].max()]
        txs_mc = txs_mc.resample('M', on=TRANSACTION_DATE) \
            .agg([sum, 'size']) \
            .reset_index(drop=False)
        txs_mc.columns = [TRANSACTION_DATE, 'amt_txs', 'n_txs']

        chargebacks_mc = chargeback_transactions[chargeback_transactions[CB_CARD_BRAND] == 'Master Card'][
            [CB_REASON, CB_DATE, CB_AMOUNT]].copy()

        # Remove the missing reasons
        chargebacks_mc = chargebacks_mc[chargebacks_mc[CB_REASON] != 'nan'].reset_index(drop=True)

        # Obtaining the reasons ordered by number of chargebacks (So that in the bar plots and pie plots they appear
        # in the same order)

        mc_reasons = list(chargebacks_mc.groupby([CB_REASON])
                          .agg('size')
                          .reset_index(drop=False)
                          .rename(columns={0: 'n_chargebacks'})
                          .sort_values(by='n_chargebacks', ascending=False)
                          .reset_index(drop=True)[CB_REASON].unique())

        key_indicators['MASTERCARD_series'] = {
            'months': txs_mc[TRANSACTION_DATE].apply(lambda x: x.strftime('%b-%y')).tolist()}
        for idx, reason in enumerate(['all'] + mc_reasons):
            key_indicators['MASTERCARD_series'][idx] = {'reason': reason}
            if reason != 'all':
                txs = chargebacks_mc[chargebacks_mc[CB_REASON] == reason][[CB_DATE, CB_AMOUNT]].copy()
            else:
                txs = chargebacks_mc[[CB_DATE, CB_AMOUNT]].copy()

            if len(txs) > 0:
                txs = txs.resample('M', on=CB_DATE).agg([sum, 'size']).reset_index(drop=False)
                txs.columns = [CB_DATE, 'amt_chargebacks', 'n_chargebacks']
                txs = pd.merge(txs_mc, txs, left_on=TRANSACTION_DATE, right_on=CB_DATE, how='left')
                txs.drop(CB_DATE, axis=1, inplace=True)
                txs.fillna(0, inplace=True)
                txs.fillna(0, inplace=True)
                txs['chargeback_ratio'] = txs.apply(compute_chargeback_ratio, axis=1)
                key_indicators['MASTERCARD_series'][idx]['n_chargebacks'] = txs['n_chargebacks'].tolist()
                key_indicators['MASTERCARD_series'][idx]['amt_chargebacks'] = txs['amt_chargebacks'].tolist()
                key_indicators['MASTERCARD_series'][idx]['chargeback_ratio'] = txs['chargeback_ratio'].tolist()
            else:
                key_indicators['MASTERCARD_series'][idx]['n_chargebacks'] = [0]
                key_indicators['MASTERCARD_series'][idx]['amt_chargebacks'] = [0]
                key_indicators['MASTERCARD_series'][idx]['chargeback_ratio'] = [0]
            del txs

        # --------------------------------------------------------------------
        # Compute Pie Chart for VISA
        # --------------------------------------------------------------------

        chargebacks_visa = chargeback_transactions[chargeback_transactions[CB_CARD_BRAND] == 'Visa'][
            [CB_REASON, CB_AMOUNT]].copy()

        # Remove the missing reasons
        chargebacks_visa = chargebacks_visa[chargebacks_visa[CB_REASON] != 'nan'].reset_index(drop=True)

        chargebacks_visa = chargebacks_visa.groupby(CB_REASON) \
            .agg('size') \
            .reset_index(drop=False) \
            .rename(columns={0: 'n_chargebacks'}) \
            .sort_values(by='n_chargebacks', ascending=False) \
            .reset_index(drop=True)

        key_indicators.update({
            'VISA_pie_n_chargebacks': chargebacks_visa['n_chargebacks'].tolist(),
            'VISA_pie_reasons': chargebacks_visa[CB_REASON].tolist()
        })

        # --------------------------------------------------------------------
        # Compute Pie Chart for Master Card
        # --------------------------------------------------------------------

        chargebacks_mc = chargeback_transactions[chargeback_transactions[CB_CARD_BRAND] == 'Master Card'][
            [CB_REASON, CB_AMOUNT]].copy()

        # Remove the missing reasons
        chargebacks_mc = chargebacks_mc[chargebacks_mc[CB_REASON] != 'nan'].reset_index(drop=True)

        chargebacks_mc = chargebacks_mc.groupby([CB_REASON]) \
            .agg('size') \
            .reset_index(drop=False) \
            .rename(columns={0: 'n_chargebacks'}) \
            .sort_values(by='n_chargebacks', ascending=False) \
            .reset_index(drop=True)

        key_indicators.update({
            'MASTERCARD_pie_n_chargebacks': chargebacks_mc['n_chargebacks'].tolist(),
            'MASTERCARD_pie_reasons': chargebacks_mc[CB_REASON].tolist()
        })

        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(key_indicators, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return key_indicators
#args are used because below list of self.plot...etc...can be extended easily
    def plot(self, *args, **kwargs):
        input_data_file = join(self.process_output_folder, 'out.pickle')
        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)
        self.plot_chargebacks_overview(data, kwargs['cmap'])
        self.plot_chargebacks_monthly_analysis_overview(data, kwargs['cmap'])
        self.plot_number_chargebacks_per_month(data, kwargs['cmap'])
        self.plot_amount_chargebacks_per_month(data, kwargs['cmap'])
        self.plot_ratio_chargebacks_per_month(data,kwargs['cmap'])

    def report(self, report, styles, *args, **kwargs):
        input_data_file = join(self.process_output_folder, 'out.pickle')

        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        Report.draw_text_right(report, 'CHARGEBACK ANALYSIS', styles['Heading2-White'])

        Report.draw_text_right(report, 'Key Indicators and Overview', styles['Heading3-White'])

        # KPIs for VISA
        img = Image(join(dirname(inspect.getfile(inspect.currentframe())),  self.options['assets'], 'visa_logo.png'),
                    width=60,
                    height=20)
        txt_visa_n_chargebacks = Paragraph('Number of chargebacks<br/>Monetary value of chargebacks',
                                           style=styles['Normal'])
        kpi_visa_n_chargebacks = Paragraph('{n_chargebacks:,.0f}<br/>{amt_chargebacks:,.0f} €'
                                           .format(n_chargebacks=data['VISA_n_chargebacks'],
                                                   amt_chargebacks=data['VISA_amt_chargebacks']),
                                           style=styles['Normal'])
        list_tables = []
        colwidths = (85, 240, 80)

        # append the visa's table
        list_tables.append(Table(data=[(img, txt_visa_n_chargebacks, kpi_visa_n_chargebacks)], colWidths=colwidths, rowHeights=60, hAlign='CENTER'))

        # KPIs for MASTERCARD
        img = Image(join(dirname(inspect.getfile(inspect.currentframe())),  self.options['assets'], 'mc_logo.png'),
                    width=40,
                    height=30)

        txt_mastercard_n_chargebacks = Paragraph('Number of chargebacks<br/>Monetary value of chargebacks',
                                           style=styles['Normal'])
        kpi_visa_n_chargebacks = Paragraph('{n_chargebacks:,.0f}<br/>{amt_chargebacks:,.0f} €'
                                           .format(n_chargebacks=data['MASTERCARD_n_chargebacks'],
                                                   amt_chargebacks=data['MASTERCARD_amt_chargebacks']),
                                           style=styles['Normal'])

        # append the mastercard's table
        list_tables.append(Table([(img, txt_mastercard_n_chargebacks, kpi_visa_n_chargebacks)], colWidths=colwidths, rowHeights=60, hAlign='CENTER'))

        # TOTAL
        txt_total_n_chargebacks = Paragraph('<b>Total number of chargebacks<br/>Total monetary value of chargebacks</b>',
                                           style=styles['Normal'])
        kpi_total_n_chargebacks = Paragraph('{n_chargebacks:,.0f}<br/>{amt_chargebacks:,.0f} €'
                                           .format(n_chargebacks=data['VISA_n_chargebacks']+data['MASTERCARD_n_chargebacks'],
                                                   amt_chargebacks=data['VISA_amt_chargebacks']+data['MASTERCARD_amt_chargebacks']),
                                           style=styles['Normal'])

        # append the summary's table
        list_tables.append(Table([('', txt_total_n_chargebacks, kpi_total_n_chargebacks)], colWidths=colwidths, rowHeights=60, hAlign='CENTER'))

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

        Report.draw_text_right(report, 'CHARGEBACK ANALYSIS', styles['Heading2-White'])

        Report.draw_text_right(report, 'Key Indicators and Overview', styles['Heading3-White'])

        img = Image(join(self.plot_output_folder, 'VISA_chgbcks_overview.png'),
                    width=400,
                    height=225)

        Report.draw_text_left(doc=report, text='Chargeback reasons for VISA', style=styles['Heading3-NightBlue'],
                              x=50, y=530)
        Report.draw_image_left(doc=report, image=img, y_coordinate=410)

        img = Image(join(self.plot_output_folder, 'MASTERCARD_chgbcks_overview.png'),
                    width=400,
                    height=225)

        Report.draw_text_left(doc=report, text='Chargeback reasons for MASTERCARD', style=styles['Heading3-NightBlue'],
                              x=50, y=280)
        Report.draw_image_left(doc=report, image=img, y_coordinate=160)

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(report, 'CHARGEBACK ANALYSIS', styles['Heading2-White'])
        Report.draw_text_right(report, 'Monthly Analysis: Distribution of the chargeback reasons per month', styles['Heading3-White'])

        img = Image(join(self.plot_output_folder, 'VISA_chgbcks_distributions.png'),
                    width=450,
                    height=200)

        Report.draw_text_left(doc=report, text="VISA", style=styles['Heading3-NightBlue'], x=50, y=520)
        Report.draw_image_left(doc=report, image=img, y_coordinate=400)

        img = Image(join(self.plot_output_folder, 'MASTERCARD_chgbcks_distributions.png'),
                    width=450,
                    height=200)

        Report.draw_text_left(doc=report, text="MASTERCARD", style=styles['Heading3-NightBlue'],x=50,y=270)
        Report.draw_image_left(doc=report, image=img, y_coordinate=150)

        # Monthly analysis (Number of chargebacks per month for VISA and MASTERCARD)

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(report, 'CHARGEBACK ANALYSIS', styles['Heading2-White'])
        Report.draw_text_right(report, 'Monthly Analysis: Number of chargebacks per month for Visa and Mastercard', styles['Heading3-White'])

        img = Image(join(self.plot_output_folder, 'chgbcks_number.png'),
                    width=550,
                    height=400)

        Report.draw_image_left(doc=report,image=img)

        # Monthly analysis (Amount of chargebacks per month for VISA and MASTERCARD)

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(report, 'CHARGEBACK ANALYSIS', styles['Heading2-White'])
        Report.draw_text_right(report, 'Monthly Analysis: Monetary value of chargebacks per month for Visa and Mastercard', styles['Heading3-White'])

        img = Image(join(self.plot_output_folder, 'chgbcks_amount.png'),
                    width=550,
                    height=400)

        Report.draw_image_left(doc=report,image=img)

        # Monthly analysis (Number of chargebacks per month for VISA and MASTERCARD)

        Report.add_new_page(config=kwargs['config'], doc=report)

        Report.draw_text_right(report, 'CHARGEBACK ANALYSIS', styles['Heading2-White'])
        Report.draw_text_right(report, 'Monthly Analysis: Chargeback ratio per month for Visa and Mastercard', styles['Heading3-White'])

        img = Image(join(self.plot_output_folder, 'chgbcks_ratio.png'),
                    width=550,
                    height=400)

        Report.draw_image_left(doc=report, image=img)
