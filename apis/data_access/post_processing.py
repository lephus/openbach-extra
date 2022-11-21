#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# OpenBACH is a generic testbed able to control/configure multiple
# network/physical entities (under test) and collect data from them.
# It is composed of an Auditorium (HMIs), a Controller, a Collector
# and multiple Agents (one for each network entity that wants to be
# tested).
#
#
# Copyright © 2016-2020 CNES
#
#
# This file is part of the OpenBACH testbed.
#
#
# OpenBACH is a free software : you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY, without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

"""Utilities to present data from an InfluxDB server and optionaly plot them.
"""

__author__ = 'Mathias ETTINGER <mettinger@toulouse.viveris.com>'
__all__ = ['save', 'Statistics']

import math
import pickle
import stat
import warnings
import itertools
from functools import partial
from contextlib import suppress
from datetime import datetime,timedelta

import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from .influxdb_tools import (
        tags_to_condition, select_query,
        InfluxDBCommunicator, Operator,
        ConditionTag, ConditionAnd, ConditionOr,ConditionTimestamp,
)


DEFAULT_COLLECTOR_FILEPATH = '/opt/openbach/agent/collector.yml'


def _identity(x):
    return x


def _column_name_serializer(name):
    return '_'.join(map(str, name))


def _prepare_columns(df, columns):
    df = df.sort_values(['suffix', 'statistic'], axis=1)
    df.columns = [next(columns, name) or name for name in df.columns]
    return df


def influx_to_pandas(response, query):
    try:
        results = response['results']
    except KeyError:
        warnings.warn('The query \'{}\' returned no result, ignoring'.format(query))
        return

    for result in results:
        try:
            series = result['series']
        except KeyError:
            warnings.warn('The query \'{}\' result contained no time series, ignoring'.format(query))
            continue

        for serie in series:
            try:
                yield pd.DataFrame(serie['values'], columns=serie['columns'])
            except KeyError:
                warnings.warn('The query \'{}\' returned time series with no data, ignoring'.format(query))
                pass


def compute_histogram(bins):
    def _compute_histogram(series):
        histogram, _ = np.histogram(series.dropna(), bins)
        return histogram / histogram.sum()
        
    return _compute_histogram


def compute_annotated_histogram(bins):
    _hist = compute_histogram(bins)
    _bins = bins[1:]
    def _compute_annotated_histogram(series):
        return pd.DataFrame(dict(zip(_bins, _hist(series))), index=[series.name])      
    return _compute_annotated_histogram


def save(figure, filename, use_pickle=False, set_legend=True):
   
    if use_pickle:
        with open(filename, 'wb') as storage:
            pickle.dump(figure, storage)
    else:

        for axis in figure.axes:
            
            if axis.get_legend() and set_legend:
                axis.legend(loc='center left', bbox_to_anchor=(1., .5))
            
        figure.savefig(filename, bbox_inches='tight')

def aggregator_factory(mapping):
    def aggregator(pd_datetime):
        for moment, intervals in mapping.items():
            for interval in intervals:
                if pd_datetime in interval:
                    return moment
        return 'undefined'
    return aggregator

def get_time_interval(df,start_journey,start_evening,start_night):

        list_date=set()
        for date in df.index.date:
            list_date.add(date)
        interval_jour=[]
        interval_soiree=[]
        interval_nuit=[]

        for item in list_date:
            journee=pd.Interval(pd.Timestamp('{} {}:00:00'.format(item,start_journey)), pd.Timestamp('{} {}:00:00'.format(item,start_evening)))
            interval_jour.append(journee)
            soiree=pd.Interval(pd.Timestamp('{} {}:00:00'.format(item,start_evening)), pd.Timestamp('{} {}:00:00'.format(item+timedelta(days=1),start_night)))
            interval_soiree.append(soiree)
            nuit=pd.Interval(pd.Timestamp('{} {}:00:00'.format(item+timedelta(days=1),start_night)), pd.Timestamp('{} {}:00:00'.format(item+timedelta(days=1),start_journey)))
            interval_nuit.append(nuit)

        mapping={f'Journée ({start_journey}h-{start_evening}h)':interval_jour,f'Soirée ({start_evening}h-{start_night}h)':interval_soiree,f'Nuit ({start_night}h-{start_journey}h)':interval_nuit}
        return mapping
        
