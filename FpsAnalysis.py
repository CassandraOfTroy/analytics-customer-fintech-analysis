# -*- coding: utf-8 -*-
"""
Created on Mon Jul 22 15:29:32 2019

@author: marina.tosic
"""

from wepair.plugins.plugin import Plugin
from ...globals import COLNAMES_RISK_MANAGEMENT
import pandas as pd
import inspect
import pickle
from os.path import join
from ...utils.location import Location
from ...utils.time_window import TimeWindow
from reportlab.platypus import Image
import plotly.io as pio
import plotly.graph_objs as go
from datetime import *
from wepair.utils_common.log import Log
from ...utils.report import Report

# log
logger = Log(__name__).get_logger()

# orca config
pio.orca.config.use_xvfb = 'auto'

FPS_SHOP_ACCOUNT_SHORT_NAME = COLNAMES_RISK_MANAGEMENT['Merchant Account Short Name']
FPS_TRANSACTION_RESULT = COLNAMES_RISK_MANAGEMENT['Transaction Result']
FPS_REASON_CODE = COLNAMES_RISK_MANAGEMENT['FPS Reason Code List']
FPS_OVERALL_SCORE = COLNAMES_RISK_MANAGEMENT['FPS Overall Score']
FPS_DATE = COLNAMES_RISK_MANAGEMENT['Transaction Date']
FPS_CARD_CATEGORY = COLNAMES_RISK_MANAGEMENT['Card Category']
FPS_CARD_BRAND = COLNAMES_RISK_MANAGEMENT['Card Brand']
FPS_AMOUNT = COLNAMES_RISK_MANAGEMENT['Order Amount']
FPS_AMOUNT_IN_EUR = 'Order Amount in EUR'
FPS_CURRENCY = COLNAMES_RISK_MANAGEMENT['Order Amount Currency']
FPS_INTERCEPT_REASON_CODE = COLNAMES_RISK_MANAGEMENT['FPS Intercept Reason Code']
FPS_ORDER_ID = COLNAMES_RISK_MANAGEMENT['Order Number']