class Statistics(InfluxDBCommunicator):
    @classmethod
    def from_default_collector(cls, filepath=DEFAULT_COLLECTOR_FILEPATH):
        with open(filepath) as f:
            collector = yaml.safe_load(f)

        influx = collector.get('stats', {})
        return cls(
                collector['address'],
                influx.get('query', 8086),
                influx.get('database', 'openbach'),
                influx.get('precision', 'ms'))

    @property
    def origin(self):
        with suppress(AttributeError):
            return self._origin

    @origin.setter
    def origin(self, value):
        if value is not None and not isinstance(value, int):
            raise TypeError('origin should be None or a timestamp in milliseconds')
        self._origin = value

    def _raw_influx_query(
            self, job=None, scenario=None, agent=None, job_instances=(),
            suffix=None, fields=None,timestamps=None, condition=None):

        if timestamps is not None:
            timestamp_condition = ConditionTimestamp.from_timestamps(timestamps)
            condition=timestamp_condition if condition is None else ConditionAnd(condition, timestamp_condition)

        
        conditions = tags_to_condition(scenario, agent, None, suffix, condition) 

        instances = [
                ConditionTag('@job_instance_id', Operator.Equal, job_id)
                for job_id in job_instances
        ]

        if not conditions and not instances:
            
            _condition = None
        elif conditions and not instances:
            
            _condition = conditions
        elif not conditions and instances:
            
            _condition = ConditionOr(*instances)
        else:
            _condition = ConditionAnd(conditions, ConditionOr(*instances))
        return select_query(job, fields, _condition)

    def _parse_dataframes(self, response, query):
        offset = self.origin
        names = ['job', 'scenario', 'agent', 'suffix', 'statistic']
        for df in influx_to_pandas(response, query):
            converters = dict.fromkeys(df.columns, partial(pd.to_numeric, errors='coerce'))            
            converters.pop('@owner_scenario_instance_id')
            converters.pop('@suffix', None)
            converters['@agent_name'] = _identity
            converted = [convert(df[column]) for column, convert in converters.items()]

            if '@suffix' in df:
                converted.append(df['@suffix'].fillna(''))
            else:
                converted.append(pd.Series('', index=df.index, name='@suffix'))
            df = pd.concat(converted, axis=1)

            df.set_index(['@job_instance_id', '@scenario_instance_id', '@agent_name', '@suffix'], inplace=True)
            for index in df.index.unique():
                extract = df.xs(index)
                if isinstance(extract, pd.Series):
                    extract = pd.DataFrame(extract.to_dict(), index=[0])
                section = extract.reset_index(drop=True).dropna(axis=1, how='all')
                section['time'] -= section.time[0] if offset is None else offset
                section.set_index('time', inplace=True)
                section.index.name = 'Time (ms)'
                section.reindex(columns=section.columns.sort_values())
                section.columns = pd.MultiIndex.from_tuples([index + (name,) for name in section.columns], names=names)
                yield section

    def fetch(
            self, job=None, scenario=None, agent=None, job_instances=(),
            suffix=None, fields=None,timestamps=None, condition=None):
        query = self._raw_influx_query(job, scenario, agent, job_instances, suffix, fields, timestamps,condition)
        data = self.sql_query(query)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
        yield from (_Plot(df) for df in self._parse_dataframes(data, query))

    def fetch_all(
            self, job=None, scenario=None, agent=None, job_instances=(),
            suffix=None, fields=None,timestamps=None, condition=None, columns=None):
        query = self._raw_influx_query(job, scenario, agent, job_instances, suffix, fields,timestamps, condition)
        data = self.sql_query(query)
        df = pd.concat(self._parse_dataframes(data, query), axis=1)
        if not job_instances or columns is None:
            return _Plot(df)
        columns = iter(columns)
        return _Plot(pd.concat([_prepare_columns(df[id], columns) for id in job_instances if id in df], axis=1))


class _Plot:
    def __init__(self, dataframe):
        self.dataframe = dataframe

        self.df = dataframe[dataframe.index >= 0]

    def _find_statistic(self, statistic_name=None, index=None):
        if statistic_name is not None:
            index = self.df.columns.get_level_values(4) == statistic_name


        if index is None:
            return self.df
        else:
            df = self.df.iloc[:, index]
            if isinstance(df, pd.DataFrame):
                return df
            else:
                return df.to_frame()

    def time_series(self):
        df = self.dataframe.interpolate()
        return df[df.index >= 0]

    def histogram(self, buckets):
        r_min = self.df.min().min()
        r_max = self.df.max().max()
        bins = np.linspace(r_min, r_max, buckets + 1)
        histogram = compute_histogram(bins)
        df = self.df.apply(histogram)
        bins = (bins + np.roll(bins, -1)) / 2
        df.index = bins[:buckets]
        return df

    def cumulative_histogram(self, buckets):
        return self.histogram(buckets).cumsum()

    def comparison(self):
        mean = self.df.mean()
        std = self.df.std().fillna(0)
        df = pd.concat([mean, std], axis=1)
        df.columns = ['Ε', 'δ']
        return df

    def temporal_binning_statistics(
            self, statistic_name=None, index=None,
            time_aggregation='hour', percentiles=[.05, .25, .75, .95]):

        df = self._find_statistic(statistic_name, index)
        
        df.index = pd.to_datetime(df.index, unit='ms')
        
        for _, column in df.items():
            groups = column.groupby(getattr(column.index, time_aggregation))
            stats = groups.describe(percentiles=percentiles)
            stats.index.name = 'Time ({}s)'.format(time_aggregation)
            yield stats

    def temporal_binning_histogram(
            self, statistic_name=None, index=None,
            bin_size=100, offset=0, maximum=None,
            time_aggregation='hour', add_total=True,facteur=None):

        df = self._find_statistic(statistic_name, index)
        
        df.index = pd.to_datetime(df.index, unit='ms')


        df =df/facteur
        
        if maximum is None:
            nb_segments = math.ceil((df.max().max() - offset) / bin_size)
            maximum = nb_segments * bin_size + offset
        nb_segments = math.ceil((maximum - offset) / bin_size)

        bins = np.linspace(offset, maximum, nb_segments + 1, dtype='int')
        
        for _, column in df.items():
            
            dframe=pd.DataFrame({column.name:column})
           
            groups = dframe.groupby(getattr(dframe.index, time_aggregation))
            stats = groups.apply(compute_annotated_histogram(bins))
            stats.index = ['{}-{}'.format(i, i+1) for i in stats.index.droplevel()]
            stats.index.name = 'Time ({}s)'.format(time_aggregation)
            if add_total:
                total = column.to_frame().apply(compute_histogram(bins))
                total.index = bins[1:]
                total.columns = ['total']
                stats = stats.append(total.transpose())          
            yield stats * 100
    

    def compute_function( self,df,function,facteur,
                           start_journey=None,start_evening=None,start_night=None):

        df.index = pd.to_datetime(df.index, unit='ms')
        df=df/facteur

        mapping=get_time_interval(df,start_journey,start_evening,start_night)
    
        moments=mapping.keys()
        if function=='moyenne':
            means_Series=df.mean(axis=1)
            mean_groups=means_Series.groupby(aggregator_factory(mapping))
            stat=mean_groups.mean()

        if function=='mediane':
            median_Series=df.median(axis=1)
            median_groups=median_Series.groupby(aggregator_factory(mapping))
            stat=median_groups.median()

        if function=='min':
            min_Series=df.min(axis=1)
            min_groups=min_Series.groupby(aggregator_factory(mapping))
            stat=min_groups.min()
            
        if function=='max':
            max_Series=df.max(axis=1)
            max_groups=max_Series.groupby(aggregator_factory(mapping))
            stat=max_groups.max() 

        return stat,moments  

        
    def plot_time_series(self, axis=None, secondary_title=None, legend=True):
        axis = self.time_series().plot(ax=axis, legend=legend)
        if secondary_title is not None:
            axis.set_ylabel(secondary_title)
        return axis

    def plot_kde(self, axis=None, secondary_title=None, legend=True):
        axis = self.df.plot.kde(ax=axis, legend=legend)
        if secondary_title is not None:
            axis.set_xlabel(secondary_title)
        return axis

    def plot_histogram(self, axis=None, secondary_title=None, bins=100, legend=True):

        axis = self.histogram(bins).plot(ax=axis, ylim=[-0.01, 1.01], legend=legend)
        if secondary_title is not None:
            axis.set_xlabel(secondary_title)
        return axis

    def plot_cumulative_histogram(self, axis=None, secondary_title=None, bins=100, legend=True):
        axis = self.cumulative_histogram(bins).plot(ax=axis, ylim=[-0.01, 1.01], legend=legend)
        if secondary_title is not None:
            axis.set_xlabel(secondary_title)
        return axis

    def plot_comparison(self, axis=None, secondary_title=None, legend=True):
        df = self.comparison()
        axis = df.Ε.plot.bar(ax=axis, yerr=df.δ, rot=30, legend=legend)
        if secondary_title is not None:
            axis.set_ylabel(secondary_title)
        return axis

    def plot_temporal_binning_statistics(
            self, axis=None, secondary_title=None,
            statistic_name=None, index=None,
            percentiles=[[5, 95], [25, 75]], time_aggregation='hour',
            median=True, average=True, deviation=True,
            boundaries=True, min_max=True, legend=True,grid=True):

        if not percentiles:
            percentiles = []
        else:
            percentiles.sort(key=lambda x: abs(x[0] - x[1]), reverse=True)

        format_percentiles = [p / 100 for pair in percentiles for p in pair]

        temporal_binning = self.temporal_binning_statistics(
                statistic_name, index,
                time_aggregation, format_percentiles)

        if axis is None:
            _, axis = plt.subplots()
        colors = ['#ffad60', '#ffdae0']

        for stats in temporal_binning:
            if average:
                axis.plot(stats.index, stats['mean'], color='#005b96', label='average')
            if median:
                axis.plot(stats.index, stats['50%'], color='#be68be', label='median')
            if boundaries:
                axis.plot(stats.index, stats['min'], color='g', linewidth=1)
                axis.plot(stats.index, stats['max'], color='#e50000', linewidth=1)
            if min_max:
                axis.fill_between(stats.index, stats['min'], stats['max'], color='#39c9bb', label='min-max')
            for color, pair in zip(colors, percentiles):
                low, high = sorted(pair)
                axis.fill_between(
                        stats.index, stats['{}%'.format(low)],
                        stats['{}%'.format(high)], color=color,
                        label='{}%-{}%'.format(low, high))
            if deviation:        
                axis.errorbar(
                        stats.index, stats['mean'], stats['std'], uplims=True,
                        lolims=True, color='#005b96', elinewidth=1, label="deviation")
            if legend:
                axis.legend()

            if grid:
                axis.grid()
                
            axis.set_xlabel(stats.index.name)
            if secondary_title is not None:
                axis.set_ylabel(secondary_title)
        
        return axis


    def plot_temporal_binning_histogram(
            self, axis=None, secondary_title=None,
            statistic_name=None, index=None,
            bin_size=100, offset=0, maximum=None,
            time_aggregation='hour', add_total=True,
            legend=True, legend_title=None,stats_unit=None,legend_unit=None,colormap=None,facteur=None):


        temporal_binning = self.temporal_binning_histogram(
                statistic_name, index,
                bin_size, offset, maximum,
                time_aggregation, add_total,facteur)

        if axis is None:

            _, axis = plt.subplots()

        for stats in temporal_binning:
            cmap=plt.get_cmap(colormap)
                
            colors = cmap(np.linspace(0, 1, len(stats.columns)))        

            xticks_size, xtick_weight = (5, 'bold') if len(stats.index) > 50 else (None, None)

            label_list=list(stats.columns)
            label_list.append(0)
            label_list.sort()    
            label=[]
            for index in range(len(list(stats.columns))):
                label.append('{} - {}'.format( label_list[index], label_list[index+1]))
            for num,(index, segments) in enumerate(stats.iterrows()):

                starts = segments.cumsum() - segments

                if not num:
                   bars= axis.bar(index, segments, bottom=starts,width=0.5,label=label,color=colors, edgecolor='k', linewidth=0.1)
                else:
                   bars= axis.bar(index, segments, bottom=starts,width=0.5,color=colors, edgecolor='k', linewidth=0.1)

                axis.set_xticks(stats.index)      
                axis.set_xticklabels(stats.index, rotation=90, fontsize=xticks_size, weight=xtick_weight)
            handles, labels = plt.gca().get_legend_handles_labels()
            if legend:
                axis.legend(reversed(handles),reversed(labels),labelspacing=0.5,title=f'{legend_title} ({legend_unit})', loc='center left', bbox_to_anchor=(1., .5))
               
            axis.set_xlabel(stats.index.name)
            if secondary_title is not None:
                axis.set_ylabel(secondary_title)

        return axis