class FpsAnalysis(Plugin):

    @staticmethod
    def _plot_monthly_analysis(data, target, cmap, filename):

        if target == 'rate':
            trace1 = go.Bar(
                x=data['monthly_analysis']['months'],
                y=data['monthly_analysis']['approval_rate'],
                text=list(map(lambda x: '{:0,.0f}%'.format(x*100),data['monthly_analysis']['approval_rate'])),
                textposition= "inside",
                textfont={"size": 20,
                          "color": "#ffffff"},
                name='Approved Transactions',
                marker=dict(
                    color=cmap['colors']['night blue']
                )
            )
            trace2 = go.Bar(
                x=data['monthly_analysis']['months'],
                y=data['monthly_analysis']['decline_rate'],
                name='Declined Transactions',
                marker=dict(
                    color=cmap['colors']['accent1']
                )
            )

            traces = [trace1, trace2]
            layout = go.Layout(
                barmode='stack',
                width=1000,
                height=1000,
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
                    "title" : "Decline rate",
                    "type": "linear",
                    "automargin": True,
                    "tickformat": "%",
                    "range":[0.4, 1]
                },
                legend={
                    "borderwidth": 0,
                    "orientation": "h",
                    "traceorder": "normal",
                    "y": -0.2,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top",
                    "font": {
                        "size": 20
                    }
                },
                margin={
                    "t": 50
                }
            )
            fig = go.Figure(data=traces, layout=layout)
            pio.write_image(fig, filename)

        elif target == 'n_transactions':

            trace1 = go.Bar(
                x=data['monthly_analysis']['months'],
                y=data['monthly_analysis']['n_accepts'],
                name='Approved Transactions',
                marker=dict(
                    color=cmap['colors']['night blue']
                )
            )

            trace2 = go.Bar(
                x=data['monthly_analysis']['months'],
                y=data['monthly_analysis']['n_declines'],
                name='Declined Transactions',
                marker=dict(
                    color=cmap['colors']['accent1']
                )
            )

            traces = [trace1, trace2]

            layout = go.Layout(
                barmode='stack',
                width=1000,
                height=1000,
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
                    "title":"Number of declined transactions",
                    "type": "linear",
                    "automargin": True,
                },
                legend={
                    "borderwidth": 0,
                    "orientation": "h",
                    "traceorder": "normal",
                    "y": -0.2,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top",
                    "font": {
                        "size": 20
                    }
                },
                margin={
                    "t": 50
                }
            )
            fig = go.Figure(data=traces, layout=layout)
            pio.write_image(fig, filename)

    @staticmethod
    def _plot_country_analysis(data, target, time_window_idx, cmap, filename):

        if target == 'n_transactions':
            y_accept = 'n_accepts'
            y_decline = 'n_declines'
            yaxis_tickformat = ''
        elif target == 'rate':
            y_accept = 'approval_rate'
            y_decline = 'decline_rate'
            yaxis_tickformat = '%'
        else:
            logger.warning('Fatal Error: Plugin FPS KPIs: Target unknown')
            return

        fig = {
            "data": [{
                "type": "bar",
                "name": "Approval rate",
                "x": data['country_analysis']['time_window_' + str(time_window_idx)]['countries'],
                "y": data['country_analysis']['time_window_' + str(time_window_idx)][y_accept],
                "text": list(map(lambda x:'{:0,.0f}%'.format(x*100), data['country_analysis']
                ['time_window_' + str(time_window_idx)][y_accept])) if target == 'rate' else None,
                "textposition": "inside",
                "textfont": {
                    "size": 20,
                    "color": "#ffffff"
                },
                "marker": {
                    "color": cmap['colors']['night blue']
                }
            },
                {
                    "type": "bar",
                    "name": "Decline rate",
                    "x": data['country_analysis']['time_window_' + str(time_window_idx)]['countries'],
                    "y": data['country_analysis']['time_window_' + str(time_window_idx)][y_decline],
                    "marker": {
                        "color": cmap['colors']['accent1']
                    }
                }],
            "layout": {
                "barmode": "stack",
                "width": 1000,
                "height":1000,
                "font": {
                    "size": 20
                },
                "bargap": 0.5,
                "yaxis": {
                    "title":"Number of declined transactions",
                    "tickformat": yaxis_tickformat
                },
                "legend": {
                    "borderwidth": 0,
                    "orientation": "h",
                    "traceorder": "normal",
                    "y": -0.35,
                    "x": 0.5,
                    "xanchor": "center",
                    "yanchor": "top",
                    "font": {
                        "size": 20
                    }
                },
                "xaxis": {
                    "tickangle": -45,
                },
                "margin": {
                    "t": 50
                }
            }
        }

        if target == 'rate':
            fig['layout']['yaxis']['range'] = [0.4, 1]
            fig['layout']['yaxis']['title'] = "Decline rate"

        pio.write_image(fig, filename, scale=3.0)

    def __init__(self, plugin_folder, id, options=None):

        self.plugin_name = "FPS Kpis"
        super().__init__(plugin_folder, id, options)
        self.required_input_data = ['tx_fps.pickle']

    def process(self, *args, **kwargs):

        key_indicators = {'has_data': False}

        args = list(args)
        logger.debug(kwargs)

        if len(args) < 1:
            logger.warning('Fatal Error: Plugin FPS KPIs: FPS Transactional data Missing')
            return key_indicators

        fps_transactions = args[0]

        # Check that all the required columns are present
        necessary_keys = [FPS_DATE, FPS_TRANSACTION_RESULT, FPS_AMOUNT_IN_EUR]
        if not all(key in fps_transactions.columns for key in necessary_keys):
            logger.warning('{fct_name}: necessary keys are missing: {keys}'
                            .format(fct_name=inspect.stack()[0][3],
                                    keys=[key for key in necessary_keys if key not in fps_transactions.columns]))
            return key_indicators

        def _per_country_analysis(start_period, end_period, txs):

            declined_per_country = txs[(txs[FPS_DATE] >= start_period) &
                                       (txs[FPS_DATE] <= end_period) &
                                       (txs[FPS_TRANSACTION_RESULT] == 'NOK')] \
                .copy() \
                .reset_index(drop=True)

            declined_per_country = declined_per_country.groupby('SHOP_COUNTRY') \
                .agg({FPS_AMOUNT_IN_EUR: [sum, 'size']}) \
                .reset_index(drop=False)
            declined_per_country.columns = declined_per_country.columns.droplevel(1)
            declined_per_country.columns = ['SHOP_COUNTRY', 'amt_declines', 'n_declines']
            declined_per_country = declined_per_country.sort_values(by='SHOP_COUNTRY', ascending=True) \
                .reset_index(drop=True)

            accepted_per_country = txs[(txs[FPS_DATE] >= start_period) &
                                       (txs[FPS_DATE] <= end_period) &
                                       (txs[FPS_TRANSACTION_RESULT] == 'OK')] \
                .copy() \
                .reset_index(drop=True)
            accepted_per_country = accepted_per_country.groupby('SHOP_COUNTRY') \
                .agg({FPS_AMOUNT_IN_EUR: [sum, 'size']}) \
                .reset_index(drop=False)
            accepted_per_country.columns = accepted_per_country.columns.droplevel(1)
            accepted_per_country.columns = ['SHOP_COUNTRY', 'amt_accepts', 'n_accepts']
            accepted_per_country = accepted_per_country.sort_values(by='SHOP_COUNTRY', ascending=True) \
                .reset_index(drop=True)

            txs_per_country = txs[(txs[FPS_DATE] >= start_period) &
                                  (txs[FPS_DATE] <= end_period)] \
                .copy() \
                .reset_index(drop=True)
            txs_per_country = txs_per_country.groupby('SHOP_COUNTRY') \
                .agg({FPS_AMOUNT_IN_EUR: [sum, 'size']}) \
                .reset_index(drop=False)
            txs_per_country.columns = txs_per_country.columns.droplevel(1)
            txs_per_country.columns = ['SHOP_COUNTRY', 'amt_txs', 'n_txs']
            txs_per_country = txs_per_country.sort_values(by='SHOP_COUNTRY', ascending=True) \
                .reset_index(drop=True)

            txs_per_country = pd.merge(txs_per_country, declined_per_country, on='SHOP_COUNTRY', how='left')
            txs_per_country = pd.merge(txs_per_country, accepted_per_country, on='SHOP_COUNTRY', how='left')
            txs_per_country.fillna(0, inplace=True)

            txs_per_country['pct_accepts'] = txs_per_country.apply(
                lambda row: row['n_accepts'] / row['n_txs'] if row['n_txs'] > 0 else 0, axis=1)

            txs_per_country['pct_declines'] = txs_per_country.apply(
                lambda row: row['n_declines'] / row['n_txs'] if row['n_txs'] > 0 else 0, axis=1)

            txs_per_country = txs_per_country.sort_values(by='SHOP_COUNTRY', ascending=True) \
                .reset_index(drop=True)

            return {
                'countries': txs_per_country['SHOP_COUNTRY'].tolist(),
                'n_reviewed': txs_per_country['n_txs'].tolist(),
                'n_declines': txs_per_country['n_declines'].tolist(),
                'n_accepts': txs_per_country['n_accepts'].tolist(),
                # 'reviewed_amt': txs_per_country['amt_txs'].tolist(),
                # 'amt_declines': txs_per_country['amt_declines'].tolist(),
                # 'amt_accepts': txs_per_country['amt_accepts'].tolist(),
                'decline_rate': txs_per_country['pct_declines'].tolist(),
                'approval_rate': txs_per_country['pct_accepts'].tolist()
            }

        # Compute the dates of the first and last transactions

        # --------------------------------------------------------------------
        # Filter and pre-process
        # --------------------------------------------------------------------

        fps_transactions = fps_transactions[fps_transactions[FPS_OVERALL_SCORE] > -1]

        if len(fps_transactions) == 0:
            return key_indicators

        key_indicators = {'has_data': True}
        location = Location(self.options['assets'])

        fps_transactions = fps_transactions[
            fps_transactions[FPS_SHOP_ACCOUNT_SHORT_NAME].apply(lambda x: x.split(' ')[3] != 'INV')]

        fps_transactions = fps_transactions[fps_transactions[FPS_AMOUNT_IN_EUR] > 0]

        fps_transactions['SHOP_COUNTRY'] = fps_transactions[FPS_SHOP_ACCOUNT_SHORT_NAME].apply(
            lambda x: location.get_country_name(x.split(' ')[1]))

        n_transactions = len(fps_transactions)
        n_declines = len(fps_transactions[fps_transactions[FPS_TRANSACTION_RESULT] == 'NOK'])

        # --------------------------------------------------------------------
        # Compute number of declines per month (Txs level)
        # --------------------------------------------------------------------

        declined_per_month = fps_transactions[fps_transactions[FPS_TRANSACTION_RESULT] == 'NOK'].copy()
        declined_per_month = declined_per_month.resample('M', on=FPS_DATE) \
            .agg({FPS_AMOUNT_IN_EUR: [sum, 'size']}) \
            .reset_index(drop=False)
        declined_per_month.columns = declined_per_month.columns.droplevel(1)
        declined_per_month.columns = [FPS_DATE, 'amt_declines', 'n_declines']
        declined_per_month = declined_per_month.sort_values(by=FPS_DATE, ascending=True) \
            .reset_index(drop=True)

        accepted_per_month = fps_transactions[fps_transactions[FPS_TRANSACTION_RESULT] == 'OK'].copy()
        accepted_per_month = accepted_per_month.resample('M', on=FPS_DATE) \
            .agg({FPS_AMOUNT_IN_EUR: [sum, 'size']}) \
            .reset_index(drop=False)
        accepted_per_month.columns = accepted_per_month.columns.droplevel(1)
        accepted_per_month.columns = [FPS_DATE, 'amt_accepts', 'n_accepts']
        accepted_per_month = accepted_per_month.sort_values(by=FPS_DATE, ascending=True) \
            .reset_index(drop=True)

        txs_per_month = fps_transactions.copy()
        txs_per_month = txs_per_month.resample('M', on=FPS_DATE) \
            .agg({FPS_AMOUNT_IN_EUR: [sum, 'size']}) \
            .reset_index(drop=False)
        txs_per_month.columns = txs_per_month.columns.droplevel(1)
        txs_per_month.columns = [FPS_DATE, 'amt_txs', 'n_txs']
        txs_per_month = txs_per_month.sort_values(by=FPS_DATE, ascending=True) \
            .reset_index(drop=True)

        declined_per_month = pd.merge(declined_per_month, txs_per_month, on=FPS_DATE, how='left')
        declined_per_month = pd.merge(declined_per_month, accepted_per_month, on=FPS_DATE, how='left')

        def compute_pct_declines(row):
            if row['n_txs'] == 0:
                return 0
            return row['n_declines'] / row['n_txs']

        declined_per_month['pct_declines'] = declined_per_month.apply(compute_pct_declines, axis=1)

        def compute_pct_accepts(row):
            if row['n_txs'] == 0:
                return 0
            return row['n_accepts'] / row['n_txs']

        declined_per_month['pct_accepts'] = declined_per_month.apply(compute_pct_accepts, axis=1)

        key_indicators.update({
            'monthly_analysis': {
                'months': declined_per_month[FPS_DATE].apply(lambda x: x.strftime('%b-%y')).tolist(),
                'n_reviewed': declined_per_month['n_txs'].tolist(),
                'n_declines': declined_per_month['n_declines'].tolist(),
                'n_accepts': declined_per_month['n_accepts'].tolist(),
                # 'reviewed_amt': declined_per_month['amt_txs'].tolist(),
                # 'amt_declines': declined_per_month['amt_declines'].tolist(),
                # 'amt_accepts': declined_per_month['amt_accepts'].tolist(),
                'decline_rate': declined_per_month['pct_declines'].tolist(),
                'approval_rate': declined_per_month['pct_accepts'].tolist()
            }
        })

        # --------------------------------------------------------------------
        # Compute number of declines per country in past months (Txs level)
        # --------------------------------------------------------------------

        key_indicators['country_analysis'] = dict()
        for time_window_idx, time_window in enumerate(self.options['time_windows']):
            start_window, end_window = TimeWindow.get_time_window(time_window)
            key_indicators['country_analysis']['time_window_' + str(time_window_idx)] \
                = _per_country_analysis(start_window, end_window, fps_transactions)
        process_output_file = join(self.process_output_folder, 'out.pickle')

        with open(process_output_file, "wb") as pickle_out:
            pickle.dump(key_indicators, pickle_out, protocol=pickle.HIGHEST_PROTOCOL)

        return key_indicators

    def plot(self, *args, **kwargs):

        input_data_file = join(self.process_output_folder, 'out.pickle')
        with open(input_data_file, 'rb') as handle:
            data = pickle.load(handle)

        for target in self.options['target']:
            self._plot_monthly_analysis(data, target, kwargs['cmap'],
                                        join(self.plot_output_folder,
                                             'monthly_' + target + '.png'))
        for time_window_idx, _ in enumerate(self.options['time_windows']):
            for target in self.options['target']:
                self._plot_country_analysis(data, target, time_window_idx, kwargs['cmap'],
                                            join(self.plot_output_folder,
                                                 'country_' + target + '_time_window_' + str(time_window_idx) + '.png'))

    def report(self, report, styles, *args, **kwargs):

        for target in self.options['target']:

            Report.add_new_page(config=kwargs['config'], doc=report)

            Report.draw_text_right(doc=report, text='FRAUD PREVENTION STATISTICS', style=styles['Heading2-White'])


            filename = join(self.plot_output_folder, 'monthly_' + target + '.png')

            if target == 'rate':
                Report.draw_text_right(doc=report,
                                       text='Monthly Analysis: Monthly approval rate on transactional level',
                                       style=styles['Heading3-White'])
            elif target == 'n_transactions':
                Report.draw_text_right(doc=report,
                                       text='Monthly Analysis: Number of approved and declined transactions per month',
                                       style=styles['Heading3-White'])

            img = Image(filename, width=500, height=500)

            Report.draw_image_left(doc=report, image=img)

        for time_window_idx, time_window in enumerate(self.options['time_windows']):
            window_start, window_end = TimeWindow.get_time_window(time_window)

            period_start = datetime.strftime(window_start, '%B %Y')
            period_end = datetime.strftime(window_end, '%B %Y')
            if period_start != period_end:

                for target in self.options['target']:

                    Report.add_new_page(config=kwargs['config'], doc=report)

                    filename = join(self.plot_output_folder,
                                    'country_' + target + '_time_window_' + str(time_window_idx) + '.png')
                    title = ''
                    if target == 'rate':
                        Report.draw_text_right(doc=report, text='Per Country Analysis: Approval rate on transactional level', style=styles['Heading3-White'])
                    elif target == 'n_transactions':
                        Report.draw_text_right(doc=report, text='Per Country Analysis: Number of approved and declined transactions', style=styles['Heading3-White'])

                    Report.draw_text_right(doc=report, text='FRAUD PREVENTION STATISTICS',
                                           style=styles['Heading2-White'])
                    Report.draw_text_right(doc=report, text=title, style=styles['Heading4-White'])

                    img = Image(filename,
                                width=500,
                                height=500)

                    Report.draw_image_left(doc=report, image=img)
            else:
                for target in self.options['target']:

                    Report.add_new_page(config=kwargs['config'], doc=report)

                    filename = join(self.plot_output_folder,
                                    'country_' + target + '_time_window_' + str(time_window_idx) + '.png')
                    title = ''
                    if target == 'rate':
                        title = 'Approval rate on transactional level.'
                    elif target == 'n_transactions':
                        title = 'Number of approved and declined transactions.'

                    Report.draw_text_right(doc=report, text='FRAUD PREVENTION STATISTICS',
                                           style=styles['Heading2-White'])
                    Report.draw_text_right(doc=report, text=title, style=styles['Heading4-White'])
                    Report.draw_text_right(doc=report, text='Per country analysis', style=styles['Heading3-White'])

                    img = Image(filename,
                                width=500,
                                height=500)
                    Report.draw_image_left(doc=report, image=img)

